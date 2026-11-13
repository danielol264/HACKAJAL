"""Módulo de gestión y validación de alertas epidemiológicas para HACKAJAL (Sprint 3).

Permite:
- Consultar alertas con filtros por estado y enfermedad
- Métricas dinámicas: Total, Pendientes, Confirmadas, Descartadas
- Tabla detallada con visualización de estado mediante badges
- Confirmación de alertas con diálogo obligatorio de mensaje público (máx. 2,000 caracteres con contador en vivo)
- Descarte de alertas con confirmación
- Control estricto de permisos (ADMIN: todas las acciones; CONSULTA: sólo lectura y detalle)
- Manejo de respuestas HTTP 400, 401, 403, 404 y 409 con actualización automática
- Ejecución asíncrona mediante QThreadPool sin bloquear la interfaz
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import AlertBadge, Card, EmptyStateWidget, MetricCard, PanelTitle
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.alerts_service import AlertsService
from app.services.api.client import ApiClient


# =============================================================================
# Asynchronous Background Worker
# =============================================================================

class AlertsWorkerSignals(QObject):
    alerts_loaded = Signal(list, list)  # alerts, diseases
    action_succeeded = Signal(str, dict)  # action_name, alert_data
    error_occurred = Signal(str, int)  # message, status_code
    finished = Signal()


class AlertsWorker(QRunnable):
    """Background worker for alerts API calls without blocking the UI."""

    def __init__(
        self,
        alerts_service: AlertsService,
        action: str = "fetch",
        estado: str | None = None,
        enfermedad: str | None = None,
        alerta_id: int | None = None,
        mensaje_publico: str = "",
    ) -> None:
        super().__init__()
        self.alerts_service = alerts_service
        self.action = action
        self.estado = estado
        self.enfermedad = enfermedad
        self.alerta_id = alerta_id
        self.mensaje_publico = mensaje_publico
        self.signals = AlertsWorkerSignals()

    def run(self) -> None:
        try:
            if self.action == "fetch":
                # Get diseases for filter dropdown
                enfermedades = []
                try:
                    enfermedades = self.alerts_service.api_client.get("/enfermedades/") or []
                except Exception:
                    pass
                alerts = self.alerts_service.get_alertas(
                    estado=self.estado or None,
                    enfermedad=self.enfermedad or None,
                )
                try:
                    self.signals.alerts_loaded.emit(alerts, enfermedades)
                except RuntimeError:
                    pass

            elif self.action == "confirm" and self.alerta_id:
                res = self.alerts_service.confirmar_alerta(self.alerta_id, self.mensaje_publico)
                try:
                    self.signals.action_succeeded.emit("confirm", res)
                except RuntimeError:
                    pass

            elif self.action == "discard" and self.alerta_id:
                res = self.alerts_service.descartar_alerta(self.alerta_id)
                try:
                    self.signals.action_succeeded.emit("discard", res)
                except RuntimeError:
                    pass

        except ApiError as err:
            status = err.status or 0
            detail = ""
            if isinstance(err.data, dict):
                detail = err.data.get("detail") or str(err.data)
            elif isinstance(err.data, str):
                detail = err.data
            else:
                detail = f"Error {status}"
            try:
                self.signals.error_occurred.emit(detail, status)
            except RuntimeError:
                pass
        except ApiRequestError:
            try:
                self.signals.error_occurred.emit("No se pudo conectar con el servidor", 0)
            except RuntimeError:
                pass
        except Exception as ex:
            try:
                self.signals.error_occurred.emit(f"Error inesperado: {ex}", 0)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass


# =============================================================================
# Dialogs: Detalle de Alerta y Confirmación con Mensaje Público
# =============================================================================

class AlertDetailDialog(QDialog):
    """Modal displaying complete alert information."""

    def __init__(self, alert: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Detalle de Alerta #{alert.get('id')}")
        self.setMinimumSize(540, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #183447;
                font-family: 'Segoe UI', Arial;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"Alerta Epidemiológica #{alert.get('id')}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #123B4A;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(AlertBadge(alert.get("estado", "pendiente")))
        layout.addLayout(header)

        # Information Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        def add_row(r: int, lbl: str, val: str, bold: bool = False) -> None:
            l = QLabel(lbl)
            l.setStyleSheet("color: #647C8C; font-size: 12px; font-weight: 600;")
            v = QLabel(val)
            v.setWordWrap(True)
            v.setStyleSheet(f"color: #123B4A; font-size: 12.5px; {'font-weight: 700;' if bold else ''}")
            grid.addWidget(l, r, 0)
            grid.addWidget(v, r, 1)

        enf_nom = alert.get("enfermedad_nombre") or alert.get("enfermedad", "Dengue")
        add_row(0, "Enfermedad:", str(enf_nom), True)
        add_row(1, "Periodo proyectado:", f"Mes {alert.get('mes', '--')} / {alert.get('anio', '--')}")
        add_row(2, "Casos estimados:", f"{alert.get('casos_estimados', '--')} casos", True)
        anterior = alert.get("casos_anio_anterior")
        add_row(3, "Casos mismo mes año anterior:", f"{anterior} casos" if anterior is not None else "Sin dato comparativo")
        add_row(4, "Fecha de creación:", str(alert.get("creada_en", "--")))

        if alert.get("revisada_por"):
            add_row(5, "Revisada por:", str(alert.get("revisada_por")))
            add_row(6, "Fecha de revisión:", str(alert.get("revisada_en", "--")))

        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        # Motivo
        motivo_box = QFrame()
        motivo_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        m_layout = QVBoxLayout(motivo_box)
        m_layout.setContentsMargins(10, 8, 10, 8)
        m_title = QLabel("Motivo epidemiológico:")
        m_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569;")
        m_text = QLabel(alert.get("motivo", "Sin motivo especificado"))
        m_text.setWordWrap(True)
        m_text.setStyleSheet("color: #1E293B; font-size: 12px;")
        m_layout.addWidget(m_title)
        m_layout.addWidget(m_text)
        layout.addWidget(motivo_box)

        # Mensaje público (si existe)
        if alert.get("mensaje_publico"):
            pub_box = QFrame()
            pub_box.setStyleSheet("background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 10px;")
            p_layout = QVBoxLayout(pub_box)
            p_layout.setContentsMargins(10, 8, 10, 8)
            p_title = QLabel("Mensaje público publicado en portal:")
            p_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #166534;")
            p_text = QLabel(alert.get("mensaje_publico", ""))
            p_text.setWordWrap(True)
            p_text.setStyleSheet("color: #14532D; font-size: 12px;")
            p_layout.addWidget(p_title)
            p_layout.addWidget(p_text)
            layout.addWidget(pub_box)

        layout.addStretch()

        # Close button
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("secondaryButton")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("QPushButton { background-color: #EAF0F5; color: #123B4A; border-radius: 6px; padding: 8px 18px; font-weight: 600; }")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


class ConfirmAlertDialog(QDialog):
    """Dialog requiring a public message before confirming an alert."""

    def __init__(self, alert: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.alert = alert
        self.public_message: str = ""
        self.setWindowTitle(f"Confirmar Alerta #{alert.get('id')}")
        self.setMinimumSize(560, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #183447;
                font-family: 'Segoe UI', Arial;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel(f"Confirmar Alerta Epidemiológica #{alert.get('id')}")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #123B4A;")
        layout.addWidget(title)

        # Notice
        notice = QFrame()
        notice.setStyleSheet("background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 8px; padding: 8px;")
        n_layout = QHBoxLayout(notice)
        n_layout.setContentsMargins(10, 8, 10, 8)
        n_lbl = QLabel(
            "⚠️ Atención: Al confirmar esta alerta, pasará a estado 'confirmada' y el mensaje público "
            "se emitirá para conocimiento de la población en el portal web institucional."
        )
        n_lbl.setWordWrap(True)
        n_lbl.setStyleSheet("color: #92400E; font-size: 11.5px; font-weight: 600;")
        n_layout.addWidget(n_lbl)
        layout.addWidget(notice)

        # Context summary
        enf = alert.get("enfermedad_nombre") or alert.get("enfermedad", "Dengue")
        summary = QLabel(
            f"<b>Enfermedad:</b> {enf} | <b>Periodo:</b> Mes {alert.get('mes')}/{alert.get('anio')} | "
            f"<b>Casos estimados:</b> {alert.get('casos_estimados')}"
        )
        summary.setStyleSheet("color: #334155; font-size: 12px;")
        layout.addWidget(summary)

        # Message Label + Counter
        msg_header = QHBoxLayout()
        msg_lbl = QLabel("Mensaje público institucional *:")
        msg_lbl.setStyleSheet("font-weight: 700; color: #123B4A; font-size: 12px;")
        self.char_counter = QLabel("0 / 2,000 caracteres")
        self.char_counter.setStyleSheet("color: #647C8C; font-size: 11px;")
        msg_header.addWidget(msg_lbl)
        msg_header.addStretch()
        msg_header.addWidget(self.char_counter)
        layout.addLayout(msg_header)

        # Text input
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Escribe aquí las recomendaciones sanitarias y preventivas oficiales que verá la población..."
        )
        default_draft = (
            f"Se proyecta un incremento epidemiológico de {enf} en la región costera de Jalisco. "
            "Se solicita a la población eliminar criaderos en recipientes con agua y usar repelente."
        )
        self.text_edit.setPlainText(default_draft)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 7px;
                padding: 10px;
                font-size: 12.5px;
                background-color: #F8FAFC;
                color: #0F172A;
            }
            QTextEdit:focus {
                border-color: #028090;
                background-color: #FFFFFF;
            }
        """)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Checkbox confirmation
        self.chk_confirm = QCheckBox("Confirmo la emisión y publicación oficial de esta alerta epidemiológica.")
        self.chk_confirm.setStyleSheet("font-size: 12px; color: #1E293B; font-weight: 600;")
        self.chk_confirm.toggled.connect(self._validate)
        layout.addWidget(self.chk_confirm)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("background-color: #EAF0F5; color: #123B4A; border-radius: 6px; padding: 8px 16px; font-weight: 600;")

        self.btn_submit = QPushButton("Confirmar y Publicar")
        self.btn_submit.setObjectName("actionButton")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.clicked.connect(self._on_submit)
        self.btn_submit.setStyleSheet("background-color: #123B4A; color: white; border-radius: 6px; padding: 8px 20px; font-weight: 700;")

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_submit)
        layout.addLayout(btn_layout)

        self._on_text_changed()

    def _on_text_changed(self) -> None:
        text = self.text_edit.toPlainText().strip()
        length = len(text)
        self.char_counter.setText(f"{length:,} / 2,000 caracteres")

        if length > 2000:
            self.char_counter.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 700;")
            self.error_label.setText("El mensaje excede el límite de 2,000 caracteres.")
            self.error_label.setVisible(True)
            self.btn_submit.setEnabled(False)
        elif length == 0:
            self.char_counter.setStyleSheet("color: #647C8C; font-size: 11px;")
            self.error_label.setText("El mensaje público es obligatorio.")
            self.error_label.setVisible(True)
            self.btn_submit.setEnabled(False)
        else:
            self.char_counter.setStyleSheet("color: #647C8C; font-size: 11px;")
            self.error_label.setVisible(False)
            self.btn_submit.setEnabled(self.chk_confirm.isChecked())

    def _validate(self) -> None:
        self._on_text_changed()

    def _on_submit(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.error_label.setText("Debes ingresar un mensaje público antes de confirmar.")
            self.error_label.setVisible(True)
            return
        if len(text) > 2000:
            self.error_label.setText("El mensaje público no puede superar 2,000 caracteres.")
            self.error_label.setVisible(True)
            return
        if not self.chk_confirm.isChecked():
            self.error_label.setText("Debes marcar la casilla de confirmación.")
            self.error_label.setVisible(True)
            return

        self.public_message = text
        self.accept()


# =============================================================================
# Main Alerts Management Module Page
# =============================================================================

class AlertsPage(QWidget):
    """Alerts Management Module (Sprint 3)."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        alerts_service: AlertsService | None = None,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.user = user or User("Administrador", "admin@hackajal.salud.gob.mx", UserRole.ADMIN, "Secretaría de Salud Jalisco")
        self.api_client = api_client or ApiClient()
        self.alerts_service = alerts_service or AlertsService(self.api_client)

        # State
        self.raw_alerts: list[dict[str, Any]] = []
        self.is_loading = False
        self.selected_estado = ""
        self.selected_enfermedad = ""
        self.search_text = ""

        # Root layout with responsive scroll support
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(20, 16, 20, 20)
        self.content_layout.setSpacing(14)

        # 1. Header Card & Filter Bar
        self._build_header()

        # 2. Status Banners (Success / Loading / Error)
        self._build_banners()

        # 3. Dynamic Indicator Cards (Total, Pendientes, Confirmadas, Descartadas)
        self._build_indicators_section()

        # 4. Table Card
        self._build_table_section()

        scroll.setWidget(self.content_container)
        root.addWidget(scroll)

        if auto_refresh:
            self.refresh_alerts()

    # -------------------------------------------------------------------------
    # Header & Filter Bar
    # -------------------------------------------------------------------------

    def _build_header(self) -> None:
        header_card = Card()
        layout = QVBoxLayout(header_card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        # Top line: Title & Subtitle + User/Role Badge
        top_line = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Gestión de Alertas Epidemiológicas")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Región Costera de Jalisco · Monitoreo institucional, revisión y publicación ciudadana")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_line.addLayout(title_box)

        top_line.addStretch()

        badge_box = QHBoxLayout()
        user_lbl = QLabel(f"{self.user.nombre} ({self.user.role.value.upper()})")
        user_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #123B4A;")
        badge_box.addWidget(user_lbl)
        if self.user.role == UserRole.ADMIN:
            admin_badge = QLabel("👑 ADMINISTRADOR")
            admin_badge.setObjectName("demoBadge")
            admin_badge.setStyleSheet("background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px;")
            badge_box.addWidget(admin_badge)
        else:
            consult_badge = QLabel("👁️ SOLO LECTURA")
            consult_badge.setStyleSheet("background-color: #E2E8F0; color: #475569; border: 1px solid #CBD5E1; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px;")
            badge_box.addWidget(consult_badge)
        top_line.addLayout(badge_box)

        layout.addLayout(top_line)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        # Filter: Estado
        filter_bar.addWidget(QLabel("Estado:"))
        self.combo_estado = QComboBox()
        self.combo_estado.addItem("Todas las alertas", "")
        self.combo_estado.addItem("Pendientes de revisión", "pendiente")
        self.combo_estado.addItem("Confirmadas (publicadas)", "confirmada")
        self.combo_estado.addItem("Descartadas", "descartada")
        self.combo_estado.currentIndexChanged.connect(self._on_filters_changed)
        filter_bar.addWidget(self.combo_estado)

        # Filter: Enfermedad
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Enfermedad:"))
        self.combo_enfermedad = QComboBox()
        self.combo_enfermedad.addItem("Todas las enfermedades", "")
        self.combo_enfermedad.addItem("Dengue", "dengue")
        self.combo_enfermedad.addItem("Diabetes mellitus tipo 2", "dm2")
        self.combo_enfermedad.currentIndexChanged.connect(self._on_filters_changed)
        filter_bar.addWidget(self.combo_enfermedad)

        # Search bar
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Buscar:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar en motivo o ID...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setMaximumWidth(220)
        filter_bar.addWidget(self.search_input)

        filter_bar.addStretch()

        # Refresh button
        self.btn_refresh = QPushButton("↻ Actualizar lista")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_alerts)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)
        self.content_layout.addWidget(header_card)

    def _build_banners(self) -> None:
        # Success Toast Banner
        self.success_banner = QFrame()
        self.success_banner.setVisible(False)
        self.success_banner.setStyleSheet("background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 6px;")
        s_layout = QHBoxLayout(self.success_banner)
        s_layout.setContentsMargins(12, 6, 12, 6)
        self.success_label = QLabel()
        self.success_label.setStyleSheet("color: #15803D; font-weight: 700; font-size: 12px;")
        s_layout.addWidget(self.success_label)
        self.content_layout.addWidget(self.success_banner)

        # Error Banner
        self.error_banner = QFrame()
        self.error_banner.setVisible(False)
        self.error_banner.setStyleSheet("background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 6px;")
        e_layout = QHBoxLayout(self.error_banner)
        e_layout.setContentsMargins(12, 6, 12, 6)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #991B1B; font-weight: 600; font-size: 12px;")
        e_layout.addWidget(self.error_label)
        e_layout.addStretch()
        btn_retry = QPushButton("Reintentar")
        btn_retry.setObjectName("retryButton")
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self.refresh_alerts)
        e_layout.addWidget(btn_retry)
        self.content_layout.addWidget(self.error_banner)

        # Loading Indicator
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px;")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        self.loading_label = QLabel("⟳ Conectando con la API de alertas...")
        self.loading_label.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(self.loading_label)
        self.content_layout.addWidget(self.loading_bar)

    # -------------------------------------------------------------------------
    # Metric Indicators (Total, Pendientes, Confirmadas, Descartadas)
    # -------------------------------------------------------------------------

    def _build_indicators_section(self) -> None:
        self.indicators_container = QWidget()
        self.indicators_layout = QGridLayout(self.indicators_container)
        self.indicators_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.setSpacing(12)

        self.card_total = MetricCard("Total de alertas", "0", "Alertas registradas", "#123B4A")
        self.card_pendientes = MetricCard("Pendientes", "0", "Requieren revisión oficial", "#C47A27")
        self.card_confirmadas = MetricCard("Confirmadas", "0", "Publicadas en portal web", "#BD4B4B")
        self.card_descartadas = MetricCard("Descartadas", "0", "Sin acción requerida", "#647C8C")

        self.indicators_layout.addWidget(self.card_total, 0, 0)
        self.indicators_layout.addWidget(self.card_pendientes, 0, 1)
        self.indicators_layout.addWidget(self.card_confirmadas, 0, 2)
        self.indicators_layout.addWidget(self.card_descartadas, 0, 3)

        self.content_layout.addWidget(self.indicators_container)

    # -------------------------------------------------------------------------
    # Alerts Table Section
    # -------------------------------------------------------------------------

    def _build_table_section(self) -> None:
        table_card = Card()
        layout = QVBoxLayout(table_card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_title = QLabel("Registro de Alertas Epidemiológicas")
        header_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #123B4A;")
        header_row.addWidget(header_title)
        header_row.addStretch()
        self.count_badge = QLabel("0 alertas encontradas")
        self.count_badge.setObjectName("muted")
        header_row.addWidget(self.count_badge)
        layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        headers = ["ID", "Enfermedad", "Año", "Mes", "Estimados", "Año anterior", "Motivo", "Estado", "Creada en"]
        if self.user.role == UserRole.ADMIN:
            headers.append("Acciones")
        else:
            headers.append("Detalle")

        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.setMinimumHeight(280)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Enfermedad
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Año
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Mes
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Estimados
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Anterior
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)           # Motivo
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Estado
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Creada en
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Acciones

        layout.addWidget(self.table)
        self.content_layout.addWidget(table_card)

    # -------------------------------------------------------------------------
    # Asynchronous Data Loading & Actions
    # -------------------------------------------------------------------------

    def refresh_alerts(self) -> None:
        """Fetch alerts from the API in a background worker."""
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = AlertsWorker(
            alerts_service=self.alerts_service,
            action="fetch",
            estado=self.combo_estado.currentData(),
            enfermedad=self.combo_enfermedad.currentData(),
        )
        worker.signals.alerts_loaded.connect(self._on_alerts_loaded)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_worker_finished(self) -> None:
        self.is_loading = False
        self.btn_refresh.setEnabled(True)
        self.loading_bar.setVisible(False)

    def _on_error_occurred(self, message: str, status: int) -> None:
        self.error_banner.setVisible(True)
        if status == 400:
            self.error_label.setText(f"Solicitud incorrecta (HTTP 400): {message}")
        elif status == 401:
            self.error_label.setText("Sesión expirada o no autorizada (HTTP 401).")
            if self.alerts_service.api_client.on_unauthorized:
                self.alerts_service.api_client.on_unauthorized()
        elif status == 403:
            self.error_label.setText("No tienes permiso para esta acción (HTTP 403).")
        elif status == 404:
            self.error_label.setText(f"Alerta no encontrada (HTTP 404): {message or 'El recurso no existe.'}")
        elif status == 409:
            self.error_label.setText("Conflicto (HTTP 409): La alerta ya fue revisada por otro usuario. Se actualizó la lista.")
            # Auto-refresh on 409 as required!
            self.refresh_alerts()
        else:
            self.error_label.setText(f"Error al comunicar con la API: {message}")

    def _on_alerts_loaded(self, alerts: list[dict[str, Any]], enfermedades: list[dict[str, Any]]) -> None:
        self.error_banner.setVisible(False)
        self.raw_alerts = alerts

        # Update disease filter combo if needed
        if enfermedades and self.combo_enfermedad.count() <= 3:
            current = self.combo_enfermedad.currentData()
            self.combo_enfermedad.blockSignals(True)
            self.combo_enfermedad.clear()
            self.combo_enfermedad.addItem("Todas las enfermedades", "")
            for d in enfermedades:
                self.combo_enfermedad.addItem(d.get("nombre", d.get("clave")), d.get("clave"))
            idx = self.combo_enfermedad.findData(current)
            if idx >= 0:
                self.combo_enfermedad.setCurrentIndex(idx)
            self.combo_enfermedad.blockSignals(False)

        # Update metrics indicators
        self._update_indicators(alerts)

        # Filter & render table
        self._render_table()

    def _update_indicators(self, alerts: list[dict[str, Any]]) -> None:
        total = len(alerts)
        pendientes = sum(1 for a in alerts if a.get("estado") == "pendiente")
        confirmadas = sum(1 for a in alerts if a.get("estado") == "confirmada")
        descartadas = sum(1 for a in alerts if a.get("estado") == "descartada")

        self.card_total.update_value(f"{total:,}")
        self.card_pendientes.update_value(f"{pendientes:,}")
        self.card_confirmadas.update_value(f"{confirmadas:,}")
        self.card_descartadas.update_value(f"{descartadas:,}")

    def _get_filtered_alerts(self) -> list[dict[str, Any]]:
        results = self.raw_alerts
        # Filter by text search
        query = self.search_text.strip().lower()
        if query:
            filtered = []
            for a in results:
                motivo = str(a.get("motivo", "")).lower()
                enf = str(a.get("enfermedad_nombre", a.get("enfermedad", ""))).lower()
                aid = str(a.get("id", ""))
                if query in motivo or query in enf or query == aid:
                    filtered.append(a)
            results = filtered
        return results

    def _render_table(self) -> None:
        alerts = self._get_filtered_alerts()
        self._update_indicators(alerts)
        self.count_badge.setText(f"{len(alerts)} alerta(s) listada(s)")
        self.table.setRowCount(len(alerts))

        for row, a in enumerate(alerts):
            aid = a.get("id")
            enf = a.get("enfermedad_nombre") or a.get("enfermedad", "Dengue")
            anio = str(a.get("anio", "--"))
            mes = str(a.get("mes", "--"))
            est = f"{a.get('casos_estimados', '--')}"
            ant = str(a.get("casos_anio_anterior", "—")) if a.get("casos_anio_anterior") is not None else "—"
            motivo = a.get("motivo", "")
            estado = a.get("estado", "pendiente")
            creada = str(a.get("creada_en", ""))[:16].replace("T", " ")

            item_id = QTableWidgetItem(f"#{aid}")
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_enf = QTableWidgetItem(enf)
            item_anio = QTableWidgetItem(anio)
            item_anio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_mes = QTableWidgetItem(mes)
            item_mes.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_est = QTableWidgetItem(est)
            item_est.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_ant = QTableWidgetItem(ant)
            item_ant.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            item_motivo = QTableWidgetItem(motivo)
            item_motivo.setToolTip(motivo)

            item_creada = QTableWidgetItem(creada)
            item_creada.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_enf)
            self.table.setItem(row, 2, item_anio)
            self.table.setItem(row, 3, item_mes)
            self.table.setItem(row, 4, item_est)
            self.table.setItem(row, 5, item_ant)
            self.table.setItem(row, 6, item_motivo)

            # Badge Estado
            badge_widget = QWidget()
            b_layout = QHBoxLayout(badge_widget)
            b_layout.setContentsMargins(4, 2, 4, 2)
            b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_layout.addWidget(AlertBadge(estado))
            self.table.setCellWidget(row, 7, badge_widget)

            self.table.setItem(row, 8, item_creada)

            # Actions Column
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Button 1: Ver Detalle
            btn_det = QPushButton("👁️")
            btn_det.setToolTip("Ver detalle de la alerta")
            btn_det.setStyleSheet("QPushButton { background-color: #EAF0F5; border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 8px; font-size: 11px; } QPushButton:hover { background-color: #DDE6ED; }")
            btn_det.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_det.clicked.connect(lambda _, alert=a: self._open_detail(alert))
            act_layout.addWidget(btn_det)

            # Admin-only buttons for pending alerts
            if self.user.role == UserRole.ADMIN:
                if estado == "pendiente":
                    btn_conf = QPushButton("✓ Confirmar")
                    btn_conf.setToolTip("Confirmar y redactar mensaje público")
                    btn_conf.setStyleSheet("QPushButton { background-color: #15803D; color: white; border: none; border-radius: 5px; padding: 4px 8px; font-weight: 700; font-size: 11px; } QPushButton:hover { background-color: #166534; }")
                    btn_conf.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_conf.clicked.connect(lambda _, alert=a: self._open_confirm_dialog(alert))
                    act_layout.addWidget(btn_conf)

                    btn_disc = QPushButton("✕ Descartar")
                    btn_disc.setToolTip("Descartar alerta sin publicar")
                    btn_disc.setStyleSheet("QPushButton { background-color: #64748B; color: white; border: none; border-radius: 5px; padding: 4px 8px; font-weight: 600; font-size: 11px; } QPushButton:hover { background-color: #475569; }")
                    btn_disc.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn_disc.clicked.connect(lambda _, alert=a: self._prompt_discard(alert))
                    act_layout.addWidget(btn_disc)
                else:
                    status_lbl = QLabel("Revisada")
                    status_lbl.setStyleSheet("color: #94A3B8; font-size: 10px; font-style: italic;")
                    act_layout.addWidget(status_lbl)

            self.table.setCellWidget(row, 9, actions_widget)

    # -------------------------------------------------------------------------
    # Dialogs & Action Triggers
    # -------------------------------------------------------------------------

    def _open_detail(self, alert: dict[str, Any]) -> None:
        dialog = AlertDetailDialog(alert, self)
        dialog.exec()

    def _on_table_double_clicked(self) -> None:
        row = self.table.currentRow()
        alerts = self._get_filtered_alerts()
        if 0 <= row < len(alerts):
            self._open_detail(alerts[row])

    def _open_confirm_dialog(self, alert: dict[str, Any]) -> None:
        if self.user.role != UserRole.ADMIN:
            QMessageBox.warning(self, "Acción restringida", "Sólo usuarios con rol Administrador pueden confirmar alertas.")
            return

        dialog = ConfirmAlertDialog(alert, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            msg = dialog.public_message
            self._execute_confirm(alert.get("id"), msg)

    def _execute_confirm(self, alert_id: int, public_message: str) -> None:
        self.loading_bar.setVisible(True)
        self.btn_refresh.setEnabled(False)

        worker = AlertsWorker(
            alerts_service=self.alerts_service,
            action="confirm",
            alerta_id=alert_id,
            mensaje_publico=public_message,
        )
        worker.signals.action_succeeded.connect(self._on_action_success)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _prompt_discard(self, alert: dict[str, Any]) -> None:
        if self.user.role != UserRole.ADMIN:
            QMessageBox.warning(self, "Acción restringida", "Sólo usuarios con rol Administrador pueden descartar alertas.")
            return

        aid = alert.get("id")
        enf = alert.get("enfermedad_nombre") or alert.get("enfermedad", "Dengue")
        resp = QMessageBox.question(
            self,
            f"Descartar Alerta #{aid}",
            f"¿Estás seguro de que deseas descartar la alerta #{aid} ({enf})?\n\n"
            "Esta alerta cambiará su estado a 'descartada' y no se emitirá al público.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._execute_discard(aid)

    def _execute_discard(self, alert_id: int) -> None:
        self.loading_bar.setVisible(True)
        self.btn_refresh.setEnabled(False)

        worker = AlertsWorker(
            alerts_service=self.alerts_service,
            action="discard",
            alerta_id=alert_id,
        )
        worker.signals.action_succeeded.connect(self._on_action_success)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_action_success(self, action_name: str, alert_data: dict[str, Any]) -> None:
        aid = alert_data.get("id")
        if action_name == "confirm":
            self.success_label.setText(f"✓ Alerta #{aid} confirmada y publicada en el portal web exitosamente.")
        else:
            self.success_label.setText(f"✓ Alerta #{aid} descartada exitosamente.")
        self.success_banner.setVisible(True)

        # Refresh list automatically to reflect new state and updated indicators
        self.refresh_alerts()

    # -------------------------------------------------------------------------
    # Filter Handlers
    # -------------------------------------------------------------------------

    def _on_filters_changed(self) -> None:
        self.refresh_alerts()

    def _on_search_changed(self, text: str) -> None:
        self.search_text = text
        self._render_table()
