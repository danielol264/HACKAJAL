from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import authentication, exceptions

from .models import Usuario

_google_request = google_requests.Request()


class FirebaseAuthentication(authentication.BaseAuthentication):
    """Lee 'Authorization: Bearer <token de Firebase>', lo verifica y devuelve el Usuario de Django."""

    def authenticate(self, request):
        encabezado = request.headers.get("Authorization", "")
        if not encabezado.startswith("Bearer "):
            return None  # sin token: la petición sigue como anónima y el permiso decide

        token = encabezado.removeprefix("Bearer ").strip()
        proyecto = settings.FIREBASE_PROJECT_ID
        try:
            datos = id_token.verify_firebase_token(token, _google_request, audience=proyecto)
        except ValueError:
            raise exceptions.AuthenticationFailed("Token inválido o expirado.")
        if datos.get("iss") != f"https://securetoken.google.com/{proyecto}":
            raise exceptions.AuthenticationFailed("Token de otro proyecto.")

        try:
            usuario = Usuario.objects.select_related("organizacion").get(firebase_uid=datos["sub"])
        except Usuario.DoesNotExist:
            raise exceptions.AuthenticationFailed("Usuario no registrado en el sistema.")
        return (usuario, datos)

    def authenticate_header(self, request):
        return "Bearer"  # hace que DRF responda 401 (no 403) cuando falta el token