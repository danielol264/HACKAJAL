"""Automated test suite for Sprint 2 - Epidemiological Administrative Dashboard."""
from __future__ import annotations

import math
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

# Ensure QApplication exists for widget testing
app = QApplication.instance() or QApplication(sys.argv)

from app.components.chart import ClimateEvolutionChart, EpidemiologicalTrendChart
from app.components.widgets import EmptyStateWidget
from app.models.user import User, UserRole
from app.pages.dashboard import DashboardPage, DashboardWorker
from app.services.statistics_service import StatisticsService


class DashboardSprint2Tests(unittest.TestCase):
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
        self.stats_service = StatisticsService()

    def test_compute_summary_cards_with_full_data(self) -> None:
        mock_stats = {
            "casos_por_mes": [
                {"enfermedad": "dengue", "mes": 9, "casos": 14},
                {"enfermedad": "dengue", "mes": 10, "casos": 9},
            ],
            "clima_por_mes": [
                {"mes": 9, "temperatura": 29.5, "humedad": 72.0, "precipitacion": 180.4},
                {"mes": 10, "temperatura": 27.5, "humedad": 68.0, "precipitacion": 95.0},
            ],
        }
        mock_pred = {
            "anio": 2026,
            "mes": 12,
            "semanas": [1.2, 1.96, 0.8, 0.5],
            "total": 4.46,
        }
        mock_alertas = [{"id": 3, "estado": "pendiente"}]

        cards = self.stats_service.compute_summary_cards(mock_stats, mock_pred, mock_alertas)
        self.assertEqual(len(cards), 6)

        # 1. Casos registrados (14 + 9 = 23)
        self.assertEqual(cards[0]["label"], "Casos registrados")
        self.assertEqual(cards[0]["value"], "23")

        # 2. Casos estimados (4.46)
        self.assertEqual(cards[1]["label"], "Casos estimados")
        self.assertEqual(cards[1]["value"], "4.46")

        # 3. Temperatura promedio ((29.5 + 27.5)/2 = 28.5 °C)
        self.assertEqual(cards[2]["label"], "Temperatura promedio")
        self.assertEqual(cards[2]["value"], "28.5 °C")

        # 4. Humedad promedio ((72 + 68)/2 = 70.0 %)
        self.assertEqual(cards[3]["label"], "Humedad promedio")
        self.assertEqual(cards[3]["value"], "70.0 %")

        # 5. Precipitación (180.4 + 95.0 = 275.4 mm)
        self.assertEqual(cards[4]["label"], "Precipitación")
        self.assertEqual(cards[4]["value"], "275.4 mm")

        # 6. Alertas pendientes (1)
        self.assertEqual(cards[5]["label"], "Alertas pendientes")
        self.assertEqual(cards[5]["value"], "1")

    def test_compute_summary_cards_shows_sin_informacion_when_data_missing(self) -> None:
        """Requirement: Si un indicador no está disponible, mostrar 'Sin información disponible'."""
        empty_stats = {"casos_por_mes": [], "clima_por_mes": []}
        cards = self.stats_service.compute_summary_cards(empty_stats, None, None)

        self.assertEqual(cards[0]["value"], "Sin información disponible")
        self.assertEqual(cards[1]["value"], "Sin información disponible")
        self.assertEqual(cards[2]["value"], "Sin información disponible")
        self.assertEqual(cards[3]["value"], "Sin información disponible")
        self.assertEqual(cards[4]["value"], "Sin información disponible")
        self.assertEqual(cards[5]["value"], "Sin información disponible")

    def test_trend_chart_does_not_draw_zeros_for_missing_months(self) -> None:
        """Requirement: 'No representar meses sin datos como cero'."""
        # Only months 9 and 10 have data
        casos = [
            {"enfermedad": "dengue", "mes": 9, "casos": 14},
            {"enfermedad": "dengue", "mes": 10, "casos": 9},
        ]
        chart = EpidemiologicalTrendChart(casos, anio=2026)

        # Lines drawn on chart
        lines = chart.figure.axes[0].get_lines()
        self.assertEqual(len(lines), 1)
        y_data = lines[0].get_ydata()

        # Months 1 to 8 and 11 to 12 must be NaN, NOT 0.0
        for m in [0, 1, 2, 3, 4, 5, 6, 7, 10, 11]:
            self.assertTrue(math.isnan(y_data[m]), f"Month index {m} should be NaN, but got {y_data[m]}")

        # Measured months
        self.assertEqual(y_data[8], 14.0)  # Month 9
        self.assertEqual(y_data[9], 9.0)   # Month 10

    def test_trend_chart_empty_state_when_no_cases(self) -> None:
        chart = EpidemiologicalTrendChart([], anio=2024)
        # When no cases, no plot lines are added, text informs empty state
        self.assertEqual(len(chart.figure.axes[0].get_lines()), 0)

    def test_climate_chart_initialization_with_missing_values(self) -> None:
        clima = [
            {"mes": 9, "temperatura": 29.5, "humedad": None, "precipitacion": 180.4},
        ]
        chart = ClimateEvolutionChart(clima, anio=2026)
        self.assertGreaterEqual(len(chart.figure.axes), 1)

    def test_dashboard_renders_with_admin_user(self) -> None:
        dashboard = DashboardPage(user=self.admin_user, auto_refresh=False)
        self.assertEqual(dashboard.user.role, UserRole.ADMIN)
        self.assertIn("Daniel Ramos", dashboard.user.nombre)
        # Verify combos exist
        self.assertIsNotNone(dashboard.combo_disease)
        self.assertIsNotNone(dashboard.combo_year)
        self.assertEqual(dashboard.current_year, 2026)
        self.assertEqual(dashboard.current_disease, "dengue")

    def test_dashboard_renders_with_consulta_user_without_admin_actions(self) -> None:
        dashboard = DashboardPage(user=self.consulta_user, auto_refresh=False)
        self.assertEqual(dashboard.user.role, UserRole.CONSULTA)
        self.assertIn("Dra. Elena Vega", dashboard.user.nombre)

        # Verification: No admin buttons (confirm, discard, edit, delete) exist in the dashboard page
        for btn in dashboard.findChildren(QPushButton):
            text = btn.text().lower()
            self.assertNotIn("confirmar", text)
            self.assertNotIn("descartar", text)
            self.assertNotIn("eliminar", text)
            self.assertNotIn("borrar", text)
            self.assertNotIn("crear", text)

    def test_empty_predictions_render_informative_empty_state(self) -> None:
        dashboard = DashboardPage(user=self.admin_user, auto_refresh=False)
        dashboard._render_predictions(None)

        empty_widgets = dashboard.pred_content_container.findChildren(EmptyStateWidget)
        self.assertGreaterEqual(len(empty_widgets), 1)

    def test_empty_alerts_render_informative_empty_state(self) -> None:
        dashboard = DashboardPage(user=self.admin_user, auto_refresh=False)
        dashboard._render_alerts([])

        empty_widgets = dashboard.alerts_content_container.findChildren(EmptyStateWidget)
        self.assertGreaterEqual(len(empty_widgets), 1)

    def test_navigation_to_alerts_callback(self) -> None:
        navigated = False

        def on_nav() -> None:
            nonlocal navigated
            navigated = True

        dashboard = DashboardPage(user=self.admin_user, on_navigate_to_alerts=on_nav, auto_refresh=False)
        dashboard.btn_go_alerts.click()
        self.assertTrue(navigated)

    def test_dashboard_worker_emits_data_on_success(self) -> None:
        mock_stats_service = MagicMock()
        mock_stats_service.fetch_dashboard_data.return_value = {
            "enfermedades": [{"clave": "dengue", "nombre": "Dengue"}],
            "estadisticas": {"casos_por_mes": [], "clima_por_mes": []},
            "summary_cards": [],
        }

        mock_api = MagicMock()
        worker = DashboardWorker(mock_api, mock_stats_service, "dengue", 2026)

        results = []
        worker.signals.data_loaded.connect(lambda d: results.append(d))
        worker.run()

        self.assertEqual(len(results), 1)
        self.assertIn("enfermedades", results[0])


if __name__ == "__main__":
    unittest.main()
