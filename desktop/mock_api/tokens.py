"""Simulated token generator and validator for HACKAJAL Mock API.

Tokens simulate Firebase idTokens with role metadata and expiration.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

MOCK_SECRET = "hackajal-mock-secret-key-2026"


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def generate_mock_token(email: str, rol: str, expires_in_seconds: int = 3600) -> str:
    """Generate a signed mock JWT-like token valid for 1 hour by default."""
    payload = {
        "email": email.strip().lower(),
        "rol": rol,
        "exp": int(time.time()) + expires_in_seconds,
        "iss": "hackajal-mock-firebase",
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64_encode(payload_bytes)
    signature = hmac.new(MOCK_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"mock.{payload_b64}.{signature[:16]}"


def verify_mock_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a mock token. Returns payload dict or None if invalid/expired."""
    if not token or not token.startswith("mock."):
        # Also support simple testing tokens like 'mock-admin-token' or 'mock-consulta-token'
        if token == "mock-admin-token":
            return {"email": "admin@hackajal.salud.gob.mx", "rol": "admin", "iss": "hackajal-mock-firebase"}
        if token == "mock-consulta-token":
            return {"email": "consulta@hackajal.salud.gob.mx", "rol": "consulta", "iss": "hackajal-mock-firebase"}
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    _, payload_b64, signature = parts
    expected_sig = hmac.new(MOCK_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(signature, expected_sig):
        return None

    try:
        payload_json = _b64_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
