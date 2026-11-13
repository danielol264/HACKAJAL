"""Launch the HACKAJAL PySide6 administrative interface."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import config  # noqa: E402
from app.login_window import LoginWindow  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from desktop.mock_api.server import MockServerHandle  # noqa: E402


class ApplicationController:
    def __init__(self) -> None:
        self.mock_handle: MockServerHandle | None = None
        self._ensure_mock_service()
        self.auth_service = AuthService()
        self.login_window: LoginWindow | None = None
        self.main_window: MainWindow | None = None

    def _ensure_mock_service(self) -> None:
        """If configured in MOCK mode and the mock server is not running, start it."""
        if config.is_mock:
            try:
                r = requests.get(f"{config.api_base_url}/health/", timeout=0.3)
                if r.ok:
                    return
            except Exception:
                pass
            try:
                parsed = urlparse(config.api_base_url)
                port = parsed.port or 8000
                host = parsed.hostname or "127.0.0.1"
                self.mock_handle = MockServerHandle(host, port)
                self.mock_handle.start()
            except Exception:
                pass

    def cleanup(self) -> None:
        if self.mock_handle:
            self.mock_handle.stop()
            self.mock_handle = None

    def show_login(self) -> None:
        self.login_window = LoginWindow(self.auth_service)
        self.login_window.authenticated.connect(self.show_main)
        self.login_window.show()

    def show_main(self, user: User) -> None:
        self.main_window = MainWindow(user, self.auth_service, self.show_login)
        self.auth_service.api_client.on_unauthorized = self.main_window.handle_session_expired
        self.main_window.show()
        if self.login_window:
            self.login_window.close()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HACKAJAL")
    controller = ApplicationController()
    app.aboutToQuit.connect(controller.cleanup)
    controller.show_login()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
