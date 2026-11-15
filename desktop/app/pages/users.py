"""Administración de usuarios (solo admin): crear cuentas, cambiar rol y quitar acceso.

Consume GET/POST /usuarios/, PATCH/DELETE /usuarios/{id}/ y GET /organizaciones/.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import Card, PanelTitle
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User
from app.services.api.client import ApiClient

ROLES = (("Consulta (solo lectura)", "consulta"), ("Administrador", "admin"))


def mensaje_de_error(error: Exception) -> str:
    """Convierte la respuesta de DRF ({"campo": ["msg"]} o {"detail": "msg"}) en un texto."""
    if isinstance(error, ApiRequestError) or not isinstance(error, ApiError):
        return "No se pudo conectar con el servidor."
    if error.status == 403:
        return "Solo un administrador puede gestionar usuarios."
    datos = error.data
    if isinstance(datos, dict):
        if "detail" in datos:
            return str(datos["detail"])
        campo, msgs = next(iter(datos.items()), ("", ""))
        msg = msgs[0] if isinstance(msgs, list) and msgs else msgs
        return f"{campo}: {msg}" if campo else str(msg)
    return f"Error {error.status}"


class _Senales(QObject):
    listo = Signal(object)
    error = Signal(str)


class _Tarea(QRunnable):
    """Corre una llamada a la API fuera del hilo de la interfaz."""

    def __init__(self, funcion: Callable[[], Any]) -> None:
        super().__init__()
        self.funcion = funcion
        self.senales = _Senales()

    def run(self) -> None:
        try:
            resultado = self.funcion()
        except Exception as error:  # noqa: BLE001 — cualquier falla se muestra en pantalla
            self.senales.error.emit(mensaje_de_error(error))
        else:
            self.senales.listo.emit(resultado)


class UsersPage(QWidget):
    def __init__(self, user: User | None = None, api_client: ApiClient | None = None, auto_refresh: bool = True) -> None:
        super().__init__()
        self.user = user
        self.api = api_client or ApiClient()
        self.usuarios: list[dict[str, Any]] = []
        self._tareas: list[_Tarea] = []  # evita que Python libere las señales antes de tiempo

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 16, 20, 20)
        raiz.setSpacing(14)

        # Encabezado
        encabezado = Card()
        h = QHBoxLayout(encabezado)
        h.setContentsMargins(18, 14, 18, 14)
        titulos = QVBoxLayout()
        t = QLabel("Usuarios del sistema")
        t.setStyleSheet("font-size: 18px; font-weight: 700; color: #123B4A;")
        s = QLabel("Crea cuentas de consulta o administración y gestiona sus permisos")
        s.setStyleSheet("font-size: 11px; color: #647C8C;")
        titulos.addWidget(t)
        titulos.addWidget(s)
        h.addLayout(titulos)
        h.addStretch()
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("refreshButton")
        self.btn_actualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_actualizar.clicked.connect(self.refresh_users)
        h.addWidget(self.btn_actualizar)
        raiz.addWidget(encabezado)

        self.aviso = QLabel()
        self.aviso.setWordWrap(True)
        self.aviso.setVisible(False)
        raiz.addWidget(self.aviso)

        # Formulario de alta
        form_card = Card()
        f = QVBoxLayout(form_card)
        f.setContentsMargins(18, 14, 18, 14)
        f.addWidget(PanelTitle("Nuevo usuario", "La cuenta se crea en Firebase y en el sistema"))
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre completo")
        self.in_email = QLineEdit()
        self.in_email.setPlaceholderText("correo@ejemplo.com")
        self.in_password = QLineEdit()
        self.in_password.setPlaceholderText("Mínimo 6 caracteres")
        self.in_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.in_rol = QComboBox()
        for nombre, clave in ROLES:
            self.in_rol.addItem(nombre, clave)
        self.in_org = QComboBox()
        form.addRow("Nombre:", self.in_nombre)
        form.addRow("Correo:", self.in_email)
        form.addRow("Contraseña:", self.in_password)
        form.addRow("Rol:", self.in_rol)
        form.addRow("Organización:", self.in_org)
        f.addLayout(form)
        fila_btn = QHBoxLayout()
        fila_btn.addStretch()
        self.btn_crear = QPushButton("Crear usuario")
        self.btn_crear.setObjectName("actionButton")
        self.btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crear.clicked.connect(self._crear)
        fila_btn.addWidget(self.btn_crear)
        f.addLayout(fila_btn)
        raiz.addWidget(form_card)

        # Tabla
        tabla_card = Card()
        tl = QVBoxLayout(tabla_card)
        tl.setContentsMargins(18, 14, 18, 14)
        self.titulo_tabla = PanelTitle("Usuarios registrados")
        tl.addWidget(self.titulo_tabla)
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Correo", "Rol", "Organización", "Acciones"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(46)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tabla.setAlternatingRowColors(True)
        cab = self.tabla.horizontalHeader()
        for col in (0, 1, 3):
            cab.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        cab.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(4, 250)
        tl.addWidget(self.tabla)
        raiz.addWidget(tabla_card, 1)

        if auto_refresh:
            self.refresh_users()

    # ---------- llamadas a la API ----------

    def _ejecutar(self, funcion: Callable[[], Any], al_terminar: Callable[[Any], None]) -> None:
        tarea = _Tarea(funcion)
        self._tareas.append(tarea)

        def fin(_=None) -> None:
            self._tareas.remove(tarea)
            self.btn_crear.setEnabled(True)
            self.btn_actualizar.setEnabled(True)

        tarea.senales.listo.connect(al_terminar)
        tarea.senales.listo.connect(fin)
        tarea.senales.error.connect(lambda msg: self._avisar(msg, error=True))
        tarea.senales.error.connect(fin)
        self.btn_crear.setEnabled(False)
        self.btn_actualizar.setEnabled(False)
        QThreadPool.globalInstance().start(tarea)

    def refresh_users(self) -> None:
        self._ejecutar(lambda: (self.api.get("/usuarios/"), self.api.get("/organizaciones/")), self._mostrar)

    def _mostrar(self, datos: tuple[list[dict[str, Any]], list[dict[str, Any]]]) -> None:
        self.usuarios, organizaciones = datos
        actual = self.in_org.currentData()
        self.in_org.clear()
        for org in organizaciones:
            self.in_org.addItem(org["nombre"], org["id"])
        if actual is not None and self.in_org.findData(actual) >= 0:
            self.in_org.setCurrentIndex(self.in_org.findData(actual))
        self._llenar_tabla()

    def _llenar_tabla(self) -> None:
        self.tabla.setRowCount(len(self.usuarios))
        for fila, u in enumerate(self.usuarios):
            self.tabla.setItem(fila, 0, QTableWidgetItem(u["nombre"]))
            self.tabla.setItem(fila, 1, QTableWidgetItem(u["email"]))
            rol = QTableWidgetItem("Administrador" if u["rol"] == "admin" else "Consulta")
            rol.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(fila, 2, rol)
            self.tabla.setItem(fila, 3, QTableWidgetItem(u.get("organizacion_nombre") or ""))

            acciones = QWidget()
            acciones.setStyleSheet(".QWidget { background: transparent; }")
            a = QHBoxLayout(acciones)
            a.setContentsMargins(4, 2, 4, 2)
            a.setSpacing(6)
            a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self.user and u["email"].lower() == self.user.email.lower():
                yo = QLabel("Tu cuenta")
                yo.setStyleSheet("color: #94A3B8; font-style: italic;")
                a.addWidget(yo)
            else:
                otro = "consulta" if u["rol"] == "admin" else "admin"
                btn_rol = QPushButton("Hacer consulta" if otro == "consulta" else "Hacer admin")
                btn_rol.setMinimumWidth(110)
                btn_rol.setStyleSheet("QPushButton { background-color: #028090; color: white; border: none; border-radius: 5px; padding: 4px 8px; font-weight: 600; font-size: 11px; }")
                btn_rol.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_rol.clicked.connect(lambda _, usr=u, r=otro: self._cambiar_rol(usr, r))
                btn_del = QPushButton("Eliminar")
                btn_del.setMinimumWidth(90)
                btn_del.setStyleSheet("QPushButton { background-color: #FEE2E2; border: 1px solid #FCA5A5; color: #DC2626; border-radius: 5px; padding: 4px 8px; font-size: 11px; }")
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.clicked.connect(lambda _, usr=u: self._eliminar(usr))
                a.addWidget(btn_rol)
                a.addWidget(btn_del)
            self.tabla.setCellWidget(fila, 4, acciones)
        self.titulo_tabla.findChildren(QLabel)[0].setText(f"Usuarios registrados ({len(self.usuarios)})")

    # ---------- acciones ----------

    def _crear(self) -> None:
        datos = {
            "nombre": self.in_nombre.text().strip(),
            "email": self.in_email.text().strip(),
            "password": self.in_password.text(),
            "rol": self.in_rol.currentData(),
            "organizacion": self.in_org.currentData(),
        }
        if not datos["nombre"] or not datos["email"]:
            return self._avisar("Escribe el nombre y el correo.", error=True)
        if len(datos["password"]) < 6:
            return self._avisar("La contraseña debe tener al menos 6 caracteres.", error=True)
        if datos["organizacion"] is None:
            return self._avisar("No hay organizaciones. Crea una en el panel de administración de Django.", error=True)

        def creado(u: dict[str, Any]) -> None:
            for campo in (self.in_nombre, self.in_email, self.in_password):
                campo.clear()
            self._avisar(f"Usuario {u['email']} creado. Ya puede iniciar sesión con su correo y contraseña.")
            self.refresh_users()

        self._ejecutar(lambda: self.api.post("/usuarios/", datos), creado)

    def _cambiar_rol(self, u: dict[str, Any], rol: str) -> None:
        def listo(_: Any) -> None:
            self._avisar(f"{u['nombre']} ahora es {'administrador' if rol == 'admin' else 'de consulta'}.")
            self.refresh_users()

        self._ejecutar(lambda: self.api.patch(f"/usuarios/{u['id']}/", {"rol": rol}), listo)

    def _eliminar(self, u: dict[str, Any]) -> None:
        resp = QMessageBox.question(
            self, "Eliminar usuario",
            f"¿Quitar el acceso a {u['nombre']} ({u['email']})?\n\nYa no podrá entrar al sistema.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        def listo(_: Any) -> None:
            self._avisar(f"Se quitó el acceso a {u['email']}.")
            self.refresh_users()

        self._ejecutar(lambda: self.api.delete(f"/usuarios/{u['id']}/"), listo)

    def _avisar(self, texto: str, error: bool = False) -> None:
        color = ("#FEF2F2", "#FECACA", "#991B1B") if error else ("#F0FDF4", "#86EFAC", "#15803D")
        self.aviso.setStyleSheet(f"background-color: {color[0]}; border: 1px solid {color[1]}; color: {color[2]}; border-radius: 8px; padding: 8px 12px; font-weight: 600;")
        self.aviso.setText(texto)
        self.aviso.setVisible(True)
