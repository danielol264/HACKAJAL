from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    CONSULTA = "consulta"


@dataclass(frozen=True)
class User:
    nombre: str
    email: str
    role: UserRole
    organizacion: str
