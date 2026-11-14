"""Runtime configuration; values can be replaced through environment variables or .env file."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """Optionally load key=value pairs from a local .env file without external dependencies."""
    search_dirs = [
        Path.cwd(),
        # PyInstaller runs modules from its internal bundle. For a distributed
        # desktop app, keep the deployer-owned configuration beside the .exe.
        Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd(),
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[3],
    ]
    for directory in dict.fromkeys(search_dirs):
        env_file = directory / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value
                break
            except Exception:
                pass


_load_env_file()


@dataclass(frozen=True)
class AppConfig:
    """Application configuration supporting both REAL and MOCK modes."""
    api_base_url: str
    firebase_api_key: str | None
    api_timeout_seconds: int
    mode: str
    firebase_login_url: str

    def __init__(
        self,
        api_base_url: str | None = None,
        firebase_api_key: str | None = None,
        api_timeout_seconds: int | None = None,
        mode: str | None = None,
        firebase_login_url: str | None = None,
    ) -> None:
        # Determine operational mode: mock vs real
        env_mode = os.getenv("HACKAJAL_MODE", os.getenv("APP_MODE", "")).strip().lower()
        if not env_mode:
            # Also check USE_MOCK boolean
            use_mock_env = os.getenv("USE_MOCK", "").strip().lower()
            if use_mock_env in ("true", "1", "yes"):
                env_mode = "mock"
            elif use_mock_env in ("false", "0", "no"):
                env_mode = "real"
            else:
                # Default to mock for local development unless FIREBASE_API_KEY is explicitly configured
                env_mode = "real" if os.getenv("FIREBASE_API_KEY") else "mock"

        effective_mode = (mode or env_mode).strip().lower()
        if effective_mode not in ("real", "mock"):
            effective_mode = "mock"
        object.__setattr__(self, "mode", effective_mode)

        # Timeout
        timeout = api_timeout_seconds if api_timeout_seconds is not None else int(os.getenv("API_TIMEOUT_SECONDS", "60"))
        object.__setattr__(self, "api_timeout_seconds", timeout)

        # URLs and Keys based on mode
        if effective_mode == "real":
            default_api = os.getenv("API_URL", "http://127.0.0.1:8000/api").rstrip("/")
            url = default_api if api_base_url is None else api_base_url.rstrip("/")
            key = os.getenv("FIREBASE_API_KEY") if firebase_api_key is None else firebase_api_key
            login_url = (
                firebase_login_url
                or os.getenv("FIREBASE_LOGIN_URL", "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword")
            )
        else:  # mock
            default_mock_api = os.getenv("MOCK_API_URL", os.getenv("API_URL", "http://127.0.0.1:8000/api")).rstrip("/")
            url = default_mock_api if api_base_url is None else api_base_url.rstrip("/")
            key = (
                firebase_api_key
                or os.getenv("FIREBASE_API_KEY")
                or "MOCK_FIREBASE_KEY"
            )
            base_host = url.replace("/api", "") if "/api" in url else url
            login_url = (
                firebase_login_url
                or os.getenv("FIREBASE_LOGIN_URL", f"{base_host}/identitytoolkit/v1/accounts:signInWithPassword")
            )

        object.__setattr__(self, "api_base_url", url)
        object.__setattr__(self, "firebase_api_key", key)
        object.__setattr__(self, "firebase_login_url", login_url)

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"


# Default application-wide configuration instance
config = AppConfig()
