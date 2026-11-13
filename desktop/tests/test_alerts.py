"""Automated test suite for Sprint 3 - UX/UI Optimization and Alerts Management Module."""
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

from PySide6.QtWidgets import QApplication, QPushButton

# Ensure QApplication instance exists for widget unit tests
app = QApplication.instance() or QApplication(sys.argv)

from app.core.exceptions import ApiError, ApiRequestError
from app.main_window import MainWindow
from app.models.user import User, UserRole
from app.pages.alerts import AlertDetailDialog, AlertsPage, ConfirmAlertDialog
from app.permissions.roles import Module
from app.services.alerts_service import AlertsService
from app.services.api.client import ApiClient


class AlertsSprint3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_user = User(
            nombre="Daniel Ramos [SIMULADO]",
            email="admin@hackajal.salud.gob.mx",
            role=UserRole.ADMIN,
            organizacion="Secretaría de Salud Jalisco [SIMULADO]",
        )
        self.consulta_user = User(
            nombre="Dra. Elena Vega [SIMULADO]",
            email="consulta@hackajal.salud.gob.mx",
            role=UserRole.CONSULTA,
            organizacion="Región Sanitaria VIII Costa Sur [SIMULADO]",
        )

        self.mock_alerts_data = [
            {
                "id": 1,
                "enfermedad": "dengue",
                "enfermedad_nombre": "Dengue",
                "anio": 2026,
                "mes": 10,
                "casos_estimados": 45,
                "casos_anio_anterior": 12,
                "motivo": "Incremento de casos estimados superior al 200% respecto al año anterior",
                "estado": "pendiente",
                "creada_en": "2026-10-15T08:00:00Z",
                "revisada_por": None,
                "revisada_en": None,
                "mensaje_publico": None,
            },
            {
                "id": 2,
                "enfermedad": "dengue",
                "enfermedad_nombre": "Dengue",
                "anio": 2026,
                "mes": 9,
                "casos_estimados": 80,
                "casos_anio_anterior": 35,
                "motivo": "Brote epidémico proyectado",
                "estado": "confirmada",
                "creada_en": "2026-09-12T10:00:00Z",
                "revisada_por": "Dr. Fernando Morales [SIMULADO]",
                "revisada_en": "2026-09-12T14:30:00Z",
                "mensaje_publico": "Se declara alerta preventiva por dengue en municipios costeros.",
            },
            {
                "id": 3,
                "enfermedad": "dm2",
                "enfermedad_nombre": "Diabetes Mellitus Tipo 2",
                "anio": 2026,
                "mes": 8,
                "casos_estimados": 20,
                "casos_anio_anterior": 22,
                "motivo": "Variación estacional esperada",
                "estado": "descartada",
                "creada_en": "2026-08-10T12:00:00Z",
                "revisada_por": "Dra. Carmen Soto [SIMULADO]",
                "revisada_en": "2026-08-11T09:00:00Z",
                "mensaje_publico": None,
            },
            {
                "id": 4,
                "enfermedad": "dengue",
                "enfermedad_nombre": "Dengue",
                "anio": 2026,
                "mes": 11,
                "casos_estimados": 95,
                "casos_anio_anterior": 28,
                "motivo": "Condiciones hidrometeorológicas favorables para el vector",
                "estado": "pendiente",
                "creada_en": "2026-11-01T08:00:00Z",
                "revisada_por": None,
                "revisada_en": None,
                "mensaje_publico": None,
            },
        ]

    # -------------------------------------------------------------------------
    # AlertsService Unit Tests
    # -------------------------------------------------------------------------

    def test_alerts_service_get_alertas_with_filters(self) -> None:
        mock_client = MagicMock(spec=ApiClient)
        mock_client.get.return_value = self.mock_alerts_data

        service = AlertsService(mock_client)
        result = service.get_alertas(estado="pendiente", enfermedad="dengue")

        mock_client.get.assert_called_once_with(
            "/alertas/",
            estado="pendiente",
            enfermedad="dengue",
        )
        self.assertEqual(len(result), 4)

    def test_alerts_service_confirmar_alerta(self) -> None:
        mock_client = MagicMock(spec=ApiClient)
        mock_client.post.return_value = {"id": 1, "estado": "confirmada"}

        service = AlertsService(mock_client)
        res = service.confirmar_alerta(1, "Mensaje público de prueba para la población.")

        mock_client.post.assert_called_once_with(
            "/alertas/1/confirmar/",
            {"mensaje_publico": "Mensaje público de prueba para la población."},
        )
        self.assertEqual(res["estado"], "confirmada")

    def test_alerts_service_descartar_alerta(self) -> None:
        mock_client = MagicMock(spec=ApiClient)
        mock_client.post.return_value = {"id": 1, "estado": "descartada"}

        service = AlertsService(mock_client)
        res = service.descartar_alerta(1)

        mock_client.post.assert_called_once_with("/alertas/1/descartar/")
        self.assertEqual(res["estado"], "descartada")

    # -------------------------------------------------------------------------
    # AlertsPage Indicators & Calculations
    # -------------------------------------------------------------------------

    def test_alerts_indicators_calculation(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        page._on_alerts_loaded(self.mock_alerts_data, [])

        # Total: 4, Pendientes: 2, Confirmadas: 1, Descartadas: 1
        self.assertEqual(page.card_total.value_label.text(), "4")
        self.assertEqual(page.card_pendientes.value_label.text(), "2")
        self.assertEqual(page.card_confirmadas.value_label.text(), "1")
        self.assertEqual(page.card_descartadas.value_label.text(), "1")

    # -------------------------------------------------------------------------
    # AlertsPage Table Filtering & Search
    # -------------------------------------------------------------------------

    def test_alerts_search_filter(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        page._on_alerts_loaded(self.mock_alerts_data, [])

        # Initial table has 4 rows
        self.assertEqual(page.table.rowCount(), 4)

        # Search by keyword in motivo
        page._on_search_changed("vector")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 0).text(), "#4")
        self.assertEqual(page.card_total.value_label.text(), "1")
        self.assertEqual(page.card_pendientes.value_label.text(), "1")

        # Search by exact disease
        page._on_search_changed("diabetes")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 0).text(), "#3")
        self.assertEqual(page.card_total.value_label.text(), "1")
        self.assertEqual(page.card_descartadas.value_label.text(), "1")

        # Clear search
        page._on_search_changed("")
        self.assertEqual(page.table.rowCount(), 4)
        self.assertEqual(page.card_total.value_label.text(), "4")

    # -------------------------------------------------------------------------
    # Role Enforcement on AlertsPage
    # -------------------------------------------------------------------------

    def test_admin_role_has_action_buttons(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        page._on_alerts_loaded(self.mock_alerts_data, [])

        # Alert #1 is 'pendiente' -> Admin must see Detalle, Confirmar and Descartar buttons
        cell_widget = page.table.cellWidget(0, 9)
        self.assertIsNotNone(cell_widget)
        buttons = cell_widget.findChildren(QPushButton)
        btn_texts = [b.text() for b in buttons]
        self.assertIn("👁️", btn_texts)
        self.assertIn("✓ Confirmar", btn_texts)
        self.assertIn("✕ Descartar", btn_texts)

        # Alert #2 is 'confirmada' -> Admin only sees Detalle button and "Revisada" label
        cell_widget_rev = page.table.cellWidget(1, 9)
        self.assertIsNotNone(cell_widget_rev)
        buttons_rev = cell_widget_rev.findChildren(QPushButton)
        btn_texts_rev = [b.text() for b in buttons_rev]
        self.assertIn("👁️", btn_texts_rev)
        self.assertNotIn("✓ Confirmar", btn_texts_rev)
        self.assertNotIn("✕ Descartar", btn_texts_rev)

    def test_consulta_role_is_strictly_read_only(self) -> None:
        page = AlertsPage(user=self.consulta_user, auto_refresh=False)
        page._on_alerts_loaded(self.mock_alerts_data, [])

        # For every row, consulta user only sees the Detalle button
        for row in range(page.table.rowCount()):
            cell_widget = page.table.cellWidget(row, 9)
            self.assertIsNotNone(cell_widget)
            buttons = cell_widget.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            self.assertEqual(btn_texts, ["👁️"])
            self.assertNotIn("✓ Confirmar", btn_texts)
            self.assertNotIn("✕ Descartar", btn_texts)

    # -------------------------------------------------------------------------
    # ConfirmAlertDialog Validations
    # -------------------------------------------------------------------------

    def test_confirm_dialog_requires_message_and_checkbox(self) -> None:
        alert = self.mock_alerts_data[0]
        dialog = ConfirmAlertDialog(alert)

        # Initially, submit button should be disabled because checkbox is not checked
        self.assertFalse(dialog.chk_confirm.isChecked())
        self.assertFalse(dialog.btn_submit.isEnabled())

        # Checking the checkbox with valid default text enables submit
        dialog.chk_confirm.setChecked(True)
        self.assertTrue(dialog.btn_submit.isEnabled())

        # Emptying text disables submit and shows error
        dialog.text_edit.setPlainText("   ")
        self.assertFalse(dialog.btn_submit.isEnabled())
        self.assertFalse(dialog.error_label.isHidden())

        # Message exceeding 2,000 characters is rejected
        huge_message = "A" * 2001
        dialog.text_edit.setPlainText(huge_message)
        self.assertFalse(dialog.btn_submit.isEnabled())
        self.assertIn("2,000", dialog.error_label.text())

        # Valid text and checked checkbox enables submission
        dialog.text_edit.setPlainText("Alerta epidemiológica oficial emitida.")
        dialog.chk_confirm.setChecked(True)
        self.assertTrue(dialog.btn_submit.isEnabled())
        self.assertTrue(dialog.error_label.isHidden())

    # -------------------------------------------------------------------------
    # AlertDetailDialog Inspection
    # -------------------------------------------------------------------------

    def test_alert_detail_dialog_shows_data(self) -> None:
        # Check modal for confirmed alert #2 with public message
        alert = self.mock_alerts_data[1]
        dialog = AlertDetailDialog(alert)
        self.assertIn("Alerta #2", dialog.windowTitle())

    # -------------------------------------------------------------------------
    # Error Handling in AlertsPage
    # -------------------------------------------------------------------------

    def test_alerts_page_handles_400_bad_request(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        page._on_error_occurred("El mensaje es requerido", 400)
        self.assertFalse(page.error_banner.isHidden())
        self.assertIn("HTTP 400", page.error_label.text())

    def test_alerts_page_handles_401_unauthorized(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        unauth_called = []
        page.alerts_service.api_client.on_unauthorized = lambda: unauth_called.append(True)

        page._on_error_occurred("Token expired", 401)
        self.assertFalse(page.error_banner.isHidden())
        self.assertIn("HTTP 401", page.error_label.text())
        self.assertTrue(unauth_called)

    def test_alerts_page_handles_403_forbidden(self) -> None:
        page = AlertsPage(user=self.consulta_user, auto_refresh=False)
        page._on_error_occurred("Permission denied", 403)
        self.assertFalse(page.error_banner.isHidden())
        self.assertIn("HTTP 403", page.error_label.text())

    def test_alerts_page_handles_404_not_found(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        page._on_error_occurred("Alerta no existe", 404)
        self.assertFalse(page.error_banner.isHidden())
        self.assertIn("HTTP 404", page.error_label.text())

    def test_alerts_page_handles_409_conflict_with_auto_refresh(self) -> None:
        page = AlertsPage(user=self.admin_user, auto_refresh=False)
        refresh_mock = MagicMock()
        page.refresh_alerts = refresh_mock

        page._on_error_occurred("Alerta ya revisada", 409)
        self.assertFalse(page.error_banner.isHidden())
        self.assertIn("409", page.error_label.text())
        refresh_mock.assert_called_once()

    # -------------------------------------------------------------------------
    # UX/UI Optimization: Collapsible Sidebar & Window Adaptation
    # -------------------------------------------------------------------------

    def test_collapsible_sidebar_toggle(self) -> None:
        mock_auth = MagicMock()
        mock_auth.api_client = MagicMock()
        window = MainWindow(self.admin_user, mock_auth, on_logout=lambda: None)

        # Initially expanded
        self.assertTrue(window.sidebar_expanded)
        self.assertEqual(window.sidebar.width(), 230)
        self.assertFalse(window.brand_label.isHidden())

        # Toggle to collapsed
        window._toggle_sidebar()
        self.assertFalse(window.sidebar_expanded)
        self.assertEqual(window.sidebar.width(), 64)
        self.assertTrue(window.brand_label.isHidden())
        self.assertTrue(window.subtitle_label.isHidden())

        # Toggle back to expanded
        window._toggle_sidebar()
        self.assertTrue(window.sidebar_expanded)
        self.assertEqual(window.sidebar.width(), 230)
        self.assertFalse(window.brand_label.isHidden())

        window.close()

    def test_window_adaptation_at_various_resolutions(self) -> None:
        """Requirement: Probar en resoluciones 1366x768, 1600x900 y 1920x1080 sin desbordamientos."""
        mock_auth = MagicMock()
        mock_auth.api_client = MagicMock()
        window = MainWindow(self.admin_user, mock_auth, on_logout=lambda: None)

        resolutions = [(1366, 768), (1600, 900), (1920, 1080)]
        for width, height in resolutions:
            window.resize(width, height)
            app.processEvents()
            # Verify window accepted the geometry resize cleanly without errors
            self.assertGreaterEqual(window.width(), 1024)
            self.assertGreaterEqual(window.height(), 600)

        window.close()


if __name__ == "__main__":
    unittest.main()
