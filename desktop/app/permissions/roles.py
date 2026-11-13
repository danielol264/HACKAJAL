from __future__ import annotations

from enum import StrEnum

from app.models.user import UserRole


class Module(StrEnum):
    DASHBOARD = "dashboard"
    SURVEILLANCE = "surveillance"
    CASES = "cases"
    MUNICIPALITIES = "municipalities"
    ALERTS = "alerts"
    REPORTS = "reports"
    HISTORY = "history"
    USERS = "users"
    SETTINGS = "settings"


ROLE_MODULES: dict[UserRole, frozenset[Module]] = {
    UserRole.ADMIN: frozenset(Module),
    UserRole.CONSULTA: frozenset({Module.DASHBOARD, Module.SURVEILLANCE, Module.MUNICIPALITIES, Module.ALERTS, Module.REPORTS}),
}
