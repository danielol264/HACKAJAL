from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import NavButton
from app.models.user import User
from app.navigation import NAVIGATION_ITEMS
from app.pages.alerts import AlertsPage
from app.pages.base import PlaceholderPage
from app.pages.content import ContentPage
from app.pages.dashboard import DashboardPage
from app.pages.data_upload import DataUploadPage
from app.pages.map import MapPage
from app.pages.predictions import PredictionsPage
from app.pages.statistics import StatisticsPage
from app.permissions.permission_manager import PermissionManager
from app.permissions.roles import Module
from app.services.auth_service import AuthService
from app.theme import STYLESHEET


class MainWindow(QMainWindow):
    """Authenticated shell with responsive collapsible sidebar and compact header."""

    def __init__(self, user: User, auth_service: AuthService, on_logout: Callable[[], None]) -> None:
        super().__init__()
        self.user = user
        self.auth_service = auth_service
        self.on_logout = on_logout
        self.permission_manager = PermissionManager()
        self.nav_buttons: dict[int, NavButton] = {}
        self.sidebar_expanded: bool = True

        # Optimized responsive window sizes for 1366x768, 1600x900, 1920x1080
        self.setWindowTitle("HACKAJAL | Vigilancia epidemiológica")
        self.resize(1366, 768)
        self.setMinimumSize(1024, 600)
        self.setStyleSheet(STYLESHEET)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main Page Stack
        self.stack = QStackedWidget()

        # 1. Dashboard Page
        self.dashboard_page = DashboardPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            on_navigate_to_alerts=self._navigate_to_alerts,
        )

        # 2. Map Page
        self.map_page = MapPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            auto_refresh=False,
        )

        # 3. Statistics Page
        self.statistics_page = StatisticsPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            auto_refresh=False,
        )

        # 4. Alerts Page
        self.alerts_page = AlertsPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            auto_refresh=False,
        )

        # 5. Content Page
        self.content_page = ContentPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            auto_refresh=False,
        )

        # 6. Data Upload Page
        self.data_upload_page = DataUploadPage(
            user=self.user,
            api_client=self.auth_service.api_client,
        )

        # 7. Predictions Page
        self.predictions_page = PredictionsPage(
            user=self.user,
            api_client=self.auth_service.api_client,
            auto_refresh=False,
        )

        # Populate stack adhering to NAVIGATION_ITEMS order
        for item in NAVIGATION_ITEMS:
            if item.module == Module.DASHBOARD:
                self.stack.addWidget(self.dashboard_page)
            elif item.module in (Module.MAP, Module.SURVEILLANCE):
                self.stack.addWidget(self.map_page)
            elif item.module in (Module.STATISTICS, Module.REPORTS):
                self.stack.addWidget(self.statistics_page)
            elif item.module == Module.ALERTS:
                self.stack.addWidget(self.alerts_page)
            elif item.module == Module.CONTENT:
                self.stack.addWidget(self.content_page)
            elif item.module in (Module.DATA_UPLOAD, Module.CASES):
                self.stack.addWidget(self.data_upload_page)
            elif item.module == Module.PREDICTIONS:
                self.stack.addWidget(self.predictions_page)
            else:
                self.stack.addWidget(PlaceholderPage(item.label, "Módulo preparado para su integración."))

        # Build Sidebar & Topbar
        self.sidebar_widget = self._build_sidebar()
        root_layout.addWidget(self.sidebar_widget)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content, 1)

        self.setCentralWidget(root)
        self._apply_permissions()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        self.sidebar = sidebar

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        # Identity Card
        self.identity = QFrame()
        self.identity.setObjectName("identityBlock")
        identity_layout = QVBoxLayout(self.identity)
        identity_layout.setContentsMargins(8, 10, 8, 10)
        identity_layout.setSpacing(6)

        self.seal = QLabel()
        self.seal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seal.setMinimumHeight(60)
        pixmap = QPixmap(str(Path(__file__).resolve().parent.parent / "resources" / "escudo_jalisco.png"))
        if not pixmap.isNull():
            self.pixmap_full = pixmap.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.pixmap_mini = pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.seal.setPixmap(self.pixmap_full)
        else:
            self.pixmap_full = None
            self.pixmap_mini = None
            self.seal.setText("Escudo")
            self.seal.setObjectName("institutionalPlaceholder")
        identity_layout.addWidget(self.seal)

        self.brand_label = QLabel("GOBIERNO DE JALISCO")
        self.brand_label.setObjectName("brand")
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label = QLabel("VIGILANCIA EPIDEMIOLÓGICA")
        self.subtitle_label.setObjectName("brandSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_layout.addWidget(self.brand_label)
        identity_layout.addWidget(self.subtitle_label)

        layout.addWidget(self.identity)
        layout.addSpacing(10)

        # Nav Buttons Group
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, item in enumerate(NAVIGATION_ITEMS):
            button = NavButton(item.icon, item.label)
            group.addButton(button, index)
            layout.addWidget(button)
            button.clicked.connect(lambda checked=False, page=index: self._on_nav_clicked(page))
            self.nav_buttons[index] = button
            if index == 0:
                button.setChecked(True)

        layout.addStretch()

        # Footer
        self.footer_label = QLabel("Gobierno del Estado de Jalisco\nSecretaría de Salud")
        self.footer_label.setObjectName("brandSubtitle")
        self.footer_label.setWordWrap(True)
        layout.addWidget(self.footer_label)

        return sidebar

    def _build_topbar(self) -> QFrame:
        """Compact header optimizing space (54px height)."""
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(54)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 6, 18, 6)
        layout.setSpacing(12)

        # Toggle Sidebar Button
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setToolTip("Colapsar / expandir barra lateral")
        self.btn_toggle_sidebar.setFixedSize(36, 36)
        self.btn_toggle_sidebar.setStyleSheet("""
            QPushButton {
                background-color: #EAF0F5;
                color: #123B4A;
                border: 1px solid #D9E3EA;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #DDE6ED;
            }
        """)
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self.btn_toggle_sidebar)

        # Platform Title
        platform = QLabel("Sistema estatal de vigilancia epidemiológica · Región Costera")
        platform.setStyleSheet("font-size: 14px; font-weight: 700; color: #123B4A;")
        layout.addWidget(platform)

        layout.addStretch()

        # User Info Pill
        user_label = QLabel(f"{self.user.nombre} · {self.user.organizacion} · {self.user.role.value.upper()}")
        user_label.setObjectName("muted")
        user_label.setStyleSheet("font-size: 11.5px; color: #475569;")
        layout.addWidget(user_label)
        layout.addSpacing(6)

        # Logout Button
        logout = QPushButton("Cerrar sesión")
        logout.setObjectName("navButton")
        logout.setStyleSheet("QPushButton { color: #123B4A; background: #EAF0F5; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 11.5px; } QPushButton:hover { background: #DDE6ED; }")
        logout.setCursor(Qt.CursorShape.PointingHandCursor)
        logout.clicked.connect(self._logout)
        layout.addWidget(logout)

        return bar

    def _toggle_sidebar(self) -> None:
        """Collapse or expand the sidebar smoothly."""
        self.sidebar_expanded = not self.sidebar_expanded

        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(230)
            self.brand_label.setVisible(True)
            self.subtitle_label.setVisible(True)
            self.footer_label.setVisible(True)
            if self.pixmap_full:
                self.seal.setPixmap(self.pixmap_full)
            for btn in self.nav_buttons.values():
                btn.set_collapsed(False)
        else:
            self.sidebar.setFixedWidth(64)
            self.brand_label.setVisible(False)
            self.subtitle_label.setVisible(False)
            self.footer_label.setVisible(False)
            if self.pixmap_mini:
                self.seal.setPixmap(self.pixmap_mini)
            for btn in self.nav_buttons.values():
                btn.set_collapsed(True)

    def _on_nav_clicked(self, page_index: int) -> None:
        self.stack.setCurrentIndex(page_index)
        item = NAVIGATION_ITEMS[page_index]
        if item.module == Module.ALERTS:
            self.alerts_page.refresh_alerts()
        elif item.module in (Module.MAP, Module.SURVEILLANCE):
            self.map_page.refresh_map()
        elif item.module in (Module.STATISTICS, Module.REPORTS):
            self.statistics_page.refresh_statistics()
        elif item.module == Module.CONTENT:
            self.content_page.refresh_content()
        elif item.module == Module.PREDICTIONS:
            self.predictions_page.refresh_prediction()

    def _apply_permissions(self) -> None:
        for index, item in enumerate(NAVIGATION_ITEMS):
            self.nav_buttons[index].setVisible(self.permission_manager.can_access_module(self.user, item.module))

    def _logout(self) -> None:
        self.auth_service.logout()
        self.close()
        self.on_logout()

    def _navigate_to_alerts(self) -> None:
        """Switch navigation directly to the alerts module."""
        for index, item in enumerate(NAVIGATION_ITEMS):
            if item.module == Module.ALERTS:
                btn = self.nav_buttons.get(index)
                if btn:
                    btn.setChecked(True)
                self.stack.setCurrentIndex(index)
                self.alerts_page.refresh_alerts()
                break

    def handle_session_expired(self) -> None:
        self._logout()
