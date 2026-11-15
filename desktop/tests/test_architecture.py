from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import AppConfig
from app.core.exceptions import ApiError, ApiNotConfiguredError
from app.models.user import User, UserRole
from app.navigation import NAVIGATION_ITEMS
from app.permissions.permission_manager import PermissionManager
from app.permissions.roles import Module
from app.services.api.client import ApiClient
from app.services.auth_service import AuthService
from app.services.statistics_service import StatisticsService
from app.login_window import LoginWindow


class ArchitectureTests(unittest.TestCase):
    def test_roles_have_expected_module_access(self) -> None:
        permissions = PermissionManager()
        admin = User("Admin", "admin@ejemplo.mx", UserRole.ADMIN, "Organización")
        consulta = User("Consulta", "consulta@ejemplo.mx", UserRole.CONSULTA, "Organización")
        self.assertTrue(permissions.can_access_module(admin, Module.USERS))
        self.assertTrue(permissions.can_access_module(consulta, Module.REPORTS))
        self.assertFalse(permissions.can_access_module(consulta, Module.CASES))
        self.assertFalse(permissions.can_access_module(consulta, Module.SETTINGS))

    def test_navigation_is_centrally_declared(self) -> None:
        self.assertEqual(len(NAVIGATION_ITEMS), 8)  # 7 módulos + Usuarios (solo admin)
        self.assertEqual(NAVIGATION_ITEMS[0].module, Module.DASHBOARD)

    def test_dashboard_data_is_provided_by_service(self) -> None:
        snapshot = StatisticsService().dashboard_snapshot()
        self.assertEqual(len(snapshot["metrics"]), 5)
        self.assertEqual(len(snapshot["historical_confirmed"]), 7)

    def test_api_does_not_call_unconfigured_servers(self) -> None:
        client = ApiClient(AppConfig(api_base_url="", firebase_api_key=None))
        with self.assertRaises(ApiNotConfiguredError):
            client.get("not-an-endpoint")

    def test_login_error_messages_do_not_expose_sensitive_data(self) -> None:
        self.assertEqual(LoginWindow._message_for(ApiError(401, {"detail": "x"})), "Tu cuenta no tiene acceso; contacta al administrador")
        self.assertEqual(LoginWindow._message_for(ApiError(403, {"detail": "x"})), "No tienes permiso para acceder al sistema")
        self.assertEqual(LoginWindow._message_for(ApiError(400, "Correo o contraseña incorrectos")), "Correo o contraseña incorrectos")


if __name__ == "__main__":
    unittest.main()
