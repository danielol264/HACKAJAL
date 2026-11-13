from __future__ import annotations

from collections.abc import Callable
from typing import Any

import requests

from app.core.config import AppConfig, config
from app.core.exceptions import ApiError, ApiNotConfiguredError, ApiRequestError


class ApiClient:
    """Reusable DRF client; callers provide backend-approved paths only."""
    def __init__(self, app_config: AppConfig = config) -> None:
        self.base_url = app_config.api_base_url
        self.timeout = app_config.api_timeout_seconds
        self.session = requests.Session()
        self.on_unauthorized: Callable[[], None] | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def set_token(self, token: str | None) -> None:
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.is_configured:
            raise ApiNotConfiguredError(None, "API_URL no está configurada.")
        try:
            response = self.session.request(method, f"{self.base_url}/{path.lstrip('/')}", timeout=self.timeout, **kwargs)
        except requests.RequestException as error:
            raise ApiRequestError(None, "No se pudo conectar con el servidor") from error
        data = None if response.status_code == 204 else self._json_or_none(response)
        if not response.ok:
            if response.status_code == 401 and self.on_unauthorized:
                self.on_unauthorized()
            raise ApiError(response.status_code, data)
        return data

    @staticmethod
    def _json_or_none(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    def get(self, path: str, **params: Any) -> Any: return self.request("GET", path, params=params)
    def post(self, path: str, data: object | None = None) -> Any: return self.request("POST", path, json=data)
    def patch(self, path: str, data: object) -> Any: return self.request("PATCH", path, json=data)
    def delete(self, path: str) -> Any: return self.request("DELETE", path)
