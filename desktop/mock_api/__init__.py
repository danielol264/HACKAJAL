"""HACKAJAL Independent Mock API package.

Provides a full local mock of Django REST Framework and Firebase Authentication
according to the API_ESCRITORIO.md specification.
"""
from __future__ import annotations

from desktop.mock_api.data import MockDatabase, db
from desktop.mock_api.server import MockServerHandle, create_mock_server
from desktop.mock_api.tokens import generate_mock_token, verify_mock_token

__all__ = [
    "MockDatabase",
    "MockServerHandle",
    "create_mock_server",
    "db",
    "generate_mock_token",
    "verify_mock_token",
]
