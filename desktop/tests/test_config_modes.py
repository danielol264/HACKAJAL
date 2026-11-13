"""Tests for MOCK vs REAL configuration modes and environment toggles."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import AppConfig
from app.core.exceptions import ApiNotConfiguredError
from app.services.auth_service import AuthService


class ConfigModesTests(unittest.TestCase):
    def test_mock_mode_default_settings(self) -> None:
        cfg = AppConfig(mode="mock")
        self.assertTrue(cfg.is_mock)
        self.assertEqual(cfg.mode, "mock")
        self.assertEqual(cfg.api_base_url, "http://127.0.0.1:8000/api")
        self.assertEqual(cfg.firebase_api_key, "MOCK_FIREBASE_KEY")
        self.assertIn("identitytoolkit", cfg.firebase_login_url)

    def test_real_mode_settings(self) -> None:
        with patch.dict(os.environ, {"FIREBASE_API_KEY": "real-fb-key", "API_URL": "https://api.produccion.mx/api"}):
            cfg = AppConfig(mode="real")
            self.assertFalse(cfg.is_mock)
            self.assertEqual(cfg.mode, "real")
            self.assertEqual(cfg.api_base_url, "https://api.produccion.mx/api")
            self.assertEqual(cfg.firebase_api_key, "real-fb-key")
            self.assertEqual(cfg.firebase_login_url, "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword")

    def test_real_mode_missing_api_key_raises_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(mode="real", firebase_api_key=None)
            auth = AuthService(app_config=cfg)
            with self.assertRaises(ApiNotConfiguredError):
                auth.login("usuario@salud.gob.mx", "secreto")

    def test_toggle_via_hackajal_mode_env_var(self) -> None:
        with patch.dict(os.environ, {"HACKAJAL_MODE": "real", "FIREBASE_API_KEY": "key123"}):
            cfg = AppConfig()
            self.assertEqual(cfg.mode, "real")
            self.assertFalse(cfg.is_mock)

        with patch.dict(os.environ, {"HACKAJAL_MODE": "mock"}):
            cfg = AppConfig()
            self.assertEqual(cfg.mode, "mock")
            self.assertTrue(cfg.is_mock)

    def test_toggle_via_use_mock_env_var(self) -> None:
        with patch.dict(os.environ, {"USE_MOCK": "false", "FIREBASE_API_KEY": "real-key"}):
            cfg = AppConfig()
            self.assertEqual(cfg.mode, "real")

        with patch.dict(os.environ, {"USE_MOCK": "true"}):
            cfg = AppConfig()
            self.assertEqual(cfg.mode, "mock")


if __name__ == "__main__":
    unittest.main()
