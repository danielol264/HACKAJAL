from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class EpidemiologyMap(QWidget):
    """Folium map rendered through QWebEngineView when optional web engine is installed."""
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        try:
            import folium
            from PySide6.QtWebEngineWidgets import QWebEngineView
            view = QWebEngineView()
            project_root = Path(__file__).resolve().parents[3]
            geojson_path = project_root / "frontend" / "src" / "assets" / "jalisco-monitored.geojson"
            map_view = folium.Map(location=[20.6, -103.5], zoom_start=7, tiles="OpenStreetMap")
            if geojson_path.exists():
                with geojson_path.open(encoding="utf-8") as source:
                    data = json.load(source)
                    # The existing portal GeoJSON has replacement characters in six labels.
                    # Correct them only in the generated map, preserving the source asset.
                    source_labels = {
                        "Cihuatl�n": "Cihuatlán",
                        "Cuautitl�n de Garc�a Barrag�n": "Cuautitlán de García Barragán",
                        "Mixtl�n": "Mixtlán",
                        "San Sebasti�n del Oeste": "San Sebastián del Oeste",
                        "Tomatl�n": "Tomatlán",
                        "Villa Purificaci�n": "Villa Purificación",
                    }
                    for feature in data["features"]:
                        properties = feature["properties"]
                        properties["NOMGEO"] = source_labels.get(properties.get("NOMGEO"), properties.get("NOMGEO"))
                    costa_sur = {"Casimiro Castillo", "Cihuatlán", "Cuautitlán de García Barragán", "La Huerta", "Tomatlán", "Villa Purificación"}
                    def style(feature: dict) -> dict:
                        name = feature["properties"].get("NOMGEO", "")
                        return {"fillColor": "#1B4E81" if name in costa_sur else "#597D9A", "color": "#FFFFFF", "weight": 1, "fillOpacity": .45}
                    folium.GeoJson(data, name="Municipios monitoreados (INEGI)", style_function=style, tooltip=folium.GeoJsonTooltip(fields=["NOMGEO"], aliases=["Municipio:"])).add_to(map_view)
            folium.LayerControl().add_to(map_view)
            output = project_root / "desktop" / "resources" / "maps" / "epidemiological_map.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            map_view.save(str(output))
            view.setUrl(QUrl.fromLocalFile(str(output)))
            layout.addWidget(view)
        except ImportError:
            fallback = QLabel("Mapa disponible al instalar Folium y PySide6-WebEngine.\nLa capa municipal se cargará desde el GeoJSON de INEGI incluido en el proyecto.")
            fallback.setWordWrap(True)
            fallback.setStyleSheet("background: #EAF3F4; color: #46636C; border-radius: 8px; padding: 24px;")
            layout.addWidget(fallback)
