from __future__ import annotations

from app.models.user import User
from app.permissions.roles import Module, ROLE_MODULES


class PermissionManager:
    """UI visibility only; Django REST Framework enforces final authorization."""
    def can_access_module(self, user: User, module: Module) -> bool:
        return module in ROLE_MODULES[user.role]
