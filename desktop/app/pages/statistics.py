"""Módulo de estadísticas epidemiológicas completas, crónicas y encuestas (Fase 3).

Implementado con:
- Consumo estricto de GET /estadisticas/, GET /estadisticas/encuesta/, GET /predicciones/
- Gráficas Matplotlib para casos históricos y variables climáticas (sin ceros inventados)
- Visualización de modelo predictivo semanal (Semanas 1-4 + total)
- Exploración de enfermedades crónicas con tabla detallada y filtro municipal selectivo
- Integración de encuestas comunitarias SUIVE
- Ejecución asíncrona mediante QThreadPool
"""
from __future__ import annotations

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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.components.chart import ClimateEvolutionChart, EpidemiologicalTrendChart, MunicipalDistributionChart
from app.components.widgets import Card, EmptyStateWidget, MetricCard, PanelTitle, WeeklyCard
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User
from app.services.api.client import ApiClient
from app.services.epidemiology_service import EpidemiologyService


class StatisticsWorkerSignals(QObject):
    data_loaded = Signal(dict, dict, dict, list, list)  # stats, encuesta, pred, municipios, enfermedades
    error_occurred = Signal(str, int)
    finished = Signal()


class StatisticsWorker(QRunnable):
    """Background worker for loading complete statistics data."""

    def __init__(
        self,
        epi_service: EpidemiologyService,
        enfermedad: str = "dengue",
        anio: int = 2026,
        municipio: str | None = None,
    ) -> None:
        super().__init__()
        self.epi_service = epi_service
        self.enfermedad = enfermedad
        self.anio = anio
        self.municipio = municipio
        self.signals = StatisticsWorkerSignals()

    def run(self) -> None:
        try:
            # 1. Fetch metadata
            municipios = []
            enfermedades = []
            try:
                municipios = self.epi_service.get_municipios() or []
                enfermedades = self.epi_service.get_enfermedades() or []
            except Exception:
                pass

            # 2. Fetch statistics
            stats = self.epi_service.get_estadisticas(
                enfermedad=self.enfermedad,
                anio=self.anio,
                municipio=self.municipio,
            )

            # 3. Fetch surveys
            encuesta = {}
            try:
                encuesta = self.epi_service.get_encuesta() or {}
            except Exception:
                pass

            # 4. Fetch predictions
            pred = {}
            try:
                pred = self.epi_service.get_prediccion(enfermedad=self.enfermedad) or {}
            except Exception:
                pass

            try:
                self.signals.data_loaded.emit(stats, encuesta, pred, municipios, enfermedades)
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


