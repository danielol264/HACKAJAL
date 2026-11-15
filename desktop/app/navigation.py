from __future__ import annotations

from dataclasses import dataclass

from app.permissions.roles import Module


@dataclass(frozen=True)
class NavigationItem:
    icon: str
    label: str
    module: Module


# Íconos monocromáticos (no emoji) para que se vean igual en cualquier Windows
NAVIGATION_ITEMS = (
    NavigationItem("▦", "Inicio", Module.DASHBOARD),
    NavigationItem("◉", "Mapa", Module.MAP),
    NavigationItem("▥", "Estadísticas", Module.STATISTICS),
    NavigationItem("⚑", "Alertas", Module.ALERTS),
    NavigationItem("≡", "Artículos y avisos", Module.CONTENT),
    NavigationItem("⇪", "Carga de datos", Module.DATA_UPLOAD),
    NavigationItem("↗", "Predicciones", Module.PREDICTIONS),
    NavigationItem("◎", "Usuarios", Module.USERS),  # solo admin (ROLE_MODULES)
)
