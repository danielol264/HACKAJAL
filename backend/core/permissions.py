from rest_framework.permissions import BasePermission

from .models import Usuario


class EsUsuario(BasePermission):
    """Cualquier usuario de una organización con sesión iniciada."""

    def has_permission(self, request, view):
        return isinstance(request.user, Usuario)


class EsAdmin(BasePermission):
    """Solo usuarios con rol admin."""

    def has_permission(self, request, view):
        return isinstance(request.user, Usuario) and request.user.rol == "admin"