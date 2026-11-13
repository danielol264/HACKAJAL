"""Módulo de mapa epidemiológico interactivo para HACKAJAL (Fase 2).

Implementado con:
- Folium + GeoJSON oficial de los 14 municipios costeros de Jalisco
- PySide6 + QWebEngineView
- Consumo estricto de GET /mapa/?enfermedad= y GET /municipios/
- Coloreo regional homogéneo según alerta (Verde: sin alerta, Amarillo: pendiente, Rojo: confirmada)
- Panel contextual con predicción, casos anteriores y municipios monitoreados
- Ejecución asíncrona mediante QThreadPool sin bloquear la interfaz
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import folium
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import AlertBadge, Card, EmptyStateWidget, MetricCard, PanelTitle
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User
from app.services.api.client import ApiClient
from app.services.epidemiology_service import EpidemiologyService


GEOJSON_PATH = Path(__file__).resolve().parents[2] / "resources" / "maps" / "jalisco-monitored.geojson"


class MapWorkerSignals(QObject):
    data_loaded = Signal(dict, list)  # map_data, enfermedades
    error_occurred = Signal(str, int)
    finished = Signal()


class MapWorker(QRunnable):
    """Background worker for loading map endpoints."""

    def __init__(self, epi_service: EpidemiologyService, enfermedad: str = "dengue") -> None:
        super().__init__()
        self.epi_service = epi_service
        self.enfermedad = enfermedad
        self.signals = MapWorkerSignals()

    def run(self) -> None:
        try:
            enfermedades = []
            try:
                enfermedades = self.epi_service.get_enfermedades() or []
            except Exception:
                pass
            map_data = self.epi_service.get_mapa(enfermedad=self.enfermedad)
            try:
                self.signals.data_loaded.emit(map_data, enfermedades)
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


class MapPage(QWidget):
    """Interactive epidemiological map page."""

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
        self.is_loading = False
        self.raw_data: dict[str, Any] = {}

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(10)

        # 1. Header & Controls
        root.addWidget(self._build_header())

        # 2. Status Banners
        self._build_banners(root)

        # 3. Main Splitter: Map (Left) and Regional Context Panel (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Map Container
        self.map_container = Card()
        map_layout = QVBoxLayout(self.map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(450)
        map_layout.addWidget(self.web_view)
        splitter.addWidget(self.map_container)

        # Context Panel (Right)
        self.context_card = Card()
        self.context_layout = QVBoxLayout(self.context_card)
        self.context_layout.setContentsMargins(16, 14, 16, 14)
        self.context_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.context_content = QWidget()
        self.context_content_layout = QVBoxLayout(self.context_content)
        self.context_content_layout.setContentsMargins(0, 0, 0, 0)
        self.context_content_layout.setSpacing(10)

        scroll.setWidget(self.context_content)
        self.context_layout.addWidget(scroll)

        self.context_card.setMinimumWidth(320)
        self.context_card.setMaximumWidth(400)
        splitter.addWidget(self.context_card)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        # Initial Empty Context
        self._render_empty_context()

        if auto_refresh:
            self.refresh_map()

    def _build_header(self) -> QWidget:
        header = Card()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Mapa Epidemiológico Regional")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Vigilancia espacial · Región Costera de Jalisco (14 municipios monitoreados)")
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        layout.addStretch()

        # Disease Filter
        layout.addWidget(QLabel("Enfermedad:"))
        self.combo_enfermedad = QComboBox()
        self.combo_enfermedad.addItem("Dengue (Transmisible)", "dengue")
        self.combo_enfermedad.addItem("Diabetes Mellitus Tipo 2 (Crónica)", "dm2")
        self.combo_enfermedad.currentIndexChanged.connect(self._on_enfermedad_changed)
        layout.addWidget(self.combo_enfermedad)

        # Refresh button
        self.btn_refresh = QPushButton("↻ Actualizar mapa")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_map)
        layout.addWidget(self.btn_refresh)

        return header

    def _build_banners(self, parent_layout: QVBoxLayout) -> None:
        # Loading Indicator
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px;")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        self.loading_label = QLabel("⟳ Obteniendo estado epidemiológico y renderizando mapa...")
        self.loading_label.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(self.loading_label)
        parent_layout.addWidget(self.loading_bar)

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
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self.refresh_map)
        e_layout.addWidget(btn_retry)
        parent_layout.addWidget(self.error_banner)

    # -------------------------------------------------------------------------
    # Asynchronous Data Loading
    # -------------------------------------------------------------------------

    def refresh_map(self) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = MapWorker(
            epi_service=self.epi_service,
            enfermedad=self.combo_enfermedad.currentData() or "dengue",
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
            self.error_label.setText("No tienes permiso para consultar el mapa (HTTP 403).")
        else:
            self.error_label.setText(f"Error al cargar mapa: {message}")

    def _on_enfermedad_changed(self) -> None:
        self.current_enfermedad = self.combo_enfermedad.currentData() or "dengue"
        self.refresh_map()

    def _on_data_loaded(self, map_data: dict[str, Any], enfermedades: list[dict[str, Any]]) -> None:
        self.error_banner.setVisible(False)
        self.raw_data = map_data

        # Update disease options if retrieved from backend
        if enfermedades and self.combo_enfermedad.count() <= 2:
            current = self.combo_enfermedad.currentData()
            self.combo_enfermedad.blockSignals(True)
            self.combo_enfermedad.clear()
            for d in enfermedades:
                clave = d.get("clave", "")
                nombre = d.get("nombre", clave)
                tipo = d.get("tipo", "")
                self.combo_enfermedad.addItem(f"{nombre} ({tipo.capitalize()})", clave)
            idx = self.combo_enfermedad.findData(current)
            if idx >= 0:
                self.combo_enfermedad.setCurrentIndex(idx)
            self.combo_enfermedad.blockSignals(False)

        # 1. Render Map with Folium
        self._render_folium_map(map_data)

        # 2. Render Contextual Info Panel
        self._render_context_panel(map_data)

    # -------------------------------------------------------------------------
    # Folium Map Generation
    # -------------------------------------------------------------------------

    def _render_folium_map(self, data: dict[str, Any]) -> None:
        alerta = data.get("alerta")
        enfermedad = data.get("enfermedad", "dengue")

        # Determine regional color strictly according to contract:
        # Verde = sin alerta, Amarillo = alerta pendiente, Rojo = alerta confirmada
        if not alerta:
            regional_color = "#22C55E"
            status_text = "Sin alerta activa"
        else:
            estado = alerta.get("estado", "pendiente")
            if estado == "confirmada":
                regional_color = "#EF4444"
                status_text = "Alerta Confirmada"
            elif estado == "descartada":
                regional_color = "#64748B"
                status_text = "Alerta Descartada"
            else:
                regional_color = "#F59E0B"
                status_text = "Alerta Pendiente de Revisión"

        # Centered around the Jalisco Coast
        m = folium.Map(
            location=[19.85, -104.90],
            zoom_start=8,
            tiles="OpenStreetMap",
            zoom_control=True,
        )

        # Load GeoJSON if available
        if GEOJSON_PATH.is_file():
            try:
                with open(GEOJSON_PATH, encoding="utf-8") as f:
                    geo_data = json.load(f)

                def style_function(feature: dict[str, Any]) -> dict[str, Any]:
                    return {
                        "fillColor": regional_color,
                        "color": "#123B4A",
                        "weight": 1.5,
                        "fillOpacity": 0.45,
                    }

                def highlight_function(feature: dict[str, Any]) -> dict[str, Any]:
                    return {
                        "fillColor": regional_color,
                        "color": "#028090",
                        "weight": 3,
                        "fillOpacity": 0.70,
                    }

                g = folium.GeoJson(
                    geo_data,
                    name="Región Costera de Jalisco",
                    style_function=style_function,
                    highlight_function=highlight_function,
                    tooltip=folium.GeoJsonTooltip(
                        fields=["NOMGEO"],
                        aliases=["Municipio:"],
                        localize=True,
                        sticky=True,
                    ),
                )
                g.add_to(m)
            except Exception as e:
                pass

        # Add Markers for municipalities that HAVE valid coordinates
        municipios = data.get("municipios") or []
        for mun in municipios:
            lat = mun.get("latitud")
            lon = mun.get("longitud")
            nombre = mun.get("nombre", "")
            region = mun.get("region", "")
            if lat is not None and lon is not None:
                try:
                    folium.CircleMarker(
                        location=[float(lat), float(lon)],
                        radius=5,
                        color="#123B4A",
                        fill=True,
                        fill_color="#FFFFFF",
                        fill_opacity=0.9,
                        weight=2,
                        tooltip=f"<b>{nombre}</b><br>{region}<br>Estado regional: {status_text}",
                    ).add_to(m)
                except (ValueError, TypeError):
                    continue

        # Add Legend HTML
        legend_html = f"""
        <div style="
            position: fixed; 
            bottom: 20px; left: 20px; width: 220px; height: auto;
            background-color: white; z-index:9999; font-size:11px;
            border:1px solid #CBD5E1; border-radius: 8px; padding: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15); font-family: 'Segoe UI', Arial, sans-serif;
        ">
            <b style="color: #123B4A;">Semáforo de Riesgo Regional</b><br>
            <div style="margin-top: 6px;">
                <span style="display:inline-block; width:12px; height:12px; background-color:#22C55E; border-radius:3px; margin-right:6px;"></span>Verde: Sin alerta activa<br>
                <span style="display:inline-block; width:12px; height:12px; background-color:#F59E0B; border-radius:3px; margin-right:6px;"></span>Amarillo: Alerta pendiente<br>
                <span style="display:inline-block; width:12px; height:12px; background-color:#EF4444; border-radius:3px; margin-right:6px;"></span>Rojo: Alerta confirmada
            </div>
            <div style="margin-top: 6px; font-size: 10px; color: #647C8C; border-top: 1px solid #E2E8F0; padding-top: 4px;">
                Estado actual: <b>{status_text}</b>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Render to QWebEngineView
        html = m.get_root().render()
        self.web_view.setHtml(html)

    # -------------------------------------------------------------------------
    # Contextual Panel
    # -------------------------------------------------------------------------

    def _render_empty_context(self) -> None:
        while self.context_content_layout.count():
            item = self.context_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        empty = EmptyStateWidget(
            icon="🗺️",
            title="Cargando mapa",
            description="Obteniendo municipios y estado epidemiológico de la región costera...",
        )
        self.context_content_layout.addWidget(empty)

    def _render_context_panel(self, data: dict[str, Any]) -> None:
        while self.context_content_layout.count():
            item = self.context_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerta = data.get("alerta")
        prediccion = data.get("prediccion")
        casos_ant = data.get("casos_anio_anterior")
        enf_clave = data.get("enfermedad", "dengue")

        # 1. Regional Alert Status Card
        alert_box = QFrame()
        alert_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        ab_layout = QVBoxLayout(alert_box)
        ab_layout.setContentsMargins(10, 8, 10, 8)
        ab_layout.setSpacing(6)

        ab_header = QHBoxLayout()
        ab_title = QLabel("Estado Epidemiológico")
        ab_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #123B4A;")
        ab_header.addWidget(ab_title)
        ab_header.addStretch()

        if alerta:
            ab_header.addWidget(AlertBadge(alerta.get("estado", "pendiente")))
        else:
            no_alert = QLabel("SIN ALERTA")
            no_alert.setStyleSheet("background-color: #DCFCE7; color: #15803D; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px;")
            ab_header.addWidget(no_alert)
        ab_layout.addLayout(ab_header)

        ab_desc = QLabel(
            "Toda la región costera (14 municipios) comparte un mismo nivel de vigilancia institucional."
        )
        ab_desc.setWordWrap(True)
        ab_desc.setStyleSheet("font-size: 11px; color: #647C8C;")
        ab_layout.addWidget(ab_desc)
        self.context_content_layout.addWidget(alert_box)

        # 2. Inter-annual comparison
        comp_box = QFrame()
        comp_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        cb_layout = QVBoxLayout(comp_box)
        cb_layout.setContentsMargins(10, 8, 10, 8)
        cb_layout.setSpacing(4)
        cb_lbl = QLabel("Casos mismo periodo año anterior:")
        cb_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #647C8C;")
        ant_text = f"{casos_ant} casos" if casos_ant is not None else "Sin dato para comparar"
        cb_val = QLabel(ant_text)
        cb_val.setStyleSheet("font-size: 15px; font-weight: 700; color: #123B4A;")
        cb_layout.addWidget(cb_lbl)
        cb_layout.addWidget(cb_val)
        self.context_content_layout.addWidget(comp_box)

        # 3. Model Prediction Panel
        if prediccion:
            pred_box = QFrame()
            pred_box.setStyleSheet("background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 10px;")
            pb_layout = QVBoxLayout(pred_box)
            pb_layout.setContentsMargins(10, 8, 10, 8)
            pb_layout.setSpacing(6)

            pb_title = QLabel(f"Predicción: Mes {prediccion.get('mes')}/{prediccion.get('anio')}")
            pb_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #15803D;")
            pb_layout.addWidget(pb_title)

            total_est = prediccion.get("total", "--")
            pb_tot = QLabel(f"Total estimado: <b>{total_est}</b> casos")
            pb_tot.setStyleSheet("font-size: 13px; color: #166534;")
            pb_layout.addWidget(pb_tot)

            semanas = prediccion.get("semanas") or []
            if semanas:
                w_grid = QGridLayout()
                w_grid.setSpacing(6)
                for idx, val in enumerate(semanas[:4], start=1):
                    val_str = f"{val:.2f}" if isinstance(val, (int, float)) else str(val) if val is not None else "--"
                    lbl_w = QLabel(f"Sem {idx}: <b>{val_str}</b>")
                    lbl_w.setStyleSheet("font-size: 11px; color: #14532D;")
                    w_grid.addWidget(lbl_w, 0, idx - 1)
                pb_layout.addLayout(w_grid)

            if prediccion.get("creado_por"):
                creator_lbl = QLabel(f"Generado por: {prediccion.get('creado_por')}")
                creator_lbl.setStyleSheet("font-size: 10.5px; color: #15803D; font-style: italic;")
                pb_layout.addWidget(creator_lbl)

            self.context_content_layout.addWidget(pred_box)
        else:
            no_pred = EmptyStateWidget(
                icon="📊",
                title="Sin predicción registrada",
                description=f"No hay modelo predictivo activo para {enf_clave.upper()}.",
            )
            self.context_content_layout.addWidget(no_pred)

        # 4. Monitored Municipalities List
        mun_box = QFrame()
        mun_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        mb_layout = QVBoxLayout(mun_box)
        mb_layout.setContentsMargins(10, 8, 10, 8)
        mb_layout.setSpacing(6)

        mb_title = QLabel("14 Municipios Monitoreados:")
        mb_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #123B4A;")
        mb_layout.addWidget(mb_title)

        municipios = data.get("municipios") or []
        for mun in municipios:
            m_row = QHBoxLayout()
            m_name = QLabel(f"• {mun.get('nombre')}")
            m_name.setStyleSheet("font-size: 11px; color: #334155;")
            m_reg = QLabel(mun.get("region", ""))
            m_reg.setStyleSheet("font-size: 10px; color: #94A3B8;")
            m_row.addWidget(m_name)
            m_row.addStretch()
            m_row.addWidget(m_reg)
            mb_layout.addLayout(m_row)

        self.context_content_layout.addWidget(mun_box)
        self.context_content_layout.addStretch()
