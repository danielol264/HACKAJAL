"""Automated unit and integration test suite for StatisticsPage (Fase 3)."""
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
from app.pages.statistics import StatisticsPage
from app.services.epidemiology_service import EpidemiologyService


class StatisticsPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User("Dra. Elena Vega", "consulta@hackajal.salud.gob.mx", UserRole.CONSULTA, "SSJ")
        self.mock_service = MagicMock(spec=EpidemiologyService)

    def test_statistics_renders_monthly_cases_and_climate(self) -> None:
        page = StatisticsPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_stats = {
            "filtros": {"enfermedad": "dengue", "anio": 2026, "municipio": None},
            "casos_por_mes": [
                {"mes": 9, "casos": 14},
                {"mes": 10, "casos": 9},
            ],
            "clima_por_mes": [
                {"mes": 9, "temperatura": 29.5, "humedad": 72.0, "precipitacion": 180.4},
                {"mes": 10, "temperatura": 27.5, "humedad": 68.0, "precipitacion": 95.0},
            ],
            "prediccion": {
                "anio": 2026,
                "mes": 12,
                "semanas": [1.2, 1.96, 0.8, 0.5],
                "total": 4.46,
                "creado_por": "Daniel",
            },
            "cronicas": None,
        }
        mock_encuesta = {
            "total": 12,
            "por_municipio": [
                {"municipio__clave_inegi": "14022", "municipio__nombre": "Cihuatlán", "respuestas": 7},
                {"municipio__clave_inegi": "14067", "municipio__nombre": "Puerto Vallarta", "respuestas": 5},
            ],
        }

        page._on_data_loaded(mock_stats, mock_encuesta, {}, [], [])

        # Casos metric: 14 + 9 = 23
        self.assertEqual(page.card_casos.value_label.text(), "23")
        # Temperatura promedio: (29.5 + 27.5)/2 = 28.5 °C
        self.assertEqual(page.card_temp.value_label.text(), "28.5 °C")
        # Humedad promedio: (72 + 68)/2 = 70.0 %
        self.assertEqual(page.card_hum.value_label.text(), "70.0 %")
        # Precipitación acumulada: 180.4 + 95.0 = 275.4 mm
        self.assertEqual(page.card_prec.value_label.text(), "275.4 mm")

    def test_statistics_handles_missing_months_and_null_climate(self) -> None:
        """Requirement: Un mes que no aparece no es cero; null debe mostrar sin información."""
        page = StatisticsPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_stats = {
            "filtros": {"enfermedad": "dengue", "anio": 2026, "municipio": None},
            "casos_por_mes": [],
            "clima_por_mes": [],
            "prediccion": None,
            "cronicas": None,
        }
        page._on_data_loaded(mock_stats, {}, {}, [], [])

        self.assertEqual(page.card_casos.value_label.text(), "Sin información disponible")
        self.assertEqual(page.card_temp.value_label.text(), "Sin información disponible")
        self.assertEqual(page.card_hum.value_label.text(), "Sin información disponible")
        self.assertEqual(page.card_prec.value_label.text(), "Sin información disponible")

    def test_statistics_renders_chronic_diseases_with_municipal_filter(self) -> None:
        page = StatisticsPage(user=self.user, epi_service=self.mock_service, auto_refresh=False)
        mock_stats = {
            "filtros": {"enfermedad": "dm2", "anio": 2026, "municipio": "14022"},
            "casos_por_mes": None,
            "clima_por_mes": None,
            "prediccion": None,
            "cronicas": [
                {
                    "indicador": "incidencia",
                    "ambito": "municipio",
                    "municipio__clave_inegi": "14022",
                    "region": "Costa Sur",
                    "anio": 2025,
                    "sexo": "total",
                    "grupo_edad": "total",
                    "institucion": "total",
                    "valor": 182.4,
                    "unidad": "tasa_100k",
                    "fuente": "SUIVE/DGE",
                }
            ],
        }

        page._on_data_loaded(mock_stats, {}, {}, [], [])
        # The page is not attached to a displayed window in this unit test.
        self.assertFalse(page.card_chronic.isHidden())
        self.assertEqual(page.chronic_table.rowCount(), 1)


if __name__ == "__main__":
    unittest.main()
