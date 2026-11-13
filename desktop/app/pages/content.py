"""Módulo de administración de contenidos, artículos y notas (Fase 4).

Permite:
- Consultar artículos y notas informativas para el portal institucional
- Filtrar por tipo (prevencion, articulo, nota), enfermedad y estado de publicación
- Visualizar detalles completos de cada contenido
- Crear contenido nuevo con validaciones estrictas (ADMIN)
- Editar contenido mediante PATCH con campos modificados (ADMIN)
- Publicar / Despublicar contenido en un clic (ADMIN)
- Eliminar contenido con confirmación y manejo de HTTP 204 (ADMIN)
- Control de permisos: CONSULTA es estrictamente de solo lectura
- Peticiones asíncronas con QThreadPool
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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import Card, EmptyStateWidget, MetricCard, PanelTitle
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient
from app.services.content_service import ContentService


class ContentWorkerSignals(QObject):
    content_loaded = Signal(list, list)  # items, enfermedades
    action_succeeded = Signal(str, dict)  # action_name, result_data
    error_occurred = Signal(str, int)
    finished = Signal()


class ContentWorker(QRunnable):
    """Background worker for content API calls."""

    def __init__(
        self,
        content_service: ContentService,
        action: str = "fetch",
        tipo: str | None = None,
        enfermedad: str | None = None,
        item_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.content_service = content_service
        self.action = action
        self.tipo = tipo
        self.enfermedad = enfermedad
        self.item_id = item_id
        self.payload = payload or {}
        self.signals = ContentWorkerSignals()

    def run(self) -> None:
        try:
            if self.action == "fetch":
                enfermedades = []
                try:
                    enfermedades = self.content_service.api_client.get("/enfermedades/") or []
                except Exception:
                    pass
                items = self.content_service.get_contenido(
                    tipo=self.tipo or None,
                    enfermedad=self.enfermedad or None,
                )
                try:
                    self.signals.content_loaded.emit(items, enfermedades)
                except RuntimeError:
                    pass

            elif self.action == "create":
                res = self.content_service.crear_contenido(**self.payload)
                try:
                    self.signals.action_succeeded.emit("create", res)
                except RuntimeError:
                    pass

            elif self.action == "patch" and self.item_id:
                res = self.content_service.actualizar_contenido(self.item_id, **self.payload)
                try:
                    self.signals.action_succeeded.emit("patch", res)
                except RuntimeError:
                    pass

            elif self.action == "delete" and self.item_id:
                self.content_service.eliminar_contenido(self.item_id)
                try:
                    self.signals.action_succeeded.emit("delete", {"id": self.item_id})
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
# Dialogs: Detalle, Creación y Edición
# =============================================================================

class ContentDetailDialog(QDialog):
    """Modal displaying full article/note information."""

    def __init__(self, item: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Contenido #{item.get('id')} · {item.get('titulo')}")
        self.setMinimumSize(600, 480)
        self.setStyleSheet("background-color: #FFFFFF; font-family: 'Segoe UI', Arial;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Header Badge Row
        h_row = QHBoxLayout()
        pub = item.get("publicado", False)
        status_badge = QLabel("PUBLICADO EN PORTAL" if pub else "BORRADOR INTERNO")
        status_badge.setStyleSheet(
            "background-color: #DCFCE7; color: #15803D; font-weight: 700; font-size: 10px; padding: 3px 8px; border-radius: 4px;"
            if pub else
            "background-color: #FEF3C7; color: #92400E; font-weight: 700; font-size: 10px; padding: 3px 8px; border-radius: 4px;"
        )
        tipo_lbl = QLabel(str(item.get("tipo", "articulo")).upper())
        tipo_lbl.setStyleSheet("background-color: #E2E8F0; color: #334155; font-weight: 700; font-size: 10px; padding: 3px 8px; border-radius: 4px;")

        h_row.addWidget(tipo_lbl)
        h_row.addSpacing(6)
        h_row.addWidget(status_badge)
        h_row.addStretch()
        layout.addLayout(h_row)

        # Title
        t_lbl = QLabel(item.get("titulo", "Sin título"))
        t_lbl.setWordWrap(True)
        t_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #123B4A;")
        layout.addWidget(t_lbl)

        # Metadata
        autor = item.get("autor", "Redacción HACKAJAL")
        fecha = str(item.get("fecha", ""))[:16].replace("T", " ")
        enf = item.get("enfermedad") or "General"
        meta_lbl = QLabel(f"Autor: <b>{autor}</b> · Fecha: {fecha} · Enfermedad: <b>{enf.upper()}</b>")
        meta_lbl.setStyleSheet("font-size: 11px; color: #647C8C;")
        layout.addWidget(meta_lbl)

        # Body Scroll Area
        body_box = QFrame()
        body_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px;")
        b_layout = QVBoxLayout(body_box)
        b_lbl = QLabel(item.get("cuerpo", "Sin contenido"))
        b_lbl.setWordWrap(True)
        b_lbl.setStyleSheet("font-size: 12.5px; color: #1E293B; line-height: 1.4;")
        b_layout.addWidget(b_lbl)
        layout.addWidget(body_box, 1)

        # Extra URLs if present
        if item.get("url_fuente") or item.get("imagen_url"):
            url_box = QVBoxLayout()
            if item.get("url_fuente"):
                f_lbl = QLabel(f"Fuente oficial: <a href='{item.get('url_fuente')}'>{item.get('url_fuente')}</a>")
                f_lbl.setOpenExternalLinks(True)
                f_lbl.setStyleSheet("font-size: 11px; color: #028090;")
                url_box.addWidget(f_lbl)
            if item.get("imagen_url"):
                img_lbl = QLabel(f"Imagen: <a href='{item.get('imagen_url')}'>{item.get('imagen_url')}</a>")
                img_lbl.setOpenExternalLinks(True)
                img_lbl.setStyleSheet("font-size: 11px; color: #028090;")
                url_box.addWidget(img_lbl)
            layout.addLayout(url_box)

        # Close
        btn_close = QPushButton("Cerrar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("background-color: #EAF0F5; color: #123B4A; border-radius: 6px; padding: 8px 18px; font-weight: 600;")
        b_row = QHBoxLayout()
        b_row.addStretch()
        b_row.addWidget(btn_close)
        layout.addLayout(b_row)


class ContentFormDialog(QDialog):
    """Modal for creating or editing articles and notes."""

    def __init__(self, item: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_edit = item is not None
        self.item = item or {}
        self.payload: dict[str, Any] = {}

        self.setWindowTitle("Editar Contenido" if self.is_edit else "Nuevo Contenido Informativo")
        self.setMinimumSize(580, 520)
        self.setStyleSheet("background-color: #FFFFFF; font-family: 'Segoe UI', Arial;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        # Title
        header_lbl = QLabel("Editar Artículo / Nota" if self.is_edit else "Crear Artículo o Nota para el Portal")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        layout.addWidget(header_lbl)

        # Form fields
        # Tipo & Enfermedad Row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Tipo de contenido *: "))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Artículo institucional", "articulo")
        self.combo_tipo.addItem("Medida de prevención", "prevencion")
        self.combo_tipo.addItem("Nota informativa / Comunicado", "nota")
        row1.addWidget(self.combo_tipo)

        row1.addSpacing(12)
        row1.addWidget(QLabel("Enfermedad: "))
        self.combo_enf = QComboBox()
        self.combo_enf.addItem("General / Sin asignar", "")
        self.combo_enf.addItem("Dengue", "dengue")
        self.combo_enf.addItem("Diabetes Mellitus Tipo 2", "dm2")
        row1.addWidget(self.combo_enf)
        layout.addLayout(row1)

        # Titulo with live counter
        t_header = QHBoxLayout()
        t_header.addWidget(QLabel("Título oficial *:"))
        t_header.addStretch()
        self.t_counter = QLabel("0 / 200 caracteres")
        self.t_counter.setStyleSheet("font-size: 11px; color: #647C8C;")
        t_header.addWidget(self.t_counter)
        layout.addLayout(t_header)

        self.edit_titulo = QLineEdit()
        self.edit_titulo.setPlaceholderText("Escribe un título claro y conciso (máximo 200 caracteres)...")
        self.edit_titulo.textChanged.connect(self._on_title_changed)
        layout.addWidget(self.edit_titulo)

        # Cuerpo
        layout.addWidget(QLabel("Cuerpo / Contenido *: "))
        self.edit_cuerpo = QTextEdit()
        self.edit_cuerpo.setPlaceholderText("Redacta aquí el texto oficial del artículo o recomendación preventiva...")
        layout.addWidget(self.edit_cuerpo)

        # URLs
        url_row = QHBoxLayout()
        url_box1 = QVBoxLayout()
        url_box1.addWidget(QLabel("URL de fuente (opcional):"))
        self.edit_fuente = QLineEdit()
        self.edit_fuente.setPlaceholderText("https://...")
        url_box1.addWidget(self.edit_fuente)

        url_box2 = QVBoxLayout()
        url_box2.addWidget(QLabel("URL de imagen (opcional):"))
        self.edit_img = QLineEdit()
        self.edit_img.setPlaceholderText("https://...")
        url_box2.addWidget(self.edit_img)

        url_row.addLayout(url_box1)
        url_row.addSpacing(10)
        url_row.addLayout(url_box2)
        layout.addLayout(url_row)

        # Publicado Checkbox
        self.chk_pub = QCheckBox("Publicar en el portal web (visible para la población)")
        self.chk_pub.setStyleSheet("font-size: 12px; font-weight: 600; color: #15803D;")
        layout.addWidget(self.chk_pub)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("background-color: #EAF0F5; color: #123B4A; border-radius: 6px; padding: 8px 16px; font-weight: 600;")

        self.btn_save = QPushButton("Guardar Cambios" if self.is_edit else "Crear Contenido")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setStyleSheet("background-color: #123B4A; color: white; border-radius: 6px; padding: 8px 20px; font-weight: 700;")
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        # Prepopulate if editing
        if self.is_edit:
            self._prepopulate()

    def _prepopulate(self) -> None:
        tipo = self.item.get("tipo", "articulo")
        idx_t = self.combo_tipo.findData(tipo)
        if idx_t >= 0:
            self.combo_tipo.setCurrentIndex(idx_t)

        enf = self.item.get("enfermedad") or ""
        idx_e = self.combo_enf.findData(enf)
        if idx_e >= 0:
            self.combo_enf.setCurrentIndex(idx_e)

        self.edit_titulo.setText(self.item.get("titulo", ""))
        self.edit_cuerpo.setPlainText(self.item.get("cuerpo", ""))
        self.edit_fuente.setText(self.item.get("url_fuente", ""))
        self.edit_img.setText(self.item.get("imagen_url", ""))
        self.chk_pub.setChecked(bool(self.item.get("publicado", False)))

    def _on_title_changed(self, text: str) -> None:
        length = len(text)
        self.t_counter.setText(f"{length} / 200 caracteres")
        if length > 200:
            self.t_counter.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 700;")
        else:
            self.t_counter.setStyleSheet("font-size: 11px; color: #647C8C;")

    def _on_save(self) -> None:
        titulo = self.edit_titulo.text().strip()
        cuerpo = self.edit_cuerpo.toPlainText().strip()
        tipo = self.combo_tipo.currentData()
        enfermedad = self.combo_enf.currentData() or None
        url_fuente = self.edit_fuente.text().strip()
        imagen_url = self.edit_img.text().strip()
        publicado = self.chk_pub.isChecked()

        if not titulo:
            self.error_label.setText("El título es obligatorio.")
            self.error_label.setVisible(True)
            return
        if len(titulo) > 200:
            self.error_label.setText("El título no puede exceder los 200 caracteres.")
            self.error_label.setVisible(True)
            return
        if not cuerpo:
            self.error_label.setText("El cuerpo del contenido es obligatorio.")
            self.error_label.setVisible(True)
            return

        if self.is_edit:
            # Send ONLY modified fields as required by contract
            changes: dict[str, Any] = {}
            if tipo != self.item.get("tipo"):
                changes["tipo"] = tipo
            if titulo != self.item.get("titulo"):
                changes["titulo"] = titulo
            if cuerpo != self.item.get("cuerpo"):
                changes["cuerpo"] = cuerpo
            if enfermedad != self.item.get("enfermedad"):
                changes["enfermedad"] = enfermedad
            if url_fuente != (self.item.get("url_fuente") or ""):
                changes["url_fuente"] = url_fuente
            if imagen_url != (self.item.get("imagen_url") or ""):
                changes["imagen_url"] = imagen_url
            if publicado != bool(self.item.get("publicado")):
                changes["publicado"] = publicado
            self.payload = changes
        else:
            self.payload = {
                "tipo": tipo,
                "titulo": titulo,
                "cuerpo": cuerpo,
                "enfermedad": enfermedad,
                "url_fuente": url_fuente,
                "imagen_url": imagen_url,
                "publicado": publicado,
            }

        self.accept()


# =============================================================================
# Main Content Management Page
# =============================================================================

class ContentPage(QWidget):
    """Articles, notes and citizen prevention content module."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        content_service: ContentService | None = None,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.user = user
        self.api_client = api_client or ApiClient()
        self.content_service = content_service or ContentService(self.api_client)

        self.raw_items: list[dict[str, Any]] = []
        self.is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # 1. Header & Filters
        root.addWidget(self._build_header())

        # 2. Status Banners
        self._build_banners(root)

        # 3. Indicators Row
        root.addWidget(self._build_indicators())

        # 4. Table Card
        root.addWidget(self._build_table_card(), 1)

        if auto_refresh:
            self.refresh_content()

    def _build_header(self) -> QWidget:
        header = Card()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Gestión de Artículos y Notas Informativas")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Publicación y difusión ciudadana para el portal de salud de Jalisco")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_row.addLayout(title_box)

        top_row.addStretch()

        # Admin Creation Button
        if self.user and self.user.role == UserRole.ADMIN:
            btn_create = QPushButton("＋ Redactar contenido")
            btn_create.setObjectName("actionButton")
            btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_create.setStyleSheet("background-color: #123B4A; color: white; padding: 7px 16px; border-radius: 6px; font-weight: 700;")
            btn_create.clicked.connect(self._open_create_dialog)
            top_row.addWidget(btn_create)

        self.btn_refresh = QPushButton("↻ Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_content)
        top_row.addWidget(self.btn_refresh)
        layout.addLayout(top_row)

        # Filters Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        # Tipo Filter
        filter_bar.addWidget(QLabel("Tipo:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Todos los tipos", "")
        self.combo_tipo.addItem("Artículo", "articulo")
        self.combo_tipo.addItem("Prevención", "prevencion")
        self.combo_tipo.addItem("Nota", "nota")
        self.combo_tipo.currentIndexChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.combo_tipo)

        # Enfermedad Filter
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Enfermedad:"))
        self.combo_enf = QComboBox()
        self.combo_enf.addItem("Todas las enfermedades", "")
        self.combo_enf.addItem("Dengue", "dengue")
        self.combo_enf.addItem("Diabetes Mellitus Tipo 2", "dm2")
        self.combo_enf.currentIndexChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.combo_enf)

        # Estado Publicación Filter (Local)
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Estado:"))
        self.combo_pub = QComboBox()
        self.combo_pub.addItem("Todos", "all")
        self.combo_pub.addItem("Publicados en portal", "published")
        self.combo_pub.addItem("Borradores internos", "draft")
        self.combo_pub.currentIndexChanged.connect(self._render_table)
        filter_bar.addWidget(self.combo_pub)

        # Search Bar
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar en título o cuerpo...")
        self.search_edit.textChanged.connect(self._render_table)
        self.search_edit.setMaximumWidth(200)
        filter_bar.addWidget(self.search_edit)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)
        return header

    def _build_banners(self, parent_layout: QVBoxLayout) -> None:
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px;")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("⟳ Conectando con la API de contenidos...")
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
        e_layout.addStretch()
        btn_retry = QPushButton("Reintentar")
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self.refresh_content)
        e_layout.addWidget(btn_retry)
        parent_layout.addWidget(self.error_banner)

        self.success_banner = QFrame()
        self.success_banner.setVisible(False)
        self.success_banner.setStyleSheet("background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 6px;")
        s_layout = QHBoxLayout(self.success_banner)
        s_layout.setContentsMargins(12, 6, 12, 6)
        self.success_label = QLabel()
        self.success_label.setStyleSheet("color: #15803D; font-weight: 700; font-size: 12px;")
        s_layout.addWidget(self.success_label)
        parent_layout.addWidget(self.success_banner)

    def _build_indicators(self) -> QWidget:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        self.card_total = MetricCard("Total de contenidos", "0", "Artículos, notas y prevenciones", "#123B4A")
        self.card_publicados = MetricCard("Publicados", "0", "Visibles en el portal ciudadano", "#15803D")
        self.card_borradores = MetricCard("Borradores", "0", "En edición interna", "#C47A27")

        grid.addWidget(self.card_total, 0, 0)
        grid.addWidget(self.card_publicados, 0, 1)
        grid.addWidget(self.card_borradores, 0, 2)
        return container

    def _build_table_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        t_head = QHBoxLayout()
        t_title = QLabel("Listado de Contenidos")
        t_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #123B4A;")
        t_head.addWidget(t_title)
        t_head.addStretch()
        self.count_lbl = QLabel("0 contenidos")
        self.count_lbl.setStyleSheet("font-size: 11px; color: #647C8C;")
        t_head.addWidget(self.count_lbl)
        layout.addLayout(t_head)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Tipo", "Enfermedad", "Título", "Autor", "Fecha", "Estado", "Acciones"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.setMinimumHeight(300)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        return card

    # -------------------------------------------------------------------------
    # Networking & Worker Dispatch
    # -------------------------------------------------------------------------

    def refresh_content(self) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = ContentWorker(
            content_service=self.content_service,
            action="fetch",
            tipo=self.combo_tipo.currentData() or None,
            enfermedad=self.combo_enf.currentData() or None,
        )
        worker.signals.content_loaded.connect(self._on_content_loaded)
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
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.error_label.setText("No tienes permiso para esta acción (HTTP 403).")
        elif status == 404:
            self.error_label.setText("Contenido no encontrado (HTTP 404). Se actualizó la lista.")
            self.refresh_content()
        else:
            self.error_label.setText(f"Error de comunicación con la API: {message}")

    def _on_content_loaded(self, items: list[dict[str, Any]], enfermedades: list[dict[str, Any]]) -> None:
        self.error_banner.setVisible(False)
        self.raw_items = items

        # Populate disease combo if backend returned diseases
        if enfermedades and self.combo_enf.count() <= 3:
            current = self.combo_enf.currentData()
            self.combo_enf.blockSignals(True)
            self.combo_enf.clear()
            self.combo_enf.addItem("Todas las enfermedades", "")
            for d in enfermedades:
                self.combo_enf.addItem(d.get("nombre", d.get("clave")), d.get("clave"))
            idx = self.combo_enf.findData(current)
            if idx >= 0:
                self.combo_enf.setCurrentIndex(idx)
            self.combo_enf.blockSignals(False)

        self._render_table()

    def _on_filter_changed(self) -> None:
        self.refresh_content()

    # -------------------------------------------------------------------------
    # Table Rendering
    # -------------------------------------------------------------------------

    def _get_filtered_items(self) -> list[dict[str, Any]]:
        items = self.raw_items
        pub_mode = self.combo_pub.currentData()
        if pub_mode == "published":
            items = [i for i in items if i.get("publicado") is True]
        elif pub_mode == "draft":
            items = [i for i in items if not i.get("publicado")]

        query = self.search_edit.text().strip().lower()
        if query:
            filtered = []
            for i in items:
                t = str(i.get("titulo", "")).lower()
                c = str(i.get("cuerpo", "")).lower()
                if query in t or query in c:
                    filtered.append(i)
            items = filtered
        return items

    def _render_table(self) -> None:
        items = self._get_filtered_items()

        # Update indicators
        total = len(self.raw_items)
        pub_cnt = sum(1 for i in self.raw_items if i.get("publicado"))
        draft_cnt = total - pub_cnt

        self.card_total.update_value(f"{total:,}")
        self.card_publicados.update_value(f"{pub_cnt:,}")
        self.card_borradores.update_value(f"{draft_cnt:,}")

        self.count_lbl.setText(f"{len(items)} de {total} contenido(s)")
        self.table.setRowCount(len(items))

        is_admin = self.user and self.user.role == UserRole.ADMIN

        for r, item in enumerate(items):
            cid = str(item.get("id", "--"))
            tipo = str(item.get("tipo", "articulo")).upper()
            enf = str(item.get("enfermedad") or "General").upper()
            titulo = str(item.get("titulo", ""))
            autor = str(item.get("autor", "Redacción"))
            fecha = str(item.get("fecha", ""))[:10]
            publicado = bool(item.get("publicado", False))

            it_id = QTableWidgetItem(f"#{cid}")
            it_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_tipo = QTableWidgetItem(tipo)
            it_tipo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_enf = QTableWidgetItem(enf)
            it_enf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_titulo = QTableWidgetItem(titulo)
            it_autor = QTableWidgetItem(autor)
            it_fecha = QTableWidgetItem(fecha)
            it_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(r, 0, it_id)
            self.table.setItem(r, 1, it_tipo)
            self.table.setItem(r, 2, it_enf)
            self.table.setItem(r, 3, it_titulo)
            self.table.setItem(r, 4, it_autor)
            self.table.setItem(r, 5, it_fecha)

            # Estado Badge
            badge_widget = QWidget()
            bw_layout = QHBoxLayout(badge_widget)
            bw_layout.setContentsMargins(4, 2, 4, 2)
            bw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_lbl = QLabel("Publicado" if publicado else "Borrador")
            badge_lbl.setStyleSheet(
                "background-color: #DCFCE7; color: #15803D; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;"
                if publicado else
                "background-color: #FEF3C7; color: #92400E; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;"
            )
            bw_layout.addWidget(badge_lbl)
            self.table.setCellWidget(r, 6, badge_widget)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Ver detalle button
            btn_view = QPushButton("👁️")
            btn_view.setToolTip("Ver detalle del contenido")
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("background-color: #EAF0F5; border: 1px solid #CBD5E1; border-radius: 4px; padding: 3px 6px; font-size: 11px;")
            btn_view.clicked.connect(lambda _, it=item: self._open_detail_dialog(it))
            act_layout.addWidget(btn_view)

            if is_admin:
                # Toggle publish button
                btn_pub = QPushButton("Despublicar" if publicado else "Publicar")
                btn_pub.setToolTip("Cambiar visibilidad en el portal")
                btn_pub.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pub.setStyleSheet(
                    "background-color: #64748B; color: white; border: none; border-radius: 4px; padding: 3px 7px; font-size: 10.5px; font-weight: 600;"
                    if publicado else
                    "background-color: #028090; color: white; border: none; border-radius: 4px; padding: 3px 7px; font-size: 10.5px; font-weight: 600;"
                )
                btn_pub.clicked.connect(lambda _, it=item: self._toggle_publish(it))
                act_layout.addWidget(btn_pub)

                # Edit button
                btn_edit = QPushButton("✎")
                btn_edit.setToolTip("Editar contenido")
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet("background-color: #EAF0F5; border: 1px solid #CBD5E1; border-radius: 4px; padding: 3px 6px; font-size: 11px;")
                btn_edit.clicked.connect(lambda _, it=item: self._open_edit_dialog(it))
                act_layout.addWidget(btn_edit)

                # Delete button
                btn_del = QPushButton("🗑️")
                btn_del.setToolTip("Eliminar contenido")
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet("background-color: #FEE2E2; border: 1px solid #FCA5A5; color: #DC2626; border-radius: 4px; padding: 3px 6px; font-size: 11px;")
                btn_del.clicked.connect(lambda _, it=item: self._prompt_delete(it))
                act_layout.addWidget(btn_del)

            self.table.setCellWidget(r, 7, act_widget)

    # -------------------------------------------------------------------------
    # Dialogs & CRUD Triggers
    # -------------------------------------------------------------------------

    def _open_detail_dialog(self, item: dict[str, Any]) -> None:
        dialog = ContentDetailDialog(item, self)
        dialog.exec()

    def _on_table_double_clicked(self) -> None:
        row = self.table.currentRow()
        items = self._get_filtered_items()
        if 0 <= row < len(items):
            self._open_detail_dialog(items[row])

    def _open_create_dialog(self) -> None:
        dialog = ContentFormDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            payload = dialog.payload
            self._execute_action("create", payload=payload)

    def _open_edit_dialog(self, item: dict[str, Any]) -> None:
        dialog = ContentFormDialog(item=item, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            changes = dialog.payload
            if not changes:
                QMessageBox.information(self, "Sin cambios", "No se detectaron modificaciones.")
                return
            self._execute_action("patch", item_id=item["id"], payload=changes)

    def _toggle_publish(self, item: dict[str, Any]) -> None:
        cid = item.get("id")
        current_pub = bool(item.get("publicado", False))
        new_pub = not current_pub
        action_str = "publicar en el portal web" if new_pub else "despublicar y pasar a borrador interno"

        resp = QMessageBox.question(
            self,
            "Confirmar cambio de publicación",
            f"¿Deseas {action_str} el contenido #{cid} ({item.get('titulo')})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._execute_action("patch", item_id=cid, payload={"publicado": new_pub})

    def _prompt_delete(self, item: dict[str, Any]) -> None:
        cid = item.get("id")
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar permanentemente el contenido #{cid}?\n\n'{item.get('titulo')}'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._execute_action("delete", item_id=cid)

    def _execute_action(self, action: str, item_id: int | None = None, payload: dict[str, Any] | None = None) -> None:
        self.loading_bar.setVisible(True)
        self.btn_refresh.setEnabled(False)

        worker = ContentWorker(
            content_service=self.content_service,
            action=action,
            item_id=item_id,
            payload=payload,
        )
        worker.signals.action_succeeded.connect(self._on_action_success)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_action_success(self, action_name: str, res: dict[str, Any]) -> None:
        if action_name == "create":
            self.success_label.setText(f"✓ Contenido #{res.get('id')} creado exitosamente.")
        elif action_name == "patch":
            self.success_label.setText(f"✓ Contenido #{res.get('id')} actualizado exitosamente.")
        elif action_name == "delete":
            self.success_label.setText(f"✓ Contenido #{res.get('id')} eliminado exitosamente.")
        self.success_banner.setVisible(True)
        self.refresh_content()
