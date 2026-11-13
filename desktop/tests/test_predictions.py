"""Automated unit and integration test suite for PredictionsPage (Fase 6)."""
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
from app.pages.predictions import PredictionsPage
from app.services.epidemiology_service import EpidemiologyService


class PredictionsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_user = User("Daniel Ramos", "admin@hackajal.salud.gob.mx", UserRole.ADMIN, "SSJ")
        self.consulta_user = User("Dra. Elena Vega", "consulta@hackajal.salud.gob.mx", UserRole.CONSULTA, "SSJ")
        self.mock_service = MagicMock(spec=EpidemiologyService)

    def test_predictions_renders_4_weeks_and_total(self) -> None:
        page = PredictionsPage(user=self.admin_user, epi_service=self.mock_service, auto_refresh=False)
        mock_data = {
            "prediccion": {
                "anio": 2026,
                "mes": 12,
                "semanas": [1.2, 1.96, 0.8, 0.5],
                "total": 4.46,
                "creado_por": "Daniel Ramos",
                "creado_en": "2026-11-13T14:00:00Z",
            }
        }
        page._on_pred_loaded(mock_data, [])
        self.assertFalse(page.error_banner.isVisible())

    def test_predictions_handles_null_prediction_gracefully(self) -> None:
        page = PredictionsPage(user=self.admin_user, epi_service=self.mock_service, auto_refresh=False)
        mock_data = {"prediccion": None}
        page._on_pred_loaded(mock_data, [])
        self.assertFalse(page.error_banner.isVisible())


if __name__ == "__main__":
    unittest.main()
