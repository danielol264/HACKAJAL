"""Service for epidemiological surveillance endpoints (API_ESCRITORIO.md)."""
from __future__ import annotations

from typing import Any

from app.services.api.client import ApiClient


class EpidemiologyService:
    """Consumes endpoints 2, 3, 4, 5, 6, 7, 16, 17 of API_ESCRITORIO.md."""

    def __init__(self, api_client: ApiClient | None = None) -> None:
        self.api_client = api_client or ApiClient()

    def get_municipios(self) -> list[dict[str, Any]]:
        """GET /municipios/ (🔓)"""
        return self.api_client.get("/municipios/")

    def get_enfermedades(self) -> list[dict[str, Any]]:
        """GET /enfermedades/ (🔓)"""
        return self.api_client.get("/enfermedades/")

    def get_mapa(self, enfermedad: str = "dengue") -> dict[str, Any]:
        """GET /mapa/?enfermedad= (🔒)"""
        return self.api_client.get("/mapa/", enfermedad=enfermedad)

    def get_estadisticas(
        self,
        enfermedad: str = "dengue",
        anio: int = 2026,
        municipio: str | None = None,
    ) -> dict[str, Any]:
        """GET /estadisticas/?enfermedad=&anio=&municipio= (🔒)"""
        params: dict[str, Any] = {"enfermedad": enfermedad, "anio": anio}
        if municipio:
            params["municipio"] = municipio
        return self.api_client.get("/estadisticas/", **params)

    def get_encuesta(self) -> dict[str, Any]:
        """GET /estadisticas/encuesta/ (🔒)"""
        return self.api_client.get("/estadisticas/encuesta/")

    def get_prediccion(self, enfermedad: str = "dengue") -> dict[str, Any]:
        """GET /predicciones/?enfermedad= (🔒)"""
        return self.api_client.get("/predicciones/", enfermedad=enfermedad)

    def create_prediccion(
        self,
        enfermedad: str,
        anio: int,
        mes: int,
        semanas: list[float],
    ) -> dict[str, Any]:
        """POST /predicciones/ (👑 admin only)"""
        data = {"enfermedad": enfermedad, "anio": anio, "mes": mes, "semanas": semanas}
        return self.api_client.post("/predicciones/", data)

    def cargar_datos(self, filas: list[dict[str, Any]]) -> dict[str, Any]:
        """POST /cargas/ (👑 admin only)"""
        return self.api_client.post("/cargas/", filas)
