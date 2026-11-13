"""Service for epidemiological alerts endpoints (API_ESCRITORIO.md)."""
from __future__ import annotations

from typing import Any

from app.services.api.client import ApiClient


class AlertsService:
    """Consumes endpoints 8, 9, 10 of API_ESCRITORIO.md."""

    def __init__(self, api_client: ApiClient | None = None) -> None:
        self.api_client = api_client or ApiClient()

    def get_alertas(
        self,
        estado: str | None = None,
        enfermedad: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /alertas/?estado=&enfermedad= (🔒)"""
        params: dict[str, Any] = {}
        if estado:
            params["estado"] = estado
        if enfermedad:
            params["enfermedad"] = enfermedad
        return self.api_client.get("/alertas/", **params)

    def confirmar_alerta(self, alerta_id: int, mensaje_publico: str) -> dict[str, Any]:
        """POST /alertas/{id}/confirmar/ (👑 admin only)"""
        return self.api_client.post(f"/alertas/{alerta_id}/confirmar/", {"mensaje_publico": mensaje_publico})

    def descartar_alerta(self, alerta_id: int) -> dict[str, Any]:
        """POST /alertas/{id}/descartar/ (👑 admin only)"""
        return self.api_client.post(f"/alertas/{alerta_id}/descartar/")
