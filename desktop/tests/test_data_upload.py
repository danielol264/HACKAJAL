"""Automated unit and integration test suite for DataUploadPage and file parser (Fase 5)."""
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
from app.pages.data_upload import DataUploadPage
from app.services.epidemiology_service import EpidemiologyService
from app.utils.file_parser import parse_csv


class DataUploadPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_user = User("Daniel Ramos", "admin@hackajal.salud.gob.mx", UserRole.ADMIN, "SSJ")
        self.consulta_user = User("Dra. Elena Vega", "consulta@hackajal.salud.gob.mx", UserRole.CONSULTA, "SSJ")
        self.mock_service = MagicMock(spec=EpidemiologyService)

    def test_file_parser_csv_converts_empty_cells_to_none(self) -> None:
        """Requirement: Celdas vacías deben convertirse a None (evitando NaN)."""
        csv_content = "anio,mes,casos_dengue,temperatura_c,humedad_pct,precipitacion_mm\n2026,9,14,29.5,72,180.4\n2026,10,9,,,\n"
        temp_csv = ROOT / "tests" / "test_temp_upload.csv"
        try:
            temp_csv.write_text(csv_content, encoding="utf-8")
            records = parse_csv(temp_csv)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["anio"], 2026)
            self.assertEqual(records[0]["mes"], 9)
            self.assertEqual(records[0]["casos_dengue"], 14)
            # Empty cells are None
            self.assertIsNone(records[1]["temperatura_c"])
            self.assertIsNone(records[1]["humedad_pct"])
            self.assertIsNone(records[1]["precipitacion_mm"])
        finally:
            if temp_csv.is_file():
                temp_csv.unlink()

    def test_validation_detects_invalid_month_and_duplicate_periods(self) -> None:
        page = DataUploadPage(user=self.admin_user, epi_service=self.mock_service)
        invalid_records = [
            {"anio": 2026, "mes": 13, "casos_dengue": 10},  # Invalid month
            {"anio": 2026, "mes": 13, "casos_dengue": 5},   # Duplicate
        ]
        page._validate_and_render_preview(invalid_records)
        self.assertFalse(page.btn_submit.isEnabled())
        self.assertGreaterEqual(len(page.validation_errors), 2)

    def test_consulta_user_cannot_select_files_or_upload(self) -> None:
        page = DataUploadPage(user=self.consulta_user, epi_service=self.mock_service)
        self.assertFalse(page.btn_select_file.isEnabled())
        self.assertFalse(page.btn_submit.isEnabled())


if __name__ == "__main__":
    unittest.main()
