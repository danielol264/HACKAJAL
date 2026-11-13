from __future__ import annotations

import requests

from app.core.config import AppConfig, config
from app.core.exceptions import ApiError, ApiNotConfiguredError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient


class AuthService:
    """Firebase email/password login followed by the exact GET /yo/ contract."""
    FIREBASE_LOGIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"

    def __init__(self, api_client: ApiClient | None = None, app_config: AppConfig = config) -> None:
        self._config = app_config
        self._api_client = api_client or ApiClient(app_config)
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        return self._current_user

    @property
    def api_client(self) -> ApiClient:
        return self._api_client

    def login(self, email: str, password: str) -> User:
        if not self._config.firebase_api_key:
            raise ApiNotConfiguredError(None, "FIREBASE_API_KEY no está configurada.")
        login_url = getattr(self._config, "firebase_login_url", self.FIREBASE_LOGIN_URL)
        try:
            response = requests.post(
                f"{login_url}?key={self._config.firebase_api_key}",
                json={"email": email, "password": password, "returnSecureToken": True}, timeout=30,
            )
        except requests.RequestException as error:
            raise ApiRequestError(None, "No se pudo conectar con el servidor") from error
        if not response.ok:
            message = self._firebase_message(response)
            raise ApiError(response.status_code, message)
        token = response.json().get("idToken")
        if not token:
            raise ApiError(response.status_code, "Respuesta de autenticación inválida")
        self._api_client.set_token(token)
        try:
            profile = self._api_client.get("/yo/")
        except ApiError:
            self.logout()
            raise
        try:
            user = User(profile["nombre"], profile["email"], UserRole(profile["rol"]), profile["organizacion"])
        except (KeyError, ValueError, TypeError) as error:
            self.logout()
            raise ApiError(None, "Perfil de usuario inválido") from error
        self._current_user = user
        return user

    def logout(self) -> None:
        self._api_client.set_token(None)
        self._current_user = None

    @staticmethod
    def _firebase_message(response: requests.Response) -> str:
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            message = ""
        messages = {
            "INVALID_LOGIN_CREDENTIALS": "Correo o contraseña incorrectos",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Demasiados intentos, espera un momento",
        }
        return messages.get(message, "No se pudo iniciar sesión")
