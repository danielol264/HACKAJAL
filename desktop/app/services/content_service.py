"""Service for articles and notes endpoints (API_ESCRITORIO.md)."""
from __future__ import annotations

from typing import Any

from app.services.api.client import ApiClient


class ContentService:
    """Consumes endpoints 11, 12, 13, 14, 15 of API_ESCRITORIO.md."""

    def __init__(self, api_client: ApiClient | None = None) -> None:
        self.api_client = api_client or ApiClient()

    def get_contenido(
        self,
        tipo: str | None = None,
        enfermedad: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /contenido/?tipo=&enfermedad= (🔒)"""
        params: dict[str, Any] = {}
        if tipo:
            params["tipo"] = tipo
        if enfermedad:
            params["enfermedad"] = enfermedad
        return self.api_client.get("/contenido/", **params)

    def get_detalle(self, contenido_id: int) -> dict[str, Any]:
        """GET /contenido/{id}/ (🔒)"""
        return self.api_client.get(f"/contenido/{contenido_id}/")

    def crear_contenido(
        self,
        tipo: str,
        titulo: str,
        cuerpo: str,
        enfermedad: str | None = None,
        url_fuente: str = "",
        imagen_url: str = "",
        publicado: bool = False,
    ) -> dict[str, Any]:
        """POST /contenido/ (👑 admin only)"""
        data = {
            "tipo": tipo,
            "titulo": titulo,
            "cuerpo": cuerpo,
            "enfermedad": enfermedad,
            "url_fuente": url_fuente,
            "imagen_url": imagen_url,
            "publicado": publicado,
        }
        return self.api_client.post("/contenido/", data)

    def actualizar_contenido(self, contenido_id: int, **campos: Any) -> dict[str, Any]:
        """PATCH /contenido/{id}/ (👑 admin only)"""
        return self.api_client.patch(f"/contenido/{contenido_id}/", campos)

    def eliminar_contenido(self, contenido_id: int) -> None:
        """DELETE /contenido/{id}/ (👑 admin only)"""
        self.api_client.delete(f"/contenido/{contenido_id}/")
