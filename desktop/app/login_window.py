from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.core.exceptions import ApiError, ApiNotConfiguredError, ApiRequestError
from app.models.user import User
from app.services.auth_service import AuthService
from app.theme import instalar_estilos


class LoginWindow(QWidget):
    """Firebase sign-in screen. Passwords exist only for the immediate request."""
    authenticated = Signal(object)

    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.setWindowTitle("HACKAJAL | Iniciar sesión")
        self.setMinimumSize(760, 520)
        self.resize(960, 640)
        self.setObjectName("loginForm")
        instalar_estilos(QApplication.instance())
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        identity = QFrame(); identity.setObjectName("sidebar"); identity.setMinimumWidth(300)
        identity_layout = QVBoxLayout(identity); identity_layout.setContentsMargins(44, 48, 44, 48)
        identity_layout.addStretch()
        escudo = QLabel()
        imagen = QPixmap(str(Path(__file__).resolve().parent.parent / "resources" / "escudo_jalisco.png"))
        if not imagen.isNull():
            escudo.setPixmap(imagen.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        identity_layout.addWidget(escudo); identity_layout.addSpacing(16)
        name = QLabel("Secretaría de Salud Jalisco"); name.setObjectName("brand")
        title = QLabel("Vigilancia epidemiológica\nde la región costera de Jalisco")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: 600;")
        subtitle = QLabel("Sistema para el personal de salud: predicción de dengue, alertas y publicación de avisos.")
        subtitle.setObjectName("brandSubtitle"); subtitle.setWordWrap(True)
        identity_layout.addWidget(name); identity_layout.addSpacing(12); identity_layout.addWidget(title); identity_layout.addSpacing(12); identity_layout.addWidget(subtitle)
        identity_layout.addStretch()
        disclaimer = QLabel("HackaJal 2026")
        disclaimer.setObjectName("brandSubtitle"); disclaimer.setWordWrap(True); identity_layout.addWidget(disclaimer)
        root.addWidget(identity, 4)
        form_area = QWidget(); form_layout = QVBoxLayout(form_area); form_layout.setContentsMargins(56, 48, 56, 48)
        form_layout.addStretch()
        heading = QLabel("Iniciar sesión"); heading.setObjectName("pageTitle")
        description = QLabel("Entra con el correo y la contraseña que te dio el administrador."); description.setObjectName("muted")
        self.email = QLineEdit(); self.email.setPlaceholderText("Correo electrónico"); self.email.setClearButtonEnabled(True)
        self.password = QLineEdit(); self.password.setPlaceholderText("Contraseña"); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel(); self.error.setWordWrap(True); self.error.setStyleSheet("color: #A13B3B; min-height: 24px;")
        self.submit_button = QPushButton("Iniciar sesión"); self.submit_button.setObjectName("actionButton"); self.submit_button.setStyleSheet("QPushButton { padding: 10px; }")
        self.submit_button.clicked.connect(self._submit)
        self.password.returnPressed.connect(self._submit)
        form_layout.addWidget(heading); form_layout.addWidget(description); form_layout.addSpacing(24); form_layout.addWidget(QLabel("Correo")); form_layout.addWidget(self.email); form_layout.addSpacing(12); form_layout.addWidget(QLabel("Contraseña")); form_layout.addWidget(self.password); form_layout.addWidget(self.error); form_layout.addWidget(self.submit_button)
        form_layout.addSpacing(16)
        notice = QLabel("¿No puedes entrar? Pide al administrador que revise tu cuenta.")
        notice.setObjectName("muted"); notice.setWordWrap(True); form_layout.addWidget(notice)
        form_layout.addStretch()
        root.addWidget(form_area, 6)

    def _submit(self) -> None:
        email, password = self.email.text().strip(), self.password.text()
        if not email or not password:
            self._show_error("Ingresa correo y contraseña.")
            return
        self.submit_button.setEnabled(False); self.submit_button.setText("Verificando…"); self.error.clear()
        try:
            user = self.auth_service.login(email, password)
        except (ApiError, ApiRequestError, ApiNotConfiguredError) as error:
            self._show_error(self._message_for(error))
        else:
            self.password.clear()
            self.authenticated.emit(user)
        finally:
            self.submit_button.setEnabled(True); self.submit_button.setText("Iniciar sesión")

    def _show_error(self, message: str) -> None:
        self.password.clear()
        self.error.setText(message)

    @staticmethod
    def _message_for(error: Exception) -> str:
        if isinstance(error, ApiRequestError):
            return "No se pudo conectar con el servidor"
        if isinstance(error, ApiError) and error.status == 401:
            return "Tu cuenta no tiene acceso; contacta al administrador"
        if isinstance(error, ApiError) and error.status == 403:
            return "No tienes permiso para acceder al sistema"
        if isinstance(error, ApiError) and isinstance(error.data, str):
            return error.data
        return "No se pudo iniciar sesión"
