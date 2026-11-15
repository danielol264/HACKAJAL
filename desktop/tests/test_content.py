"""Automated unit and integration test suite for ContentPage (Fase 4)."""
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
from app.pages.content import ContentDetailDialog, ContentFormDialog, ContentPage
from app.services.content_service import ContentService


class ContentPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_user = User("Daniel Ramos", "admin@hackajal.salud.gob.mx", UserRole.ADMIN, "SSJ")
        self.consulta_user = User("Dra. Elena Vega", "consulta@hackajal.salud.gob.mx", UserRole.CONSULTA, "SSJ")
        self.mock_service = MagicMock(spec=ContentService)

        self.mock_items = [
            {
                "id": 1,
                "tipo": "prevencion",
                "enfermedad": "dengue",
                "titulo": "Eliminación de criaderos de mosquitos",
                "cuerpo": "Lavar, tapar, voltear y tirar recipientes con agua estancada.",
                "url_fuente": "https://salud.jalisco.gob.mx/dengue",
                "imagen_url": "",
                "publicado": True,
                "autor": "Daniel Ramos",
                "fecha": "2026-11-10T10:00:00Z",
            },
            {
                "id": 2,
                "tipo": "articulo",
                "enfermedad": "dengue",
                "titulo": "Comportamiento del vector en la costa sur",
                "cuerpo": "Estudio epidemiológico de temperatura y humedad en el desarrollo del Aedes aegypti.",
                "url_fuente": "",
                "imagen_url": "",
                "publicado": False,
                "autor": "Dr. Fernando Morales",
                "fecha": "2026-11-12T14:00:00Z",
            },
        ]

    def test_content_table_and_indicators_rendering(self) -> None:
        page = ContentPage(user=self.admin_user, content_service=self.mock_service, auto_refresh=False)
        page._on_content_loaded(self.mock_items, [])

        self.assertEqual(page.table.rowCount(), 2)
        self.assertEqual(page.card_total.value_label.text(), "2")
        self.assertEqual(page.card_publicados.value_label.text(), "1")
        self.assertEqual(page.card_borradores.value_label.text(), "1")

    def test_consulta_user_cannot_see_admin_buttons(self) -> None:
        page = ContentPage(user=self.consulta_user, content_service=self.mock_service, auto_refresh=False)
        page._on_content_loaded(self.mock_items, [])

        # For every row, consulta only has 1 action button: Detalle
        for row in range(page.table.rowCount()):
            cell = page.table.cellWidget(row, 7)
            buttons = cell.findChildren(type(page.btn_refresh))
            self.assertEqual(len(buttons), 1)
            self.assertEqual(buttons[0].text(), "Ver")

    def test_form_validation_rejects_empty_fields_and_over_200_chars(self) -> None:
        dialog = ContentFormDialog()
        dialog.edit_titulo.setText("   ")
        dialog.edit_cuerpo.setPlainText("Cuerpo")
        dialog._on_save()
        # The dialog is intentionally not shown in this unit test; verify the
        # label state rather than the inherited window visibility.
        self.assertFalse(dialog.error_label.isHidden())

        # Over 200 chars
        dialog.edit_titulo.setText("A" * 201)
        dialog._on_save()
        self.assertFalse(dialog.error_label.isHidden())
        self.assertIn("200", dialog.error_label.text())


if __name__ == "__main__":
    unittest.main()