class StatisticsPage(QWidget):
    """Complete statistics, chronic diseases and surveys page."""

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

        # The API defaults to the current year. Keep the desktop filter aligned
        # with that contract instead of leaving a historical year hard-coded.
        self.current_year = date.today().year
        self.current_disease = "dengue"
        self.current_municipality: str | None = None
        self.disease_types: dict[str, str] = {
            "dengue": "transmisible",
            "dm2": "cronica",
        }
        self.is_loading = False

        # Root scrollable layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(18, 14, 18, 18)
        self.content_layout.setSpacing(12)

        # 1. Header & Filters
        self._build_header()

        # 2. Status Banners
        self._build_banners()

        # 3. Dynamic Metrics Row
        self._build_metrics_row()

        # 4. Charts Section (Monthly Cases + Regional Climate)
        self._build_charts_section()

        # 5. Prediction & Surveys Section
        self._build_pred_and_surveys_section()

        # 6. Chronic Diseases Section (Table + Filter)
        self._build_chronic_section()

        scroll.setWidget(self.container)
        root.addWidget(scroll)

        if auto_refresh:
            self.refresh_statistics()

    def _build_header(self) -> None:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Reportes y Estadísticas Epidemiológicas")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Análisis temporal, meteorológico, enfermedades crónicas y encuestas territoriales")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_row.addLayout(title_box)

        top_row.addStretch()
        self.btn_refresh = QPushButton("↻ Actualizar estadísticas")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_statistics)
        top_row.addWidget(self.btn_refresh)
        layout.addLayout(top_row)

        # Filters Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        # Enfermedad
        filter_bar.addWidget(QLabel("Enfermedad:"))
        self.combo_disease = QComboBox()
        self.combo_disease.addItem("Dengue (Transmisible)", "dengue")
        self.combo_disease.addItem("Diabetes Mellitus Tipo 2 (Crónica)", "dm2")
        self.combo_disease.currentIndexChanged.connect(self._on_filters_changed)
        filter_bar.addWidget(self.combo_disease)

        # Año
        filter_bar.addSpacing(6)
        filter_bar.addWidget(QLabel("Año:"))
        self.combo_year = QComboBox()
        for y in range(self.current_year, self.current_year - 5, -1):
            self.combo_year.addItem(str(y), y)
        self.combo_year.currentIndexChanged.connect(self._on_filters_changed)
        filter_bar.addWidget(self.combo_year)

        # Municipio (Strictly for chronic diseases per contract)
        filter_bar.addSpacing(6)
        self.lbl_municipio = QLabel("Municipio (Solo crónicas):")
        filter_bar.addWidget(self.lbl_municipio)
        self.combo_mun = QComboBox()
        self.combo_mun.addItem("Todos los municipios / Estatal", "")
        self.combo_mun.currentIndexChanged.connect(self._on_filters_changed)
        filter_bar.addWidget(self.combo_mun)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)
        self.content_layout.addWidget(card)

    def _build_banners(self) -> None:
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px;")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("⟳ Consultando estadísticas epidemiológicas desde la API...")
        lbl.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(lbl)
        self.content_layout.addWidget(self.loading_bar)

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
        btn_retry.clicked.connect(self.refresh_statistics)
        e_layout.addWidget(btn_retry)
        self.content_layout.addWidget(self.error_banner)

    def _build_metrics_row(self) -> None:
        self.metrics_container = QWidget()
        self.metrics_grid = QGridLayout(self.metrics_container)
        self.metrics_grid.setContentsMargins(0, 0, 0, 0)
        self.metrics_grid.setSpacing(10)

        self.card_casos = MetricCard("Casos registrados", "--", "En el año epidemiológico", "#123B4A")
        self.card_temp = MetricCard("Temperatura promedio", "--", "Promedio regional anual", "#C47A27")
        self.card_hum = MetricCard("Humedad promedio", "--", "Promedio regional anual", "#028090")
        self.card_prec = MetricCard("Precipitación acumulada", "--", "Total acumulado anual", "#2B6B55")

        self.metrics_grid.addWidget(self.card_casos, 0, 0)
        self.metrics_grid.addWidget(self.card_temp, 0, 1)
        self.metrics_grid.addWidget(self.card_hum, 0, 2)
        self.metrics_grid.addWidget(self.card_prec, 0, 3)

        self.content_layout.addWidget(self.metrics_container)

    def _build_charts_section(self) -> None:
        self.charts_row = QGridLayout()
        self.charts_row.setSpacing(12)

        # Trend Chart Card
        self.card_trend = Card()
        self.trend_layout = QVBoxLayout(self.card_trend)
        self.trend_layout.setContentsMargins(14, 12, 14, 12)
        self.trend_layout.addWidget(PanelTitle("Evolución mensual de casos", "Casos registrados por mes · Sin ceros inventados"))
        self.trend_canvas_box = QWidget()
        self.trend_canvas_layout = QVBoxLayout(self.trend_canvas_box)
        self.trend_canvas_layout.setContentsMargins(0, 6, 0, 0)
        self.trend_layout.addWidget(self.trend_canvas_box)

        # Climate Chart Card
        self.card_climate = Card()
        self.climate_layout = QVBoxLayout(self.card_climate)
        self.climate_layout.setContentsMargins(14, 12, 14, 12)
        self.climate_layout.addWidget(PanelTitle("Variables climáticas", "Temperatura (°C), Humedad (%) y Lluvia (mm)"))
        self.climate_canvas_box = QWidget()
        self.climate_canvas_layout = QVBoxLayout(self.climate_canvas_box)
        self.climate_canvas_layout.setContentsMargins(0, 6, 0, 0)
        self.climate_layout.addWidget(self.climate_canvas_box)

        self.charts_row.addWidget(self.card_trend, 0, 0)
        self.charts_row.addWidget(self.card_climate, 0, 1)
        self.charts_row.setColumnStretch(0, 1)
        self.charts_row.setColumnStretch(1, 1)

        self.content_layout.addLayout(self.charts_row)

    def _build_pred_and_surveys_section(self) -> None:
        self.pred_survey_row = QGridLayout()
        self.pred_survey_row.setSpacing(12)

        # Left: Model Prediction
        self.card_pred = Card()
        self.pred_box_layout = QVBoxLayout(self.card_pred)
        self.pred_box_layout.setContentsMargins(14, 12, 14, 12)
        self.pred_box_layout.setSpacing(8)

        p_header = QHBoxLayout()
        p_title = QLabel("Proyección Epidemiológica")
        p_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #123B4A;")
        p_badge = QLabel("MODELO PREDICTIVO (CASOS ESTIMADOS)")
        p_badge.setObjectName("predictionBadge")
        p_header.addWidget(p_title)
        p_header.addStretch()
        p_header.addWidget(p_badge)
        self.pred_box_layout.addLayout(p_header)

        self.pred_container = QWidget()
        self.pred_layout = QVBoxLayout(self.pred_container)
        self.pred_layout.setContentsMargins(0, 4, 0, 0)
        self.pred_box_layout.addWidget(self.pred_container)

        # Right: Survey Responses
        self.card_survey = Card()
        self.survey_box_layout = QVBoxLayout(self.card_survey)
        self.survey_box_layout.setContentsMargins(14, 12, 14, 12)
        self.survey_box_layout.setSpacing(8)
        self.survey_box_layout.addWidget(PanelTitle("Encuestas Territoriales", "Participación comunitaria por municipio"))

        self.survey_container = QWidget()
        self.survey_layout = QVBoxLayout(self.survey_container)
        self.survey_layout.setContentsMargins(0, 4, 0, 0)
        self.survey_box_layout.addWidget(self.survey_container)

        self.pred_survey_row.addWidget(self.card_pred, 0, 0)
        self.pred_survey_row.addWidget(self.card_survey, 0, 1)
        self.pred_survey_row.setColumnStretch(0, 1)
        self.pred_survey_row.setColumnStretch(1, 1)

        self.content_layout.addLayout(self.pred_survey_row)

    def _build_chronic_section(self) -> None:
        self.card_chronic = Card()
        self.chronic_layout = QVBoxLayout(self.card_chronic)
        self.chronic_layout.setContentsMargins(14, 12, 14, 12)
        self.chronic_layout.setSpacing(10)

        ch_header = QHBoxLayout()
        ch_title = QLabel("Enfermedades Crónicas (Morbilidad y Tasa)")
        ch_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #123B4A;")
        ch_sub = QLabel("Datos SUIVE / DGE Anuario de Morbilidad · Filtrable por municipio")
        ch_sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        ch_header.addWidget(ch_title)
        ch_header.addSpacing(10)
        ch_header.addWidget(ch_sub)
        ch_header.addStretch()
        self.chronic_count = QLabel("0 registros")
        self.chronic_count.setStyleSheet("font-size: 11px; color: #647C8C;")
        ch_header.addWidget(self.chronic_count)
        self.chronic_layout.addLayout(ch_header)

        self.chronic_table = QTableWidget()
        self.chronic_table.setColumnCount(11)
        self.chronic_table.setHorizontalHeaderLabels([
            "Indicador", "Ámbito", "Región", "Año", "Sexo", "Grupo Edad",
            "Institución", "Valor", "Unidad", "Fuente", "Municipio"
        ])
        self.chronic_table.verticalHeader().setVisible(False)
        self.chronic_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.chronic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.chronic_table.setAlternatingRowColors(True)
        self.chronic_table.setMinimumHeight(240)
        self.chronic_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.chronic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.chronic_layout.addWidget(self.chronic_table)

        self.content_layout.addWidget(self.card_chronic)

    # -------------------------------------------------------------------------
    # Actions & Handlers
    # -------------------------------------------------------------------------

    def _on_filters_changed(self) -> None:
        self.current_disease = self.combo_disease.currentData() or "dengue"
        self.current_year = int(self.combo_year.currentData() or 2026)
        self.current_municipality = self.combo_mun.currentData() or None

        # Enable/disable municipal filter based on chronic disease
        is_chronic = self.disease_types.get(self.current_disease) == "cronica"
        if not is_chronic:
            # The endpoint explicitly accepts municipio only for chronic
            # conditions; never carry a stale municipality into dengue queries.
            self.current_municipality = None
        self.combo_mun.setEnabled(is_chronic)
        self.lbl_municipio.setStyleSheet("color: #123B4A; font-weight: 600;" if is_chronic else "color: #94A3B8;")

        self.refresh_statistics()

    def refresh_statistics(self) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = StatisticsWorker(
            epi_service=self.epi_service,
            enfermedad=self.current_disease,
            anio=self.current_year,
            municipio=self.current_municipality,
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
        self.error_banner.setVisible(True)
        if status == 401:
            self.error_label.setText("Sesión expirada o no autorizada (HTTP 401).")
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.error_label.setText("No tienes permiso para consultar estadísticas (HTTP 403).")
        else:
            self.error_label.setText(f"Error al cargar estadísticas: {message}")

    def _on_data_loaded(
        self,
        stats: dict[str, Any],
        encuesta: dict[str, Any],
        pred: dict[str, Any],
        municipios: list[dict[str, Any]],
        enfermedades: list[dict[str, Any]],
    ) -> None:
        self.error_banner.setVisible(False)

        # Update municipalities dropdown if needed
        if municipios and self.combo_mun.count() <= 1:
            self.combo_mun.blockSignals(True)
            for m in municipios:
                cve = m.get("clave_inegi", "")
                nom = m.get("nombre", cve)
                self.combo_mun.addItem(nom, cve)
            self.combo_mun.blockSignals(False)

        if enfermedades:
            self.disease_types = {
                str(item.get("clave")): str(item.get("tipo", ""))
                for item in enfermedades
                if item.get("clave")
            }
            current = self.current_disease
            self.combo_disease.blockSignals(True)
            self.combo_disease.clear()
            for item in enfermedades:
                clave = str(item.get("clave", ""))
                nombre = str(item.get("nombre", clave))
                tipo = str(item.get("tipo", ""))
                self.combo_disease.addItem(f"{nombre} ({tipo.capitalize()})", clave)
            index = self.combo_disease.findData(current)
            self.combo_disease.setCurrentIndex(index if index >= 0 else 0)
            self.combo_disease.blockSignals(False)
            self.current_disease = self.combo_disease.currentData() or "dengue"

            is_chronic = self.disease_types.get(self.current_disease) == "cronica"
            self.combo_mun.setEnabled(is_chronic)
            self.lbl_municipio.setStyleSheet(
                "color: #123B4A; font-weight: 600;" if is_chronic else "color: #94A3B8;"
            )

        # 1. Update Metrics Cards
        casos_por_mes = stats.get("casos_por_mes") or []
        clima_por_mes = stats.get("clima_por_mes") or []

        total_casos = sum(c.get("casos", 0) for c in casos_por_mes) if casos_por_mes else None
        self.card_casos.update_value(f"{total_casos:,}" if total_casos is not None else "Sin información disponible")

        temps = [c.get("temperatura") for c in clima_por_mes if c.get("temperatura") is not None]
        avg_temp = (sum(temps) / len(temps)) if temps else None
        self.card_temp.update_value(f"{avg_temp:.1f} °C" if avg_temp is not None else "Sin información disponible")

        hums = [c.get("humedad") for c in clima_por_mes if c.get("humedad") is not None]
        avg_hum = (sum(hums) / len(hums)) if hums else None
        self.card_hum.update_value(f"{avg_hum:.1f} %" if avg_hum is not None else "Sin información disponible")

        precs = [c.get("precipitacion") for c in clima_por_mes if c.get("precipitacion") is not None]
        tot_prec = sum(precs) if precs else None
        self.card_prec.update_value(f"{tot_prec:.1f} mm" if tot_prec is not None else "Sin información disponible")

        # 2. Render Charts
        self._render_charts(casos_por_mes, clima_por_mes)

        # 3. Render Prediction
        prediction_obj = stats.get("prediccion") or pred.get("prediccion")
        self._render_prediction(prediction_obj)

        # 4. Render Surveys
        self._render_surveys(encuesta)

        # 5. Render Chronic Diseases
        cronicas = stats.get("cronicas")
        self._render_chronic_table(cronicas)

    def _render_charts(self, casos_por_mes: list[dict[str, Any]], clima_por_mes: list[dict[str, Any]]) -> None:
        # Clear trend
        while self.trend_canvas_layout.count():
            item = self.trend_canvas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        trend_canvas = EpidemiologicalTrendChart(casos_por_mes, self.current_year)
        self.trend_canvas_layout.addWidget(trend_canvas)

        # Clear climate
        while self.climate_canvas_layout.count():
            item = self.climate_canvas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        climate_canvas = ClimateEvolutionChart(clima_por_mes, self.current_year)
        self.climate_canvas_layout.addWidget(climate_canvas)

    def _render_prediction(self, pred: dict[str, Any] | None) -> None:
        while self.pred_layout.count():
            item = self.pred_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pred or not pred.get("semanas"):
            self.pred_layout.addWidget(
                EmptyStateWidget(
                    icon="📊",
                    title="Sin predicción disponible",
                    description=f"No hay modelo predictivo registrado para el periodo {self.current_year}.",
                )
            )
            return

        semanas = pred.get("semanas", [])
        total = pred.get("total", sum(s for s in semanas if s is not None))
        mes = pred.get("mes", "--")
        anio = pred.get("anio", self.current_year)
        autor = pred.get("creado_por", "Sistema")

        info_lbl = QLabel(f"Proyección estimada para Mes {mes}/{anio} · Autor: {autor}")
        info_lbl.setStyleSheet("font-size: 11px; color: #647C8C; margin-bottom: 4px;")
        self.pred_layout.addWidget(info_lbl)

        grid = QGridLayout()
        grid.setSpacing(8)
        for idx, val in enumerate(semanas[:4], start=1):
            val_txt = f"{val:.2f}" if isinstance(val, (int, float)) else str(val) if val is not None else "--"
            grid.addWidget(WeeklyCard(f"Semana {idx}", val_txt), 0, idx - 1)
        self.pred_layout.addLayout(grid)

        # Total summary
        tot_card = QFrame()
        tot_card.setStyleSheet("background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 6px 12px;")
        tl = QHBoxLayout(tot_card)
        tl.setContentsMargins(8, 4, 8, 4)
        tl_txt = QLabel(f"Total estimado mensual: <b>{total:.2f} casos</b>")
        tl_txt.setStyleSheet("color: #15803D; font-size: 12.5px;")
        tl.addWidget(tl_txt)
        tl.addStretch()
        self.pred_layout.addWidget(tot_card)

    def _render_surveys(self, encuesta: dict[str, Any]) -> None:
        while self.survey_layout.count():
            item = self.survey_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = encuesta.get("total", 0)
        por_mun = encuesta.get("por_municipio", [])

        if not total and not por_mun:
            self.survey_layout.addWidget(
                EmptyStateWidget(
                    icon="📋",
                    title="Sin encuestas registradas",
                    description="No se han recopilado respuestas comunitarias para este periodo.",
                )
            )
            return

        tot_lbl = QLabel(f"Total de respuestas recibidas: <b>{total:,}</b>")
        tot_lbl.setStyleSheet("font-size: 13px; color: #123B4A; margin-bottom: 4px;")
        self.survey_layout.addWidget(tot_lbl)

        # Simple distribution table
        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Clave", "Municipio", "Respuestas"])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setRowCount(len(por_mun))
        tbl.setAlternatingRowColors(True)
        tbl.setMaximumHeight(160)

        for r, item in enumerate(por_mun):
            cve = str(item.get("municipio__clave_inegi", "--"))
            nom = str(item.get("municipio__nombre", "Desconocido"))
            resp = str(item.get("respuestas", 0))

            it_cve = QTableWidgetItem(cve)
            it_cve.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_nom = QTableWidgetItem(nom)
            it_resp = QTableWidgetItem(resp)
            it_resp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            tbl.setItem(r, 0, it_cve)
            tbl.setItem(r, 1, it_nom)
            tbl.setItem(r, 2, it_resp)

        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.survey_layout.addWidget(tbl)

    def _render_chronic_table(self, cronicas: list[dict[str, Any]] | None) -> None:
        if cronicas is None:
            self.card_chronic.setVisible(False)
            return

        self.card_chronic.setVisible(True)
        self.chronic_count.setText(f"{len(cronicas)} registros")
        self.chronic_table.setRowCount(len(cronicas))

        for r, item in enumerate(cronicas):
            indicador = str(item.get("indicador", "--"))
            ambito = str(item.get("ambito", "--"))
            region = str(item.get("region", "Estatal"))
            anio = str(item.get("anio", "--"))
            sexo = str(item.get("sexo", "total"))
            grupo_edad = str(item.get("grupo_edad", "total"))
            institucion = str(item.get("institucion", "total"))
            valor = f"{item.get('valor', 0):,}"
            unidad = str(item.get("unidad", "--"))
            fuente = str(item.get("fuente", "--"))
            cve_mun = str(item.get("municipio__clave_inegi") or "Estatal")

            self.chronic_table.setItem(r, 0, QTableWidgetItem(indicador))
            self.chronic_table.setItem(r, 1, QTableWidgetItem(ambito))
            self.chronic_table.setItem(r, 2, QTableWidgetItem(region))
            self.chronic_table.setItem(r, 3, QTableWidgetItem(anio))
            self.chronic_table.setItem(r, 4, QTableWidgetItem(sexo))
            self.chronic_table.setItem(r, 5, QTableWidgetItem(grupo_edad))
            self.chronic_table.setItem(r, 6, QTableWidgetItem(institucion))

            it_val = QTableWidgetItem(valor)
            it_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.chronic_table.setItem(r, 7, it_val)

            self.chronic_table.setItem(r, 8, QTableWidgetItem(unidad))
            self.chronic_table.setItem(r, 9, QTableWidgetItem(fuente))
            self.chronic_table.setItem(r, 10, QTableWidgetItem(cve_mun))
