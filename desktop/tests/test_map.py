"""Automated unit and integration test suite for MapPage (Fase 2)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from app.models.user import User, UserRole
from app.pages.map import GEOJSON_PATH, MapPage
from app.services.epidemiology_service import EpidemiologyService


class MapPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User("Dra. Elena Vega", "consulta@hackajal.salud.gob.mx", UserRole.CONSULTA, "SSJ")
        self.mock_service = MagicMock(spec=EpidemiologyService)

    def test_geojson_file_exists_locally(self) -> None:
        """Requirement: GeoJSON must be present locally in desktop resources."""
        self.assertTrue(GEOJSON_PATH.is_file(), f"GeoJSON missing at: {GEOJSON_PATH}")

    def test_map_page_renders_with_null_alert_and_null_prediction(self) -> None:
        """Requirement: Si la predicción o la alerta son null, la interfaz debe manejarlo sin errores."""
        page = MapPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_data = {
            "enfermedad": "dengue",
            "prediccion": None,
            "casos_anio_anterior": None,
            "alerta": None,
            "municipios": [
                {"clave_inegi": "14022", "nombre": "Cihuatlán", "region": "Costa Sur", "latitud": None, "longitud": None},
                {"clave_inegi": "14067", "nombre": "Puerto Vallarta", "region": "Costa-Sierra Occidental", "latitud": 20.62, "longitud": -105.23},
            ],
        }

        # Render without crashing
        page._on_data_loaded(mock_data, [])
        self.assertEqual(page.raw_data, mock_data)
        self.assertFalse(page.error_banner.isVisible())

    def test_map_page_renders_with_pending_alert(self) -> None:
        page = MapPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_data = {
            "enfermedad": "dengue",
            "prediccion": {
                "anio": 2026,
                "mes": 12,
                "semanas": [1.2, 1.96, 0.8, 0.5],
                "total": 4.46,
                "creado_por": "Daniel",
                "creado_en": "2026-11-13T14:15:00Z",
            },
            "casos_anio_anterior": 2,
            "alerta": {"id": 3, "estado": "pendiente"},
            "municipios": [],
        }

        page._on_data_loaded(mock_data, [])
        self.assertEqual(page.raw_data["alerta"]["estado"], "pendiente")

    def test_map_page_renders_with_confirmed_alert(self) -> None:
        page = MapPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_data = {
            "enfermedad": "dengue",
            "prediccion": None,
            "casos_anio_anterior": 15,
            "alerta": {"id": 1, "estado": "confirmada"},
            "municipios": [],
        }

        page._on_data_loaded(mock_data, [])
        self.assertEqual(page.raw_data["alerta"]["estado"], "confirmada")


if __name__ == "__main__":
    unittest.main()
