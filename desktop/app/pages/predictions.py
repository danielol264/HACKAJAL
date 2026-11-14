"""Módulo de consulta y administración de predicciones epidemiológicas (Fase 6).

Endpoints oficiales:
GET /predicciones/?enfermedad= (🔒)
POST /predicciones/ (👑 solo ADMIN)

Implementa:
- Consulta y visualización de proyecciones matemáticas semanales (Semanas 1 a 4)
- Identificación clara: Casos estimados / Modelo predictivo (no confirmados)
- Estados vacíos informativos cuando no existe predicción
- Panel administrativo para ejecución y registro de nuevas proyecciones
- Validación estricta: exactamente 4 valores semanales numéricos >= 0
- Detección de alerta generada ("Se generó una alerta pendiente de revisión")
- Manejo asíncrono con QThreadPool
- Documentación transparente sobre la disponibilidad del modelo local de Machine Learning
"""
from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import Card, EmptyStateWidget, MetricCard, PanelTitle, WeeklyCard
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient
from app.services.epidemiology_service import EpidemiologyService


class PredictionsWorkerSignals(QObject):
    pred_loaded = Signal(dict, list)  # pred_data, enfermedades
    pred_created = Signal(dict)
    error_occurred = Signal(str, int)
    finished = Signal()


