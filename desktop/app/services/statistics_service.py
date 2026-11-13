"""Application operations for dashboard statistics, independent of Qt."""
from __future__ import annotations

from typing import Any

from app.repositories.dashboard_repository import DashboardRepository
from app.services.api.client import ApiClient


class StatisticsService:
    """Application operations for dashboard statistics, independent of Qt."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self._repository = repository or DashboardRepository()

    def dashboard_snapshot(self) -> dict[str, object]:
        """Historical technical report cut-off snapshot."""
        return self._repository.load_snapshot()

    def fetch_dashboard_data(
        self,
        api_client: ApiClient,
        enfermedad: str = "dengue",
        anio: int = 2026,
    ) -> dict[str, Any]:
        """Fetch all official endpoints for the dashboard as specified in API_ESCRITORIO.md."""
        # 1. Enfermedades catalog (for filters)
        enfermedades = api_client.get("/enfermedades/")

        # 2. Estadísticas (casos y clima por mes)
        estadisticas = api_client.get("/estadisticas/", enfermedad=enfermedad, anio=anio)

        # 3. Predicciones
        prediccion_data = api_client.get("/predicciones/", enfermedad=enfermedad)
        prediccion = prediccion_data.get("prediccion") if isinstance(prediccion_data, dict) else None

        # 4. Alertas pendientes y recientes
        alertas_pendientes = api_client.get("/alertas/", estado="pendiente", enfermedad=enfermedad)
        alertas_todas = api_client.get("/alertas/", enfermedad=enfermedad)

        # 5. Mapa snapshot
        mapa = api_client.get("/mapa/", enfermedad=enfermedad)

        # 6. Compute summary metrics from real API data
        summary_cards = self.compute_summary_cards(estadisticas, prediccion, alertas_pendientes)

        return {
            "enfermedades": enfermedades,
            "estadisticas": estadisticas,
            "prediccion": prediccion,
            "alertas_pendientes": alertas_pendientes,
            "alertas_recientes": alertas_todas,
            "mapa": mapa,
            "summary_cards": summary_cards,
            "filtros": {
                "enfermedad": enfermedad,
                "anio": anio,
            },
        }

    @staticmethod
    def compute_summary_cards(
        estadisticas: dict[str, Any] | None,
        prediccion: dict[str, Any] | None,
        alertas_pendientes: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Compute the 6 statistical cards according to section 3.B of Sprint 2.
        
        Strict rules:
        - Exclusively use information provided by the API.
        - No invented indicators.
        - If an indicator is not available, show 'Sin información disponible'.
        """
        stats = estadisticas or {}
        casos_por_mes = stats.get("casos_por_mes") or []
        clima_por_mes = stats.get("clima_por_mes") or []

        # 1. Casos registrados (Total sum of registered cases)
        if casos_por_mes:
            total_casos = sum(c.get("casos", 0) for c in casos_por_mes if c.get("casos") is not None)
            casos_val = f"{total_casos:,}"
            casos_note = f"Acumulado en {len(casos_por_mes)} meses con registro"
        else:
            casos_val = "Sin información disponible"
            casos_note = "Sin registros para el periodo seleccionado"

        # 2. Casos estimados (Next month forecast total from prediccion)
        if prediccion and prediccion.get("total") is not None:
            estimados_val = f"{prediccion['total']:.2f}"
            estimados_note = f"Mes {prediccion.get('mes', '--')}/{prediccion.get('anio', '--')} · Región costera"
        else:
            estimados_val = "Sin información disponible"
            estimados_note = "Sin modelo predictivo generado"

        # 3. Temperatura promedio
        temps = [float(c["temperatura"]) for c in clima_por_mes if c.get("temperatura") is not None]
        if temps:
            temp_val = f"{sum(temps) / len(temps):.1f} °C"
            temp_note = f"Promedio en {len(temps)} mediciones"
        else:
            temp_val = "Sin información disponible"
            temp_note = "Sin mediciones térmicas"

        # 4. Humedad promedio
        hums = [float(c["humedad"]) for c in clima_por_mes if c.get("humedad") is not None]
        if hums:
            hum_val = f"{sum(hums) / len(hums):.1f} %"
            hum_note = f"Promedio en {len(hums)} mediciones"
        else:
            hum_val = "Sin información disponible"
            hum_note = "Sin mediciones higrométricas"

        # 5. Precipitación
        precs = [float(c["precipitacion"]) for c in clima_por_mes if c.get("precipitacion") is not None]
        if precs:
            prec_val = f"{sum(precs):.1f} mm"
            prec_note = f"Acumulada en {len(precs)} meses medidos"
        else:
            prec_val = "Sin información disponible"
            prec_note = "Sin registros pluviométricos"

        # 6. Alertas pendientes
        if alertas_pendientes is not None:
            count = len(alertas_pendientes)
            alertas_val = str(count)
            alertas_note = "Requieren revisión institucional" if count > 0 else "Sin alertas pendientes"
            alertas_accent = "#BD4B4B" if count > 0 else "#23658A"
        else:
            alertas_val = "Sin información disponible"
            alertas_note = "No se pudo consultar el estado"
            alertas_accent = "#647C8C"

        return [
            {"label": "Casos registrados", "value": casos_val, "note": casos_note, "accent": "#123B4A"},
            {"label": "Casos estimados", "value": estimados_val, "note": estimados_note, "accent": "#028090"},
            {"label": "Temperatura promedio", "value": temp_val, "note": temp_note, "accent": "#C47A27"},
            {"label": "Humedad promedio", "value": hum_val, "note": hum_note, "accent": "#1B4E81"},
            {"label": "Precipitación", "value": prec_val, "note": prec_note, "accent": "#00897B"},
            {"label": "Alertas pendientes", "value": alertas_val, "note": alertas_note, "accent": alertas_accent},
        ]
