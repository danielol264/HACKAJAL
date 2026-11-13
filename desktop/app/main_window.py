from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.components.widgets import NavButton
from app.models.user import User
from app.navigation import NAVIGATION_ITEMS
from app.pages.base import PlaceholderPage
from app.pages.dashboard import DashboardPage
from app.permissions.permission_manager import PermissionManager
from app.services.auth_service import AuthService
from app.theme import STYLESHEET


class MainWindow(QMainWindow):
    """Authenticated shell. Login and REST access remain outside the UI shell."""
    def __init__(self, user: User, auth_service: AuthService, on_logout: Callable[[], None]) -> None:
        super().__init__()
        self.user = user
        self.auth_service = auth_service
        self.on_logout = on_logout
        self.permission_manager = PermissionManager()
        self.nav_buttons: dict[int, NavButton] = {}
        self.setWindowTitle("HACKAJAL | Vigilancia epidemiológica")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 700)
        self.setStyleSheet(STYLESHEET)
        root = QWidget(); root_layout = QHBoxLayout(root); root_layout.setContentsMargins(0, 0, 0, 0); root_layout.setSpacing(0)
        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            on_navigate_to_alerts=self._navigate_to_alerts,
        )
        self.stack.addWidget(self.dashboard_page)
        for item in NAVIGATION_ITEMS[1:]:
            self.stack.addWidget(PlaceholderPage(item.label, "Módulo preparado para su integración con Django REST Framework."))
        root_layout.addWidget(self._build_sidebar())
        content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(0, 0, 0, 0); content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self._apply_permissions()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(252)
        layout = QVBoxLayout(sidebar); layout.setContentsMargins(16, 22, 16, 18); layout.setSpacing(5)
        identity = QFrame(); identity.setObjectName("identityBlock")
        identity_layout = QVBoxLayout(identity); identity_layout.setContentsMargins(12, 14, 12, 14); identity_layout.setSpacing(8)
        seal = QLabel(); seal.setAlignment(Qt.AlignmentFlag.AlignCenter); seal.setMinimumHeight(110)
        pixmap = QPixmap(str(Path(__file__).resolve().parent.parent / "resources" / "escudo_jalisco.png"))
        if not pixmap.isNull():
            seal.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            seal.setText("Escudo institucional"); seal.setObjectName("institutionalPlaceholder")
        identity_layout.addWidget(seal)
        brand = QLabel("GOBIERNO DE JALISCO"); brand.setObjectName("brand"); brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("VIGILANCIA EPIDEMIOLÓGICA"); subtitle.setObjectName("brandSubtitle"); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_layout.addWidget(brand); identity_layout.addWidget(subtitle)
        layout.addWidget(identity); layout.addSpacing(20)
        group = QButtonGroup(self); group.setExclusive(True)
        for index, item in enumerate(NAVIGATION_ITEMS):
            button = NavButton(item.icon, item.label); group.addButton(button, index); layout.addWidget(button)
            button.clicked.connect(lambda checked=False, page=index: self.stack.setCurrentIndex(page))
            self.nav_buttons[index] = button
            if index == 0: button.setChecked(True)
        layout.addStretch()
        footer = QLabel("Gobierno del Estado de Jalisco\nSecretaría de Salud · Acceso institucional")
        footer.setObjectName("brandSubtitle"); footer.setWordWrap(True); layout.addWidget(footer)
        return sidebar

    def _build_topbar(self) -> QFrame:
        bar = QFrame(); bar.setObjectName("topbar"); bar.setFixedHeight(74)
        layout = QHBoxLayout(bar); layout.setContentsMargins(28, 12, 28, 12)
        platform = QLabel("Sistema estatal de vigilancia epidemiológica · Dengue")
        platform.setStyleSheet("font-size: 15px; font-weight: 600; color: #123B4A;")
        layout.addWidget(platform); layout.addStretch()
        user_label = QLabel(f"{self.user.nombre} · {self.user.organizacion} · {self.user.role.value}")
        user_label.setObjectName("muted"); layout.addWidget(user_label); layout.addSpacing(12)
        logout = QPushButton("Cerrar sesión"); logout.setObjectName("navButton")
        logout.setStyleSheet("QPushButton { color: #123B4A; background: #EAF0F5; padding: 7px 10px; }")
        logout.clicked.connect(self._logout)
        layout.addWidget(logout)
        return bar

    def _apply_permissions(self) -> None:
        for index, item in enumerate(NAVIGATION_ITEMS):
            self.nav_buttons[index].setVisible(self.permission_manager.can_access_module(self.user, item.module))

    def _logout(self) -> None:
        self.auth_service.logout()
        self.close()
        self.on_logout()

    def _navigate_to_alerts(self) -> None:
        """Switch navigation directly to the alerts module."""
        from app.permissions.roles import Module
        for index, item in enumerate(NAVIGATION_ITEMS):
            if item.module == Module.ALERTS:
                btn = self.nav_buttons.get(index)
                if btn:
                    btn.setChecked(True)
                self.stack.setCurrentIndex(index)
                break

    def handle_session_expired(self) -> None:
        self._logout()
