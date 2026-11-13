from __future__ import annotations

from dataclasses import dataclass

from app.permissions.roles import Module


@dataclass(frozen=True)
class NavigationItem:
    icon: str
    label: str
    module: Module


NAVIGATION_ITEMS = (
    NavigationItem("▦", "Dashboard", Module.DASHBOARD),
    NavigationItem("◉", "Vigilancia epidemiológica", Module.SURVEILLANCE),
    NavigationItem("＋", "Registro de casos", Module.CASES),
    NavigationItem("⌖", "Municipios", Module.MUNICIPALITIES),
    NavigationItem("⚑", "Alertas epidemiológicas", Module.ALERTS),
    NavigationItem("▥", "Reportes y estadísticas", Module.REPORTS),
    NavigationItem("◷", "Historial", Module.HISTORY),
    NavigationItem("♙", "Usuarios y permisos", Module.USERS),
    NavigationItem("⚙", "Configuración", Module.SETTINGS),
)
