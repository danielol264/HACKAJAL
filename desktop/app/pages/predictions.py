"""Módulo de consulta y administración de predicciones epidemiológicas (Fase 6).

Endpoints oficiales:
GET /predicciones/?enfermedad= (🔒)
POST /predicciones/ (👑 solo ADMIN)

Implementa:
- Consulta y visualización de proyecciones matemáticas semanales (Semanas 1 a 4)
- Identificación clara: Casos estimados / Modelo predictivo (no confirmados)
- Estados vacíos informativos cuando no existe predicción
- Panel administrativo para ejecución y registro de nuevas proyecciones
- Validación estricta: exactamente 4 valores semanales numéricos >= 0
- Detección de alerta generada ("Se generó una alerta pendiente de revisión")
- Manejo asíncrono con QThreadPool
- Documentación transparente sobre la disponibilidad del modelo local de Machine Learning
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import Card, EmptyStateWidget, MetricCard, PanelTitle, SplitterReflow, WeeklyCard
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient
from app.services import model_runner
from app.services.epidemiology_service import EpidemiologyService


class PredictionsWorkerSignals(QObject):
    pred_loaded = Signal(dict, list)  # pred_data, enfermedades
    pred_created = Signal(dict)
    error_occurred = Signal(str, int)
    finished = Signal()


class PredictionsWorker(QRunnable):
    """Background worker for prediction queries and registration."""

    def __init__(
        self,
        epi_service: EpidemiologyService,
        action: str = "fetch",
        enfermedad: str = "dengue",
        create_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.epi_service = epi_service
        self.action = action
        self.enfermedad = enfermedad
        self.create_payload = create_payload or {}
        self.signals = PredictionsWorkerSignals()

    def run(self) -> None:
        try:
            if self.action == "fetch":
                enfermedades = []
                try:
                    enfermedades = self.epi_service.get_enfermedades() or []
                except Exception:
                    pass
                pred = self.epi_service.get_prediccion(enfermedad=self.enfermedad)
                try:
                    self.signals.pred_loaded.emit(pred, enfermedades)
                except RuntimeError:
                    pass

            elif self.action == "create":
                res = self.epi_service.create_prediccion(
                    enfermedad=self.create_payload["enfermedad"],
                    anio=self.create_payload["anio"],
                    mes=self.create_payload["mes"],
                    semanas=self.create_payload["semanas"],
                )
                try:
                    self.signals.pred_created.emit(res)
                except RuntimeError:
                    pass

        except ApiError as err:
            status = err.status or 0
            detail = ""
            if isinstance(err.data, dict):
                detail = err.data.get("detail") or str(err.data)
            else:
                detail = f"Error {status}"
            try:
                self.signals.error_occurred.emit(detail, status)
            except RuntimeError:
                pass
        except ApiRequestError:
            try:
                self.signals.error_occurred.emit("No se pudo conectar con el servidor.", 0)
            except RuntimeError:
                pass
        except Exception as ex:
            try:
                self.signals.error_occurred.emit(f"Error inesperado: {ex}", 0)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass


class ModelSignals(QObject):
    done = Signal(dict)
    failed = Signal(str)


class ModelWorker(QRunnable):
    def __init__(self, ruta_datos: Path) -> None:
        super().__init__()
        self.ruta_datos = ruta_datos
        self.signals = ModelSignals()

    def run(self) -> None:
        try:
            resultado = model_runner.predecir(self.ruta_datos)
        except Exception as error:  # noqa: BLE001 — se muestra en pantalla
            self.signals.failed.emit(str(error))
        else:
            self.signals.done.emit(resultado)


class PredictionsPage(QWidget):
    """Epidemiological predictions and model execution page."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        epi_service: EpidemiologyService | None = None,
        auto_refresh: bool = True,
    ) -> None:
        super().__init__()
        self.user = user
        self.api_client = api_client or ApiClient()
        self.epi_service = epi_service or EpidemiologyService(self.api_client)

        self.current_enfermedad = "dengue"
        self.predictable_diseases: set[str] = {"dengue"}
        self.is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # 1. Header Card
        root.addWidget(self._build_header_card())

        # 2. Status Banners
        self._build_banners(root)

        # 3. Main Splitter: Prediction Display (Left) + Execution / Technical Panel (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: Prediction Details
        self.display_card = Card()
        self.disp_layout = QVBoxLayout(self.display_card)
        self.disp_layout.setContentsMargins(16, 14, 16, 14)
        self.disp_layout.setSpacing(12)

        self.disp_content = QWidget()
        self.disp_content_layout = QVBoxLayout(self.disp_content)
        self.disp_content_layout.setContentsMargins(0, 0, 0, 0)
        self.disp_content_layout.setSpacing(10)
        self.disp_layout.addWidget(self.disp_content)

        splitter.addWidget(self.display_card)

        # Right: Administrative Generation Panel
        self.admin_card = Card()
        self.admin_layout = QVBoxLayout(self.admin_card)
        self.admin_layout.setContentsMargins(16, 14, 16, 14)
        self.admin_layout.setSpacing(10)
        self._build_admin_panel()
        splitter.addWidget(self.admin_card)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)
        SplitterReflow(self, splitter, 1000)  # en ventanas angostas, el panel del modelo baja

        self._render_empty()

        if auto_refresh:
            self.refresh_prediction()

    def _build_header_card(self) -> QWidget:
        card = Card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Predicciones")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Casos estimados de dengue para las próximas 4 semanas en la Costa")
        sub.setWordWrap(True)
        sub.setMinimumWidth(300)
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        layout.addStretch()

        layout.addWidget(QLabel("Enfermedad:"))
        self.combo_disease = QComboBox()
        self.combo_disease.addItem("Dengue (Transmisible)", "dengue")
        self.combo_disease.currentIndexChanged.connect(self._on_disease_changed)
        layout.addWidget(self.combo_disease)

        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_prediction)
        layout.addWidget(self.btn_refresh)

        return card

    def _build_banners(self, parent_layout: QVBoxLayout) -> None:
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet(".QFrame { background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 6px; }")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("Cargando predicción…")
        lbl.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(lbl)
        parent_layout.addWidget(self.loading_bar)

        self.error_banner = QFrame()
        self.error_banner.setVisible(False)
        self.error_banner.setStyleSheet(".QFrame { background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 6px; }")
        e_layout = QHBoxLayout(self.error_banner)
        e_layout.setContentsMargins(12, 6, 12, 6)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #991B1B; font-weight: 600; font-size: 12px;")
        e_layout.addWidget(self.error_label)
        parent_layout.addWidget(self.error_banner)

        self.success_banner = QFrame()
        self.success_banner.setVisible(False)
        self.success_banner.setStyleSheet(".QFrame { background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 8px; }")
        s_layout = QHBoxLayout(self.success_banner)
        s_layout.setContentsMargins(12, 6, 12, 6)
        self.success_label = QLabel()
        self.success_label.setStyleSheet("color: #15803D; font-weight: 700; font-size: 12px;")
        s_layout.addWidget(self.success_label)
        parent_layout.addWidget(self.success_banner)

    def _build_admin_panel(self) -> None:
        is_admin = self.user and self.user.role == UserRole.ADMIN

        p_title = QLabel("Ejecutar modelo predictivo")
        p_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #123B4A;")
        self.admin_layout.addWidget(p_title)

        notice = QFrame()
        notice.setStyleSheet(".QFrame { background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 6px; padding: 8px; }")
        nl = QVBoxLayout(notice)
        nl.setContentsMargins(8, 6, 8, 6)
        n_body = QLabel(
            "El modelo predice las próximas 4 semanas para los 14 municipios "
            "de la Costa a partir de los datos <b>semanales por municipio</b>. El resultado se envía a la API y, si supera "
            "al mismo mes del año anterior, se genera una alerta pendiente de revisión."
        )
        n_body.setWordWrap(True)
        n_body.setStyleSheet("color: #075985; font-size: 11px;")
        nl.addWidget(n_body)
        self.admin_layout.addWidget(notice)

        if not is_admin:
            cons_lbl = QLabel("Solo los administradores pueden ejecutar el modelo.")
            cons_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-style: italic; margin-top: 8px;")
            self.admin_layout.addWidget(cons_lbl)
            self.admin_layout.addStretch()
            return

        datos_lbl = QLabel("Datos semanales del modelo:")
        datos_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #123B4A; margin-top: 6px;")
        self.admin_layout.addWidget(datos_lbl)
        self.ruta_elegida: Path | None = None  # None = el último archivo cargado en "Carga de datos"
        self.lbl_archivo = QLabel()
        self.lbl_archivo.setWordWrap(True)
        self.lbl_archivo.setStyleSheet("font-size: 11px; color: #334155; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 5px; padding: 6px;")
        self.admin_layout.addWidget(self.lbl_archivo)
        self._mostrar_archivo()
        btn_archivo = QPushButton("Cambiar archivo…")
        btn_archivo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_archivo.clicked.connect(self._elegir_archivo)
        self.admin_layout.addWidget(btn_archivo)

        self.btn_submit_pred = QPushButton("▶ Ejecutar modelo y generar predicción")
        self.btn_submit_pred.setObjectName("actionButton")
        self.btn_submit_pred.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit_pred.setStyleSheet(
            "QPushButton { background-color: #123B4A; color: white; border-radius: 6px; padding: 10px 16px; font-weight: 700; margin-top: 10px; }"
            " QPushButton:disabled { background-color: #94A3B8; color: #E2E8F0; }"
        )
        self.btn_submit_pred.clicked.connect(self._submit_prediction)
        self.admin_layout.addWidget(self.btn_submit_pred)

        self.lbl_modelo = QLabel()
        self.lbl_modelo.setWordWrap(True)
        self.lbl_modelo.setStyleSheet("font-size: 11px; color: #647C8C;")
        self.admin_layout.addWidget(self.lbl_modelo)

        self.admin_layout.addStretch()

    @property
    def ruta_datos(self) -> Path:
        return self.ruta_elegida or model_runner.datos_del_modelo()

    def _mostrar_archivo(self) -> None:
        if self.ruta_elegida:
            origen = "elegido a mano"
        elif self.ruta_datos == model_runner.DATOS_CARGADOS:
            origen = "último cargado en Carga de datos"
        else:
            origen = "datos originales del modelo"
        self.lbl_archivo.setText(f"{self.ruta_datos.name}  ({origen})")

    def _elegir_archivo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Datos semanales por municipio", str(self.ruta_datos.parent), "Archivos CSV (*.csv)"
        )
        if ruta:
            self.ruta_elegida = Path(ruta)
            self._mostrar_archivo()

    # -------------------------------------------------------------------------
    # Actions & Rendering
    # -------------------------------------------------------------------------

    def _on_disease_changed(self) -> None:
        self.current_enfermedad = self.combo_disease.currentData() or "dengue"
        self.refresh_prediction()

    def refresh_prediction(self) -> None:
        if hasattr(self, "lbl_archivo"):
            self._mostrar_archivo()  # pudo cambiar al cargar un archivo nuevo
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.error_banner.setVisible(False)

        worker = PredictionsWorker(
            epi_service=self.epi_service,
            action="fetch",
            enfermedad=self.current_enfermedad,
        )
        worker.signals.pred_loaded.connect(self._on_pred_loaded)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_worker_finished(self) -> None:
        self.is_loading = False
        self.btn_refresh.setEnabled(True)
        if hasattr(self, "btn_submit_pred"):
            self.btn_submit_pred.setEnabled(True)
        self.loading_bar.setVisible(False)

    def _on_error_occurred(self, message: str, status: int) -> None:
        self.error_banner.setVisible(True)
        if status == 401:
            self.error_label.setText("Tu sesión expiró. Vuelve a iniciar sesión.")
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.error_label.setText("Tu usuario no tiene permiso para ver predicciones.")
        else:
            self.error_label.setText(f"Error de comunicación con la API: {message}")

    def _on_pred_loaded(self, data: dict[str, Any], enfermedades: list[dict[str, Any]]) -> None:
        self.error_banner.setVisible(False)

        if enfermedades:
            # The API contract defines predictions only for transmissible
            # diseases (currently dengue). Do not offer chronic conditions
            # here, because they are statistical data only.
            predictable = [item for item in enfermedades if item.get("tipo") == "transmisible"]
            self.predictable_diseases = {
                str(item.get("clave")) for item in predictable if item.get("clave")
            }
            if not self.predictable_diseases:
                self.predictable_diseases = {"dengue"}
            current = self.combo_disease.currentData()
            self.combo_disease.blockSignals(True)
            self.combo_disease.clear()
            for d in predictable:
                clave = d.get("clave", "")
                nombre = d.get("nombre", clave)
                tipo = d.get("tipo", "")
                self.combo_disease.addItem(f"{nombre} ({tipo.capitalize()})", clave)
            idx = self.combo_disease.findData(current)
            self.combo_disease.setCurrentIndex(idx if idx >= 0 else 0)
            self.combo_disease.blockSignals(False)
            self.current_enfermedad = self.combo_disease.currentData() or "dengue"

        pred = data.get("prediccion")
        self._render_prediction(pred)

    def _render_empty(self) -> None:
        while self.disp_content_layout.count():
            item = self.disp_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        empty = EmptyStateWidget(
            icon="📊",
            title="Sin predicción activa",
            description="No se ha recuperado ninguna proyección epidemiológica para el periodo actual.",
        )
        self.disp_content_layout.addWidget(empty)

    def _render_prediction(self, pred: dict[str, Any] | None) -> None:
        while self.disp_content_layout.count():
            item = self.disp_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pred or not pred.get("semanas"):
            self._render_empty()
            return

        anio = pred.get("anio", 2026)
        mes = pred.get("mes", "--")
        semanas = pred.get("semanas", [])
        total = pred.get("total", sum(s for s in semanas if s is not None))
        creado_por = pred.get("creado_por", "Sistema")
        creada_en = str(pred.get("creado_en", "--"))[:16].replace("T", " ")

        # Header Title
        title_box = QFrame()
        title_box.setStyleSheet(".QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
        tl = QVBoxLayout(title_box)
        tl.setContentsMargins(10, 8, 10, 8)

        t_lbl = QLabel(f"Predicción para {mes:02d}/{anio}" if isinstance(mes, int) else f"Predicción para {mes}/{anio}")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub_lbl = QLabel(f"Enfermedad: {self.current_enfermedad.upper()} · Creado por: <b>{creado_por}</b> ({creada_en})")
        sub_lbl.setStyleSheet("font-size: 11px; color: #647C8C;")
        tl.addWidget(t_lbl)
        tl.addWidget(sub_lbl)
        self.disp_content_layout.addWidget(title_box)

        # 4 Weeks Grid
        weeks_lbl = QLabel("Casos estimados por semana")
        weeks_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #123B4A; margin-top: 4px;")
        self.disp_content_layout.addWidget(weeks_lbl)

        grid = QGridLayout()
        grid.setSpacing(10)
        for idx, val in enumerate(semanas[:4], start=1):
            val_txt = f"{val:.2f}" if isinstance(val, (int, float)) else str(val) if val is not None else "--"
            card = WeeklyCard(f"Semana {idx}", val_txt)
            grid.addWidget(card, 0, idx - 1)
        self.disp_content_layout.addLayout(grid)

        # Total Card
        tot_card = QFrame()
        tot_card.setStyleSheet(".QFrame { background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 12px; }")
        tcl = QHBoxLayout(tot_card)
        tcl.setContentsMargins(14, 10, 14, 10)
        tot_val = QLabel(f"Total proyectado mensual: <b>{total:.2f} casos estimados</b>")
        tot_val.setStyleSheet("font-size: 15px; color: #15803D; font-weight: 700;")
        tcl.addWidget(tot_val)
        tcl.addStretch()
        note = QLabel("Costa de Jalisco")
        note.setStyleSheet("font-size: 11px; color: #166534;")
        tcl.addWidget(note)
        self.disp_content_layout.addWidget(tot_card)

        # Disclaimer
        disc = QLabel(
            "Son casos estimados por el modelo a partir del clima y del historial; "
            "obtenidas a partir de covariables climáticas y registros históricos. No representan casos confirmados de dengue."
        )
        disc.setWordWrap(True)
        disc.setStyleSheet("font-size: 10.5px; color: #647C8C; font-style: italic; margin-top: 6px;")
        self.disp_content_layout.addWidget(disc)
        self.disp_content_layout.addStretch()

    def _submit_prediction(self) -> None:
        if not (self.user and self.user.role == UserRole.ADMIN):
            QMessageBox.warning(self, "Acceso restringido", "Solo administradores pueden generar predicciones.")
            return
        if self.current_enfermedad not in self.predictable_diseases:
            QMessageBox.warning(
                self,
                "Enfermedad no predictiva",
                "Solo las enfermedades transmisibles disponibles pueden registrarse como predicción.",
            )
            return

        if self.current_enfermedad != "dengue":
            QMessageBox.warning(self, "Modelo no disponible", "Por ahora el modelo solo predice dengue.")
            return

        self.btn_submit_pred.setEnabled(False)
        self.lbl_modelo.setText("Ejecutando el modelo…")
        self._mostrar_archivo()
        worker = ModelWorker(self.ruta_datos)
        worker.signals.done.connect(self._on_model_done)
        worker.signals.failed.connect(self._on_model_failed)
        self._model_worker = worker  # que Python no libere las señales antes de tiempo
        QThreadPool.globalInstance().start(worker)

    def _on_model_failed(self, mensaje: str) -> None:
        self.btn_submit_pred.setEnabled(True)
        self.lbl_modelo.setText("")
        QMessageBox.critical(self, "No se pudo ejecutar el modelo", mensaje)

    def _on_model_done(self, resultado: dict[str, Any]) -> None:
        self.btn_submit_pred.setEnabled(True)
        self.lbl_modelo.setText("")
        semanas = [float(v) for v in resultado["semanas"]]
        payload = {
            "enfermedad": self.current_enfermedad,
            "anio": int(resultado["anio"]),
            "mes": int(resultado["mes"]),
            "semanas": semanas,
        }
        detalle = "\n".join(
            f"   Semana del {inicio}: {valor:.2f} casos"
            for inicio, valor in zip(resultado.get("semanas_inicio", ["?"] * 4), semanas)
        )
        hoy = date.today()
        aviso_pasado = ""
        if (payload["anio"], payload["mes"]) < (hoy.year, hoy.month):
            aviso_pasado = (
                "\n\nAviso: el mes predicho ya pasó: los datos semanales no están al día. "
                "Si la envías, la alerta (si se genera) sería de un mes pasado."
            )

        resp = QMessageBox.question(
            self,
            "Resultado del modelo",
            f"El modelo predice para {payload['enfermedad'].upper()} en {payload['mes']:02d}/{payload['anio']} "
            f"(14 municipios de la Costa):\n\n{detalle}\n\n   Total: {sum(semanas):.2f} casos\n\n"
            "¿Enviar esta predicción a la API? Si supera al mismo mes del año anterior, se generará una alerta "
            f"pendiente de revisión.{aviso_pasado}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.loading_bar.setVisible(True)
        self.btn_submit_pred.setEnabled(False)

        worker = PredictionsWorker(
            epi_service=self.epi_service,
            action="create",
            create_payload=payload,
        )
        worker.signals.pred_created.connect(self._on_pred_created)
        worker.signals.error_occurred.connect(self._on_error_occurred)
        worker.signals.finished.connect(self._on_worker_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_pred_created(self, res: dict[str, Any]) -> None:
        alerta = res.get("alerta")
        msg = f"Predicción guardada: {res.get('total')} casos estimados."
        if alerta:
            msg += " Se generó una alerta pendiente de revisión."
        self.success_label.setText(msg)
        self.success_banner.setVisible(True)
        self.refresh_prediction()
