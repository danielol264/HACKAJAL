from __future__ import annotations

from enum import StrEnum

from app.models.user import UserRole


class Module(StrEnum):
    DASHBOARD = "dashboard"
    MAP = "map"
    STATISTICS = "statistics"
    ALERTS = "alerts"
    CONTENT = "content"
    DATA_UPLOAD = "data_upload"
    PREDICTIONS = "predictions"

    # Backward compatibility identifiers
    SURVEILLANCE = "surveillance"
    CASES = "cases"
    MUNICIPALITIES = "municipalities"
    REPORTS = "reports"
    HISTORY = "history"
    USERS = "users"
    SETTINGS = "settings"


ROLE_MODULES: dict[UserRole, frozenset[Module]] = {
    UserRole.ADMIN: frozenset(Module),
    UserRole.CONSULTA: frozenset({
        Module.DASHBOARD,
        Module.MAP,
        Module.SURVEILLANCE,
        Module.STATISTICS,
        Module.REPORTS,
        Module.ALERTS,
        Module.CONTENT,
        Module.PREDICTIONS,
        Module.MUNICIPALITIES,
    }),
}