class PredictionsWorker(QRunnable):
    """Background worker for prediction queries and registration."""

    def __init__(
        self,
        epi_service: EpidemiologyService,
        action: str = "fetch",
        enfermedad: str = "dengue",
        create_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.epi_service = epi_service
        self.action = action
        self.enfermedad = enfermedad
        self.create_payload = create_payload or {}
        self.signals = PredictionsWorkerSignals()

    def run(self) -> None:
        try:
            if self.action == "fetch":
                enfermedades = []
                try:
                    enfermedades = self.epi_service.get_enfermedades() or []
                except Exception:
                    pass
                pred = self.epi_service.get_prediccion(enfermedad=self.enfermedad)
                try:
                    self.signals.pred_loaded.emit(pred, enfermedades)
                except RuntimeError:
                    pass

            elif self.action == "create":
                res = self.epi_service.create_prediccion(
                    enfermedad=self.create_payload["enfermedad"],
                    anio=self.create_payload["anio"],
                    mes=self.create_payload["mes"],
                    semanas=self.create_payload["semanas"],
                )
                try:
                    self.signals.pred_created.emit(res)
                except RuntimeError:
                    pass

        except ApiError as err:
            status = err.status or 0
            detail = ""
            if isinstance(err.data, dict):
                detail = err.data.get("detail") or str(err.data)
            else:
                detail = f"Error {status}"
            try:
                self.signals.error_occurred.emit(detail, status)
            except RuntimeError:
                pass
        except ApiRequestError:
            try:
                self.signals.error_occurred.emit("No se pudo conectar con el servidor.", 0)
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


class PredictionsPage(QWidget):
    """Epidemiological predictions and model execution page."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        epi_service: EpidemiologyService | None = None,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.user = user
        self.api_client = api_client or ApiClient()
        self.epi_service = epi_service or EpidemiologyService(self.api_client)

        self.current_enfermedad = "dengue"
        self.predictable_diseases: set[str] = {"dengue"}
        self.is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # 1. Header Card
        root.addWidget(self._build_header_card())

        # 2. Status Banners
        self._build_banners(root)

        # 3. Main Splitter: Prediction Display (Left) + Execution / Technical Panel (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: Prediction Details
        self.display_card = Card()
        self.disp_layout = QVBoxLayout(self.display_card)
        self.disp_layout.setContentsMargins(16, 14, 16, 14)
        self.disp_layout.setSpacing(12)

        self.disp_content = QWidget()
        self.disp_content_layout = QVBoxLayout(self.disp_content)
        self.disp_content_layout.setContentsMargins(0, 0, 0, 0)
        self.disp_content_layout.setSpacing(10)
        self.disp_layout.addWidget(self.disp_content)

        splitter.addWidget(self.display_card)

        # Right: Administrative Generation Panel
        self.admin_card = Card()
        self.admin_layout = QVBoxLayout(self.admin_card)
        self.admin_layout.setContentsMargins(16, 14, 16, 14)
        self.admin_layout.setSpacing(10)
        self._build_admin_panel()
        splitter.addWidget(self.admin_card)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        self._render_empty()

        if auto_refresh:
            self.refresh_prediction()

    def _build_header_card(self) -> QWidget:
        card = Card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Predicción Epidemiológica Regional")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Modelación estadística de 4 semanas para la región costera de Jalisco · Casos estimados (no confirmados)")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        layout.addStretch()

        layout.addWidget(QLabel("Enfermedad:"))
        self.combo_disease = QComboBox()
        self.combo_disease.addItem("Dengue (Transmisible)", "dengue")
        self.combo_disease.currentIndexChanged.connect(self._on_disease_changed)
        layout.addWidget(self.combo_disease)

        self.btn_refresh = QPushButton("↻ Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_prediction)
        layout.addWidget(self.btn_refresh)

        return card

    def _build_banners(self, parent_layout: QVBoxLayout) -> None:
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px;")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("⟳ Consultando modelo predictivo desde la API...")
        lbl.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(lbl)
        parent_layout.addWidget(self.loading_bar)

        self.error_banner = QFrame()
        self.error_banner.setVisible(False)
        self.error_banner.setStyleSheet("background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 6px;")
        e_layout = QHBoxLayout(self.error_banner)
        e_layout.setContentsMargins(12, 6, 12, 6)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #991B1B; font-weight: 600; font-size: 12px;")
        e_layout.addWidget(self.error_label)
        parent_layout.addWidget(self.error_banner)

        self.success_banner = QFrame()
        self.success_banner.setVisible(False)
        self.success_banner.setStyleSheet("background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 8px;")
        s_layout = QHBoxLayout(self.success_banner)
        s_layout.setContentsMargins(12, 6, 12, 6)
        self.success_label = QLabel()
        self.success_label.setStyleSheet("color: #15803D; font-weight: 700; font-size: 12px;")
        s_layout.addWidget(self.success_label)
        parent_layout.addWidget(self.success_banner)

    def _build_admin_panel(self) -> None:
        is_admin = self.user and self.user.role == UserRole.ADMIN

        p_title = QLabel("Generar / Registrar Predicción (POST /predicciones/)")
        p_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #123B4A;")
        self.admin_layout.addWidget(p_title)

        # Technical ML Model Status Notice
        notice = QFrame()
        notice.setStyleSheet("background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 6px; padding: 8px;")
        nl = QVBoxLayout(notice)
        nl.setContentsMargins(8, 6, 8, 6)
        nl.setSpacing(2)
        n_head = QLabel("ℹ Estado de Conexión del Modelo de Machine Learning:")
        n_head.setStyleSheet("color: #92400E; font-weight: 700; font-size: 11px;")
        n_body = QLabel(
            "El repositorio no incluye actualmente pesos binarios de un modelo entrenado (.pkl / .h5). "
            "Este módulo valida y permite registrar las 4 semanas oficiales directamente en el backend "
            "cuando el modelo ejecute su inferencia en el servidor o localmente."
        )
        n_body.setWordWrap(True)
        n_body.setStyleSheet("color: #78350F; font-size: 10.5px;")
        nl.addWidget(n_head)
        nl.addWidget(n_body)
        self.admin_layout.addWidget(notice)

        if not is_admin:
            cons_lbl = QLabel("🔒 Rol de Consulta: Solo Administradores pueden registrar nuevas predicciones.")
            cons_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic; margin-top: 8px;")
            self.admin_layout.addWidget(cons_lbl)
            self.admin_layout.addStretch()
            return

        # Input controls for Admin
        form_grid = QGridLayout()
        form_grid.setSpacing(8)

        form_grid.addWidget(QLabel("Año proyección:"), 0, 0)
        self.spin_anio = QSpinBox()
        self.spin_anio.setRange(2020, 2100)
        self.spin_anio.setValue(date.today().year)
        form_grid.addWidget(self.spin_anio, 0, 1)

        form_grid.addWidget(QLabel("Mes proyección:"), 1, 0)
        self.spin_mes = QSpinBox()
        self.spin_mes.setRange(1, 12)
        self.spin_mes.setValue(12)
        form_grid.addWidget(self.spin_mes, 1, 1)

        self.admin_layout.addLayout(form_grid)

        # 4 Weeks Spinners
        weeks_lbl = QLabel("Casos estimados por semana (exactamente 4 valores >= 0):")
        weeks_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #123B4A; margin-top: 6px;")
        self.admin_layout.addWidget(weeks_lbl)

        self.spin_w1 = QDoubleSpinBox()
        self.spin_w2 = QDoubleSpinBox()
        self.spin_w3 = QDoubleSpinBox()
        self.spin_w4 = QDoubleSpinBox()

        for sp, default_v in zip([self.spin_w1, self.spin_w2, self.spin_w3, self.spin_w4], [1.20, 1.96, 0.80, 0.50]):
            sp.setRange(0.0, 99999.0)
            sp.setDecimals(2)
            sp.setValue(default_v)

        w_grid = QGridLayout()
        w_grid.addWidget(QLabel("Semana 1:"), 0, 0)
        w_grid.addWidget(self.spin_w1, 0, 1)
        w_grid.addWidget(QLabel("Semana 2:"), 1, 0)
        w_grid.addWidget(self.spin_w2, 1, 1)
        w_grid.addWidget(QLabel("Semana 3:"), 2, 0)
        w_grid.addWidget(self.spin_w3, 2, 1)
        w_grid.addWidget(QLabel("Semana 4:"), 3, 0)
        w_grid.addWidget(self.spin_w4, 3, 1)
        self.admin_layout.addLayout(w_grid)

        # Submit button
        self.btn_submit_pred = QPushButton("⚡ Registrar Predicción Oficial")
        self.btn_submit_pred.setObjectName("actionButton")
        self.btn_submit_pred.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit_pred.setStyleSheet("background-color: #123B4A; color: white; border-radius: 6px; padding: 8px 16px; font-weight: 700; margin-top: 10px;")
        self.btn_submit_pred.clicked.connect(self._submit_prediction)
        self.admin_layout.addWidget(self.btn_submit_pred)

        self.admin_layout.addStretch()

    # -------------------------------------------------------------------------
    # Actions & Rendering
    # -------------------------------------------------------------------------

    def _on_disease_changed(self) -> None:
        self.current_enfermedad = self.combo_disease.currentData() or "dengue"
        self.refresh_prediction()

    def refresh_prediction(self) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = PredictionsWorker(
            epi_service=self.epi_service,
            action="fetch",
            enfermedad=self.current_enfermedad,
        )
        worker.signals.pred_loaded.connect(self._on_pred_loaded)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_worker_finished(self) -> None:
        self.is_loading = False
        self.btn_refresh.setEnabled(True)
        self.loading_bar.setVisible(False)

    def _on_error_occurred(self, message: str, status: int) -> None:
        self.error_banner.setVisible(True)
        if status == 401:
            self.error_label.setText("Sesión expirada o no autorizada (HTTP 401).")
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.error_label.setText("No tienes permiso para consultar o generar predicciones (HTTP 403).")
        else:
            self.error_label.setText(f"Error de comunicación con la API: {message}")

    def _on_pred_loaded(self, data: dict[str, Any], enfermedades: list[dict[str, Any]]) -> None:
        self.error_banner.setVisible(False)

        if enfermedades:
            # The API contract defines predictions only for transmissible
            # diseases (currently dengue). Do not offer chronic conditions
            # here, because they are statistical data only.
            predictable = [item for item in enfermedades if item.get("tipo") == "transmisible"]
            self.predictable_diseases = {
                str(item.get("clave")) for item in predictable if item.get("clave")
            }
            if not self.predictable_diseases:
                self.predictable_diseases = {"dengue"}
            current = self.combo_disease.currentData()
            self.combo_disease.blockSignals(True)
            self.combo_disease.clear()
            for d in predictable:
                clave = d.get("clave", "")
                nombre = d.get("nombre", clave)
                tipo = d.get("tipo", "")
                self.combo_disease.addItem(f"{nombre} ({tipo.capitalize()})", clave)
            idx = self.combo_disease.findData(current)
            self.combo_disease.setCurrentIndex(idx if idx >= 0 else 0)
            self.combo_disease.blockSignals(False)
            self.current_enfermedad = self.combo_disease.currentData() or "dengue"

        pred = data.get("prediccion")
        self._render_prediction(pred)

    def _render_empty(self) -> None:
        while self.disp_content_layout.count():
            item = self.disp_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        empty = EmptyStateWidget(
            icon="📊",
            title="Sin predicción activa",
            description="No se ha recuperado ninguna proyección epidemiológica para el periodo actual.",
        )
        self.disp_content_layout.addWidget(empty)

    def _render_prediction(self, pred: dict[str, Any] | None) -> None:
        while self.disp_content_layout.count():
            item = self.disp_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pred or not pred.get("semanas"):
            self._render_empty()
            return

        anio = pred.get("anio", 2026)
        mes = pred.get("mes", "--")
        semanas = pred.get("semanas", [])
        total = pred.get("total", sum(s for s in semanas if s is not None))
        creado_por = pred.get("creado_por", "Sistema")
        creada_en = str(pred.get("creado_en", "--"))[:16].replace("T", " ")

        # Header Title
        title_box = QFrame()
        title_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px;")
        tl = QVBoxLayout(title_box)
        tl.setContentsMargins(10, 8, 10, 8)

        t_lbl = QLabel(f"Proyección Oficial: Periodo Mes {mes} / {anio}")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub_lbl = QLabel(f"Enfermedad: {self.current_enfermedad.upper()} · Creado por: <b>{creado_por}</b> ({creada_en})")
        sub_lbl.setStyleSheet("font-size: 11px; color: #647C8C;")
        tl.addWidget(t_lbl)
        tl.addWidget(sub_lbl)
        self.disp_content_layout.addWidget(title_box)

        # 4 Weeks Grid
        weeks_lbl = QLabel("Estimación semanal proyectada con variables meteorológicas:")
        weeks_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #123B4A; margin-top: 4px;")
        self.disp_content_layout.addWidget(weeks_lbl)

        grid = QGridLayout()
        grid.setSpacing(10)
        for idx, val in enumerate(semanas[:4], start=1):
            val_txt = f"{val:.2f}" if isinstance(val, (int, float)) else str(val) if val is not None else "--"
            card = WeeklyCard(f"Semana {idx}", val_txt)
            grid.addWidget(card, 0, idx - 1)
        self.disp_content_layout.addLayout(grid)

        # Total Card
        tot_card = QFrame()
        tot_card.setStyleSheet("background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 12px;")
        tcl = QHBoxLayout(tot_card)
        tcl.setContentsMargins(14, 10, 14, 10)
        tot_val = QLabel(f"Total proyectado mensual: <b>{total:.2f} casos estimados</b>")
        tot_val.setStyleSheet("font-size: 15px; color: #15803D; font-weight: 700;")
        tcl.addWidget(tot_val)
        tcl.addStretch()
        note = QLabel("Modelo predictivo regional (Costa de Jalisco)")
        note.setStyleSheet("font-size: 11px; color: #166534;")
        tcl.addWidget(note)
        self.disp_content_layout.addWidget(tot_card)

        # Disclaimer
        disc = QLabel(
            "⚠️ Nota institucional: Los valores semanales y mensuales corresponden a estimaciones probabilísticas "
            "obtenidas a partir de covariables climáticas y registros históricos. No representan casos confirmados de dengue."
        )
        disc.setWordWrap(True)
        disc.setStyleSheet("font-size: 10.5px; color: #647C8C; font-style: italic; margin-top: 6px;")
        self.disp_content_layout.addWidget(disc)
        self.disp_content_layout.addStretch()

    def _submit_prediction(self) -> None:
        if not (self.user and self.user.role == UserRole.ADMIN):
            QMessageBox.warning(self, "Acceso restringido", "Solo administradores pueden generar predicciones.")
            return
        if self.current_enfermedad not in self.predictable_diseases:
            QMessageBox.warning(
                self,
                "Enfermedad no predictiva",
                "Solo las enfermedades transmisibles disponibles pueden registrarse como predicción.",
            )
            return

        semanas = [
            float(self.spin_w1.value()),
            float(self.spin_w2.value()),
            float(self.spin_w3.value()),
            float(self.spin_w4.value()),
        ]

        payload = {
            "enfermedad": self.current_enfermedad,
            "anio": int(self.spin_anio.value()),
            "mes": int(self.spin_mes.value()),
            "semanas": semanas,
        }

        resp = QMessageBox.question(
            self,
            "Confirmar Registro de Predicción",
            f"¿Deseas enviar la predicción de {payload['enfermedad'].upper()} para el mes {payload['mes']}/{payload['anio']} "
            f"con un total estimado de {sum(semanas):.2f} casos?\n\n"
            "Si la proyección supera al año anterior, el backend generará una alerta pendiente de revisión.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.loading_bar.setVisible(True)
        self.btn_submit_pred.setEnabled(False)

        worker = PredictionsWorker(
            epi_service=self.epi_service,
            action="create",
            create_payload=payload,
        )
        worker.signals.pred_created.connect(self._on_pred_created)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_pred_created(self, res: dict[str, Any]) -> None:
        alerta = res.get("alerta")
        msg = f"✓ Predicción registrada exitosamente (Total: {res.get('total')} casos)."
        if alerta:
            msg += " ⚠️ Se generó una alerta epidemiológica pendiente de revisión oficial."
        self.success_label.setText(msg)
        self.success_banner.setVisible(True)
        self.refresh_prediction()
