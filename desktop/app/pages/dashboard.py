"""Dashboard epidemiológico administrativo de la región costera de Jalisco.

Sprint 2 implementation:
- Consumes exclusively official endpoints from API_ESCRITORIO.md
- Non-blocking asynchronous data fetching with PySide6 QThreadPool
- Real Matplotlib charts for monthly epidemiological cases and climate variables
- Weekly forecast cards with clear distinction between predictions and confirmed cases
- Recent alerts table with direct navigation to alerts module
- Role-based permissions enforcement
- Responsive layout with loading, error, and empty states
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.components.chart import ClimateEvolutionChart, EpidemiologicalTrendChart
from app.components.widgets import AlertBadge, Card, EmptyStateWidget, GridReflow, MetricCard, PanelTitle, WeeklyCard
from app.core.config import config
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient
from app.services.statistics_service import StatisticsService


class DashboardWorkerSignals(QObject):
    """Signals for asynchronous background data loading."""
    data_loaded = Signal(dict)
    error_occurred = Signal(str, int)
    finished = Signal()


class DashboardWorker(QRunnable):
    """Fetches dashboard API endpoints in a background thread without blocking UI."""

    def __init__(self, api_client: ApiClient, stats_service: StatisticsService, enfermedad: str, anio: int) -> None:
        super().__init__()
        self.api_client = api_client
        self.stats_service = stats_service
        self.enfermedad = enfermedad
        self.anio = anio
        self.signals = DashboardWorkerSignals()

    def run(self) -> None:
        try:
            data = self.stats_service.fetch_dashboard_data(
                api_client=self.api_client,
                enfermedad=self.enfermedad,
                anio=self.anio,
            )
            try:
                self.signals.data_loaded.emit(data)
            except RuntimeError:
                pass
        except ApiError as err:
            status = err.status or 0
            message = str(err.data) if err.data else "Error al consultar la API"
            try:
                self.signals.error_occurred.emit(message, status)
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


class DashboardPage(QWidget):
    """Main administrative dashboard for epidemiological surveillance."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        on_navigate_to_alerts: Callable[[], None] | None = None,
        statistics_service: StatisticsService | None = None,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.user = user or User("Administrador", "admin@hackajal.salud.gob.mx", UserRole.ADMIN, "Secretaría de Salud Jalisco")
        self.api_client = api_client or ApiClient()
        self.on_navigate_to_alerts = on_navigate_to_alerts
        self.stats_service = statistics_service or StatisticsService()

        # State
        self.current_disease = "dengue"
        self.current_year = date.today().year
        self.is_loading = False
        self.enfermedades_catalog: list[dict[str, Any]] = [
            {"clave": "dengue", "nombre": "Dengue", "tipo": "transmisible"},
            {"clave": "dm2", "nombre": "Diabetes mellitus tipo 2", "tipo": "cronica"},
        ]

        # Root layout with scroll support
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Main scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(18, 14, 18, 18)
        self.content_layout.setSpacing(14)

        # 1. Header & Controls
        self._build_header()

        # 2. Status / Error banner
        self._build_status_banner()

        # 3. Statistical summary cards container
        self.metrics_container = QWidget()
        self.metrics_layout = QGridLayout(self.metrics_container)
        self.metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_layout.setSpacing(14)
        self.content_layout.addWidget(self.metrics_container)

        # 4. Charts row (Epidemiological evolution + Climate)
        self._build_charts_section()

        # 5. Lower row (Predictions + Recent alerts)
        self._build_lower_section()

        # Se reacomodan solas según el ancho de la ventana
        self._reflow_metrics = GridReflow(self, self.metrics_layout, 230, 3)
        GridReflow(self, self.charts_row, 560, 2)
        GridReflow(self, self.lower_row, 560, 2)

        scroll.setWidget(self.content_container)
        root.addWidget(scroll)

        # Initial data load
        if auto_refresh:
            self.refresh_data()

    # -------------------------------------------------------------------------
    # Header & Controls
    # -------------------------------------------------------------------------

    def _build_header(self) -> None:
        header_card = Card()
        layout = QVBoxLayout(header_card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()

        # Institutional Identity
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        app_title = QLabel("Resumen")
        app_title.setObjectName("pageTitle")
        app_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #123B4A;")
        self.subtitle_label = QLabel(
            f"Región Costa de Jalisco (14 municipios) · {self.current_year}"
        )
        self.subtitle_label.setObjectName("muted")
        self.subtitle_label.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_block.addWidget(app_title)
        title_block.addWidget(self.subtitle_label)
        top_row.addLayout(title_block)

        top_row.addStretch()

        if config.is_mock:
            demo_badge = QLabel("Datos de prueba")
            demo_badge.setObjectName("demoBadge")
            top_row.addWidget(demo_badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top_row)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        # Disease Filter
        filter_bar.addWidget(QLabel("Enfermedad:"))
        self.combo_disease = QComboBox()
        self.combo_disease.setMinimumWidth(180)
        self.combo_disease.currentIndexChanged.connect(self._on_disease_changed)
        filter_bar.addWidget(self.combo_disease)

        # Year Filter
        filter_bar.addSpacing(10)
        filter_bar.addWidget(QLabel("Año:"))
        self.combo_year = QComboBox()
        self.combo_year.setMinimumWidth(90)
        for yr in range(self.current_year, self.current_year - 3, -1):
            self.combo_year.addItem(str(yr), yr)
        self.combo_year.currentIndexChanged.connect(self._on_year_changed)
        filter_bar.addWidget(self.combo_year)

        filter_bar.addStretch()

        # Refresh button
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_data)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)
        self.content_layout.addWidget(header_card)

    def _build_status_banner(self) -> None:
        self.status_banner = QFrame()
        self.status_banner.setVisible(False)
        self.status_banner.setStyleSheet("""
            .QFrame {
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QHBoxLayout(self.status_banner)
        layout.setContentsMargins(14, 8, 14, 8)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #991B1B; font-weight: 600; font-size: 12px;")
        self.btn_retry = QPushButton("Reintentar")
        self.btn_retry.setObjectName("retryButton")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.clicked.connect(self.refresh_data)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.btn_retry)
        self.content_layout.addWidget(self.status_banner)

        # Loading notification bar
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("""
            .QFrame {
                background-color: #E0F2FE;
                border: 1px solid #BAE6FD;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        load_layout = QHBoxLayout(self.loading_bar)
        load_layout.setContentsMargins(14, 6, 14, 6)
        self.loading_label = QLabel("Cargando información…")
        self.loading_label.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        load_layout.addWidget(self.loading_label)
        self.content_layout.addWidget(self.loading_bar)

    # -------------------------------------------------------------------------
    # Charts Section
    # -------------------------------------------------------------------------

    def _build_charts_section(self) -> None:
        self.charts_row = QGridLayout()
        self.charts_row.setSpacing(14)

        # Left: Epidemiological Evolution Chart Card
        self.card_trend = Card()
        self.trend_layout = QVBoxLayout(self.card_trend)
        self.trend_layout.setContentsMargins(14, 12, 14, 12)
        self.trend_title = PanelTitle(
            "Casos por mes",
            "Costa Sur y Costa-Sierra Occidental",
        )
        self.trend_layout.addWidget(self.trend_title)
        self.trend_chart_container = QWidget()
        self.trend_chart_layout = QVBoxLayout(self.trend_chart_container)
        self.trend_chart_layout.setContentsMargins(0, 6, 0, 0)
        self.trend_layout.addWidget(self.trend_chart_container)

        # Right: Climate Evolution Chart Card
        self.card_climate = Card()
        self.climate_layout = QVBoxLayout(self.card_climate)
        self.climate_layout.setContentsMargins(14, 12, 14, 12)
        self.climate_title = PanelTitle(
            "Clima",
            "Temperatura, humedad y precipitación mensual",
        )
        self.climate_layout.addWidget(self.climate_title)
        self.climate_chart_container = QWidget()
        self.climate_chart_layout = QVBoxLayout(self.climate_chart_container)
        self.climate_chart_layout.setContentsMargins(0, 6, 0, 0)
        self.climate_layout.addWidget(self.climate_chart_container)

        self.charts_row.addWidget(self.card_trend, 0, 0)
        self.charts_row.addWidget(self.card_climate, 0, 1)
        self.charts_row.setColumnStretch(0, 1)
        self.charts_row.setColumnStretch(1, 1)

        self.content_layout.addLayout(self.charts_row)

    # -------------------------------------------------------------------------
    # Predictions & Alerts Section
    # -------------------------------------------------------------------------

    def _build_lower_section(self) -> None:
        self.lower_row = QGridLayout()
        self.lower_row.setSpacing(14)

        # Left: Predictions Panel
        self.card_prediction = Card()
        self.pred_layout = QVBoxLayout(self.card_prediction)
        self.pred_layout.setContentsMargins(14, 12, 14, 12)
        self.pred_layout.setSpacing(10)

        pred_header = QHBoxLayout()
        pred_title = QLabel("Predicción")
        pred_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #123B4A;")
        pred_badge = QLabel("Estimado")
        pred_badge.setObjectName("predictionBadge")
        pred_header.addWidget(pred_title)
        pred_header.addStretch()
        pred_header.addWidget(pred_badge)
        self.pred_layout.addLayout(pred_header)

        self.pred_content_container = QWidget()
        self.pred_content_layout = QVBoxLayout(self.pred_content_container)
        self.pred_content_layout.setContentsMargins(0, 0, 0, 0)
        self.pred_layout.addWidget(self.pred_content_container)

        # Right: Recent Alerts Panel
        self.card_alerts = Card()
        self.alerts_layout = QVBoxLayout(self.card_alerts)
        self.alerts_layout.setContentsMargins(14, 12, 14, 12)
        self.alerts_layout.setSpacing(10)

        alerts_header = QHBoxLayout()
        alerts_title = QLabel("Alertas recientes")
        alerts_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #123B4A;")
        alerts_header.addWidget(alerts_title)
        alerts_header.addStretch()

        self.btn_go_alerts = QPushButton("Ver alertas")
        self.btn_go_alerts.setObjectName("secondaryButton")
        self.btn_go_alerts.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.on_navigate_to_alerts:
            self.btn_go_alerts.clicked.connect(self.on_navigate_to_alerts)
        alerts_header.addWidget(self.btn_go_alerts)
        self.alerts_layout.addLayout(alerts_header)

        self.alerts_content_container = QWidget()
        self.alerts_content_layout = QVBoxLayout(self.alerts_content_container)
        self.alerts_content_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.addWidget(self.alerts_content_container)

        self.lower_row.addWidget(self.card_prediction, 0, 0)
        self.lower_row.addWidget(self.card_alerts, 0, 1)
        self.lower_row.setColumnStretch(0, 1)
        self.lower_row.setColumnStretch(1, 1)

        self.content_layout.addLayout(self.lower_row)

    # -------------------------------------------------------------------------
    # Asynchronous Data Refreshing
    # -------------------------------------------------------------------------

    def refresh_data(self) -> None:
        """Trigger asynchronous background retrieval of all dashboard endpoints."""
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.status_banner.setVisible(False)

        worker = DashboardWorker(
            api_client=self.api_client,
            stats_service=self.stats_service,
            enfermedad=self.current_disease,
            anio=self.current_year,
        )
        worker.signals.data_loaded.connect(self._on_data_loaded)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_worker_finished(self) -> None:
        self.is_loading = False
        self.btn_refresh.setEnabled(True)
        self.loading_bar.setVisible(False)

    def _on_error_occurred(self, message: str, status: int) -> None:
        self.status_banner.setVisible(True)
        if status == 401:
            self.status_label.setText("Tu sesión expiró. Vuelve a iniciar sesión.")
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.status_label.setText("Tu usuario no tiene permiso para ver esta información.")
        else:
            self.status_label.setText(f"Error al consultar la API: {message}")

    def _on_data_loaded(self, data: dict[str, Any]) -> None:
        """Update all visual cards, charts, prediction panel, and alerts table."""
        self.status_banner.setVisible(False)

        # 1. Update diseases combo catalog if loaded
        enfermedades = data.get("enfermedades") or []
        if enfermedades and len(enfermedades) != self.combo_disease.count():
            self.combo_disease.blockSignals(True)
            self.combo_disease.clear()
            for d in enfermedades:
                self.combo_disease.addItem(d["nombre"], d["clave"])
            # Restore current selection
            idx = self.combo_disease.findData(self.current_disease)
            if idx >= 0:
                self.combo_disease.setCurrentIndex(idx)
            self.combo_disease.blockSignals(False)

        # Update subtitle label
        self.subtitle_label.setText(
            f"Región Costa de Jalisco (14 municipios) · {self.current_year}"
        )

        # 2. Update Statistical Cards
        summary_cards = data.get("summary_cards") or []
        self._render_metric_cards(summary_cards)

        # 3. Update Charts
        stats = data.get("estadisticas") or {}
        casos_por_mes = stats.get("casos_por_mes")
        clima_por_mes = stats.get("clima_por_mes")
        self._render_charts(casos_por_mes, clima_por_mes)

        # 4. Update Predictions
        prediccion = data.get("prediccion")
        self._render_predictions(prediccion)

        # 5. Update Recent Alerts
        alertas = data.get("alertas_recientes") or []
        self._render_alerts(alertas)

    # -------------------------------------------------------------------------
    # Rendering Helpers
    # -------------------------------------------------------------------------

    def _render_metric_cards(self, cards_data: list[dict[str, Any]]) -> None:
        # Clear existing metric widgets
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Render up to 6 cards in a 2x3 grid
        for i, card_info in enumerate(cards_data):
            row = i // 3
            col = i % 3
            card_widget = MetricCard(
                label=card_info["label"],
                value=card_info["value"],
                note=card_info["note"],
                accent=card_info.get("accent", "#123B4A"),
            )
            self.metrics_layout.addWidget(card_widget, row, col)
        self._reflow_metrics.apply()

    def _render_charts(self, casos_por_mes: list[dict[str, Any]] | None, clima_por_mes: list[dict[str, Any]] | None) -> None:
        # Clear previous trend chart
        while self.trend_chart_layout.count():
            item = self.trend_chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        trend_canvas = EpidemiologicalTrendChart(casos_por_mes, self.current_year)
        self.trend_chart_layout.addWidget(trend_canvas)

        # Clear previous climate chart
        while self.climate_chart_layout.count():
            item = self.climate_chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        climate_canvas = ClimateEvolutionChart(clima_por_mes, self.current_year)
        self.climate_chart_layout.addWidget(climate_canvas)

    def _render_predictions(self, prediccion: dict[str, Any] | None) -> None:
        while self.pred_content_layout.count():
            item = self.pred_content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not prediccion or not prediccion.get("semanas"):
            empty = EmptyStateWidget(
                icon="📊",
                title="Sin predicción disponible",
                description="No existe un modelo predictivo generado para el periodo seleccionado. Los modelos se ejecutan mensualmente una vez registrados los datos climáticos y epidemiológicos.",
            )
            self.pred_content_layout.addWidget(empty)
            return

        semanas = prediccion.get("semanas", [])
        total = prediccion.get("total", sum(semanas))
        mes = prediccion.get("mes", "--")
        anio = prediccion.get("anio", self.current_year)
        creado_por = prediccion.get("creado_por", "Sistema")

        info_lbl = QLabel(f"Predicción para {mes}/{anio} · {creado_por}")
        info_lbl.setObjectName("muted")
        info_lbl.setStyleSheet("font-size: 11px; margin-bottom: 6px;")
        self.pred_content_layout.addWidget(info_lbl)

        # Grid for the 4 weeks
        grid = QGridLayout()
        grid.setSpacing(10)
        for idx, val in enumerate(semanas[:4], start=1):
            val_text = f"{val:.2f}" if isinstance(val, (int, float)) else str(val)
            card = WeeklyCard(f"Semana {idx}", val_text)
            grid.addWidget(card, 0, idx - 1)
        self.pred_content_layout.addLayout(grid)

        # Total highlight
        total_card = QFrame()
        total_card.setStyleSheet("""
            .QFrame {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        t_layout = QHBoxLayout(total_card)
        t_layout.setContentsMargins(12, 8, 12, 8)
        t_lbl = QLabel(f"Total estimado mensual: {total:.2f} casos")
        t_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #15803D;")
        t_note = QLabel("Costa de Jalisco")
        t_note.setStyleSheet("font-size: 11px; color: #166534;")
        t_layout.addWidget(t_lbl)
        t_layout.addStretch()
        t_layout.addWidget(t_note)

        self.pred_content_layout.addWidget(total_card)

    def _render_alerts(self, alertas: list[dict[str, Any]]) -> None:
        while self.alerts_content_layout.count():
            item = self.alerts_content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not alertas:
            empty = EmptyStateWidget(
                icon="🔔",
                title="Sin alertas recientes",
                description="No se encontraron alertas epidemiológicas emitidas para esta enfermedad en el periodo consultado.",
            )
            self.alerts_content_layout.addWidget(empty)
            return

        # Render alerts table
        table = QTableWidget(len(alertas), 5)
        table.setHorizontalHeaderLabels(["Enfermedad", "Periodo", "Estimados", "Año anterior", "Estado"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(min(220, 42 * len(alertas) + 40))

        for row_idx, alerta in enumerate(alertas):
            enfermedad_nom = alerta.get("enfermedad_nombre") or alerta.get("enfermedad", "Dengue")
            periodo = f"{alerta.get('mes', '--')}/{alerta.get('anio', '--')}"
            estimados = f"{alerta.get('casos_estimados', '--')}"
            anterior = f"{alerta.get('casos_anio_anterior', 'Sin dato')}"
            estado = alerta.get("estado", "pendiente")

            item_enf = QTableWidgetItem(enfermedad_nom)
            item_per = QTableWidgetItem(periodo)
            item_est = QTableWidgetItem(estimados)
            item_ant = QTableWidgetItem(anterior)

            table.setItem(row_idx, 0, item_enf)
            table.setItem(row_idx, 1, item_per)
            table.setItem(row_idx, 2, item_est)
            table.setItem(row_idx, 3, item_ant)

            # Estado with styled badge widget
            badge_container = QWidget()
            b_layout = QHBoxLayout(badge_container)
            b_layout.setContentsMargins(4, 4, 4, 4)
            b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_layout.addWidget(AlertBadge(estado))
            table.setCellWidget(row_idx, 4, badge_container)

        self.alerts_content_layout.addWidget(table)

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_disease_changed(self) -> None:
        selected_code = self.combo_disease.currentData()
        if selected_code and selected_code != self.current_disease:
            self.current_disease = selected_code
            self.refresh_data()

    def _on_year_changed(self) -> None:
        selected_year = self.combo_year.currentData()
        if selected_year and selected_year != self.current_year:
            self.current_year = int(selected_year)
            self.refresh_data()
