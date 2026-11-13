from __future__ import annotations

from dataclasses import dataclass

from app.permissions.roles import Module


@dataclass(frozen=True)
class NavigationItem:
    icon: str
    label: str
    module: Module


# Official 7 modules defined in HACKAJAL specifications (Fase 9)
NAVIGATION_ITEMS = (
    NavigationItem("▦", "Dashboard", Module.DASHBOARD),
    NavigationItem("◉", "Mapa epidemiológico", Module.MAP),
    NavigationItem("▥", "Estadísticas", Module.STATISTICS),
    NavigationItem("⚑", "Alertas epidemiológicas", Module.ALERTS),
    NavigationItem("📄", "Artículos y notas", Module.CONTENT),
    NavigationItem("＋", "Carga de datos", Module.DATA_UPLOAD),
    NavigationItem("📈", "Predicciones", Module.PREDICTIONS),
)
