"""Módulo administrativo para la importación y carga masiva de datos CSV / Excel (Fase 5).

Endpoint:
POST /cargas/ (👑 solo ADMIN)

Implementa:
- Selector de archivos .csv y .xlsx
- Parser nativo con conversión de celdas vacías a None
- Vista previa interactiva de filas parseadas
- Validación previa fila por fila (año 2000-2100, mes 1-12, casos >= 0, rangos de clima)
- Detección de duplicados año/mes en el archivo
- Envío atómico "todo o nada" sin fragmentación
- Mapeo de errores de validación del backend (índice 0 -> Fila 2 de Excel)
- Despliegue de métricas de éxito (casos/clima creados y actualizados)
- Restricción estricta por rol (ADMIN habilitado, CONSULTA bloqueado)
- Petición asíncrona mediante QThreadPool
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.components.widgets import Card, MetricCard, PanelTitle
from app.core.exceptions import ApiError, ApiRequestError
from app.models.user import User, UserRole
from app.services.api.client import ApiClient
from app.services import model_runner
from app.services.epidemiology_service import EpidemiologyService
from app.utils.file_parser import parse_data_file


class UploadWorkerSignals(QObject):
    upload_succeeded = Signal(dict)
    error_occurred = Signal(dict, int)  # error_data, status_code
    finished = Signal()


class UploadWorker(QRunnable):
    """Background worker for batch dataset upload."""

    def __init__(self, epi_service: EpidemiologyService, rows: list[dict[str, Any]]) -> None:
        super().__init__()
        self.epi_service = epi_service
        self.rows = rows
        self.signals = UploadWorkerSignals()

    def run(self) -> None:
        try:
            res = self.epi_service.cargar_datos(self.rows)
            try:
                self.signals.upload_succeeded.emit(res)
            except RuntimeError:
                pass
        except ApiError as err:
            status = err.status or 0
            err_data = err.data if isinstance(err.data, dict) else {"detail": str(err.data)}
            try:
                self.signals.error_occurred.emit(err_data, status)
            except RuntimeError:
                pass
        except ApiRequestError:
            try:
                self.signals.error_occurred.emit({"detail": "No se pudo conectar con el servidor."}, 0)
            except RuntimeError:
                pass
        except Exception as ex:
            try:
                self.signals.error_occurred.emit({"detail": f"Error inesperado: {ex}"}, 0)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass


class DataUploadPage(QWidget):
    """Dataset upload and batch ingestion page."""

    def __init__(
        self,
        user: User | None = None,
        api_client: ApiClient | None = None,
        epi_service: EpidemiologyService | None = None,
    ) -> None:
        super().__init__()
        self.user = user
        self.api_client = api_client or ApiClient()
        self.epi_service = epi_service or EpidemiologyService(self.api_client)

        self.parsed_records: list[dict[str, Any]] = []
        self.validation_errors: list[str] = []
        self.selected_file_path: Path | None = None
        self.archivo_semanal: Path | None = None  # si se cargó el CSV semanal, también alimenta al modelo
        self.is_uploading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # 1. Header & File Selector Card
        root.addWidget(self._build_header_card())

        # 2. Status Banners (Success, Errors, Loading)
        self._build_banners(root)

        # 3. Validation Summary Card
        root.addWidget(self._build_validation_card())

        # 4. Preview Table Card
        root.addWidget(self._build_preview_card(), 1)

    def _build_header_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Carga de datos")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #123B4A;")
        sub = QLabel("Sube el archivo semanal por municipio (CSV). Actualiza las estadísticas y los datos del modelo.")
        sub.setWordWrap(True)
        sub.setMinimumWidth(300)
        sub.setObjectName("muted")
        sub.setStyleSheet("font-size: 11px; color: #647C8C;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_row.addLayout(title_box)

        top_row.addStretch()

        is_admin = self.user and self.user.role == UserRole.ADMIN

        self.btn_select_file = QPushButton("Seleccionar archivo")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.setEnabled(is_admin)
        self.btn_select_file.setStyleSheet(
            "background-color: #EAF0F5; color: #123B4A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 7px 14px; font-weight: 600;"
            if is_admin else
            "background-color: #F1F5F9; color: #94A3B8; border: 1px solid #E2E8F0; border-radius: 6px; padding: 7px 14px;"
        )
        self.btn_select_file.clicked.connect(self._select_file)
        top_row.addWidget(self.btn_select_file)

        self.btn_submit = QPushButton("Cargar datos")
        self.btn_submit.setObjectName("actionButton")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setEnabled(False)
        self.btn_submit.setStyleSheet("background-color: #123B4A; color: white; border-radius: 6px; padding: 7px 18px; font-weight: 700;")
        self.btn_submit.clicked.connect(self._confirm_and_upload)
        top_row.addWidget(self.btn_submit)

        layout.addLayout(top_row)

        if not is_admin:
            role_notice = QLabel("Solo los administradores pueden cargar datos.")
            role_notice.setStyleSheet("color: #92400E; background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600;")
            layout.addWidget(role_notice)

        # File info path label
        self.file_info_lbl = QLabel("Ningún archivo seleccionado.")
        self.file_info_lbl.setStyleSheet("font-size: 11.5px; color: #475569; font-style: italic;")
        layout.addWidget(self.file_info_lbl)

        return card

    def _build_banners(self, parent_layout: QVBoxLayout) -> None:
        # Loading Banner
        self.loading_bar = QFrame()
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet(".QFrame { background-color: #E0F2FE; border: 1px solid #BAE6FD; border-radius: 8px; padding: 8px; }")
        l_layout = QHBoxLayout(self.loading_bar)
        l_layout.setContentsMargins(12, 6, 12, 6)
        lbl = QLabel("Guardando datos…")
        lbl.setStyleSheet("color: #0369A1; font-weight: 600; font-size: 12px;")
        l_layout.addWidget(lbl)
        parent_layout.addWidget(self.loading_bar)

        # Success Banner
        self.success_banner = QFrame()
        self.success_banner.setVisible(False)
        self.success_banner.setStyleSheet(".QFrame { background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 10px; }")
        self.s_layout = QVBoxLayout(self.success_banner)
        self.s_layout.setContentsMargins(12, 8, 12, 8)
        self.s_layout.setSpacing(4)
        self.success_title = QLabel("Datos cargados.")
        self.success_title.setStyleSheet("color: #15803D; font-weight: 700; font-size: 13px;")
        self.success_detail = QLabel()
        self.success_detail.setStyleSheet("color: #166534; font-size: 12px;")
        self.s_layout.addWidget(self.success_title)
        self.s_layout.addWidget(self.success_detail)
        parent_layout.addWidget(self.success_banner)

        # Error Banner
        self.error_banner = QFrame()
        self.error_banner.setVisible(False)
        self.error_banner.setStyleSheet(".QFrame { background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 10px; }")
        self.e_layout = QVBoxLayout(self.error_banner)
        self.e_layout.setContentsMargins(12, 8, 12, 8)
        self.e_layout.setSpacing(4)
        self.error_title = QLabel("No se pudieron cargar los datos:")
        self.error_title.setStyleSheet("color: #991B1B; font-weight: 700; font-size: 13px;")
        self.error_detail = QLabel()
        self.error_detail.setWordWrap(True)
        self.error_detail.setStyleSheet("color: #B91C1C; font-size: 11.5px;")
        self.e_layout.addWidget(self.error_title)
        self.e_layout.addWidget(self.error_detail)
        parent_layout.addWidget(self.error_banner)

    def _build_validation_card(self) -> QWidget:
        self.card_validation = Card()
        self.val_layout = QVBoxLayout(self.card_validation)
        self.val_layout.setContentsMargins(16, 10, 16, 10)
        self.val_layout.setSpacing(6)

        v_head = QHBoxLayout()
        v_title = QLabel("Revisión del archivo")
        v_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #123B4A;")
        v_head.addWidget(v_title)
        v_head.addStretch()
        self.val_status_badge = QLabel("Sin archivo")
        self.val_status_badge.setStyleSheet("background-color: #E2E8F0; color: #475569; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;")
        v_head.addWidget(self.val_status_badge)
        self.val_layout.addLayout(v_head)

        self.val_msg = QLabel("Elige el archivo semanal por municipio (mismo formato que Dengue Clima Semanal.csv). También se acepta la plantilla mensual.")
        self.val_msg.setWordWrap(True)
        self.val_msg.setStyleSheet("font-size: 11.5px; color: #647C8C;")
        self.val_layout.addWidget(self.val_msg)

        return self.card_validation

    def _build_preview_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        p_head = QHBoxLayout()
        p_title = QLabel("Vista previa")
        p_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #123B4A;")
        p_head.addWidget(p_title)
        p_head.addStretch()
        self.preview_count_lbl = QLabel("0 filas listas")
        self.preview_count_lbl.setStyleSheet("font-size: 11px; color: #647C8C;")
        p_head.addWidget(self.preview_count_lbl)
        layout.addLayout(p_head)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(7)
        self.preview_table.setHorizontalHeaderLabels([
            "Fila Excel", "Año", "Mes", "Casos Dengue", "Temperatura (°C)", "Humedad (%)", "Precipitación (mm)"
        ])
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(240)

        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.preview_table)
        return card

    # -------------------------------------------------------------------------
    # File Selection & Parsing
    # -------------------------------------------------------------------------

    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de datos epidemiológicos y climáticos",
            "",
            "Archivos de datos (*.csv *.xlsx *.xlsm);;Archivos CSV (*.csv);;Archivos Excel (*.xlsx *.xlsm)",
        )
        if not file_path:
            return

        p = Path(file_path)
        self.selected_file_path = p
        self.file_info_lbl.setText(f"Archivo: <b>{p.name}</b> ({p.stat().st_size:,} bytes)")
        self.success_banner.setVisible(False)
        self.error_banner.setVisible(False)

        self.archivo_semanal = None
        try:
            if model_runner.es_archivo_semanal(p):
                # mismo cálculo que generar_plantilla_mensual.py, con el entorno del modelo
                self.file_info_lbl.setText(f"Archivo: <b>{p.name}</b> · calculando totales mensuales…")
                self.setCursor(Qt.CursorShape.WaitCursor)
                try:
                    records = model_runner.resumen_mensual(p)
                finally:
                    self.unsetCursor()
                self.archivo_semanal = p
                self.file_info_lbl.setText(
                    f"Archivo semanal: <b>{p.name}</b> ({p.stat().st_size:,} bytes) → {len(records)} meses de la Costa. "
                    "Al cargarlo también se usará para el modelo."
                )
            else:
                records = parse_data_file(p)
            self.parsed_records = records
            self._validate_and_render_preview(records)
        except Exception as ex:
            self.parsed_records = []
            self.validation_errors = [f"Error al leer el archivo: {ex}"]
            self.val_status_badge.setText("No se pudo leer")
            self.val_status_badge.setStyleSheet("background-color: #FEE2E2; color: #DC2626; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;")
            self.val_msg.setText(f"No se pudo parsear el archivo: {ex}")
            self.val_msg.setStyleSheet("color: #DC2626; font-size: 11.5px;")
            self.btn_submit.setEnabled(False)
            self.preview_table.setRowCount(0)
            self.preview_count_lbl.setText("0 filas")

    def _validate_and_render_preview(self, records: list[dict[str, Any]]) -> None:
        errors: list[str] = []
        seen_keys: set[tuple[int, int]] = set()

        if not records:
            errors.append("El archivo no contiene filas de datos válidas.")

        for idx, r in enumerate(records):
            excel_row = idx + 2
            anio = r.get("anio")
            mes = r.get("mes")
            casos = r.get("casos_dengue")
            temp = r.get("temperatura_c")
            hum = r.get("humedad_pct")
            prec = r.get("precipitacion_mm")

            if anio is None:
                errors.append(f"Fila {excel_row}: El campo 'anio' es obligatorio.")
            elif not isinstance(anio, int) or anio < 2000 or anio > 2100:
                errors.append(f"Fila {excel_row}: 'anio' debe ser un número entero entre 2000 y 2100 (valor: {anio}).")

            if mes is None:
                errors.append(f"Fila {excel_row}: El campo 'mes' es obligatorio.")
            elif not isinstance(mes, int) or mes < 1 or mes > 12:
                errors.append(f"Fila {excel_row}: 'mes' debe ser entre 1 y 12 (valor: {mes}).")

            if anio and mes:
                key = (anio, mes)
                if key in seen_keys:
                    errors.append(f"Fila {excel_row}: Periodo duplicado ({mes}/{anio}) en el mismo envío.")
                else:
                    seen_keys.add(key)

            if casos is not None and (not isinstance(casos, int) or casos < 0):
                errors.append(f"Fila {excel_row}: 'casos_dengue' debe ser un número entero >= 0 o vacío.")

            if temp is not None and (not isinstance(temp, (int, float)) or not (-20 <= float(temp) <= 60)):
                errors.append(f"Fila {excel_row}: 'temperatura_c' fuera de rango (-20 a 60 °C).")

            if hum is not None and (not isinstance(hum, (int, float)) or not (0 <= float(hum) <= 100)):
                errors.append(f"Fila {excel_row}: 'humedad_pct' fuera de rango (0 a 100 %).")

            if prec is not None and (not isinstance(prec, (int, float)) or float(prec) < 0):
                errors.append(f"Fila {excel_row}: 'precipitacion_mm' debe ser >= 0 o vacío.")

        self.validation_errors = errors

        # Update Validation Status
        if errors:
            self.val_status_badge.setText(f"{len(errors)} errores")
            self.val_status_badge.setStyleSheet("background-color: #FEE2E2; color: #DC2626; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;")
            summary_text = f"Se detectaron {len(errors)} problema(s) de validación:\n• " + "\n• ".join(errors[:5])
            if len(errors) > 5:
                summary_text += f"\n• ... y {len(errors) - 5} error(es) más."
            self.val_msg.setText(summary_text)
            self.val_msg.setStyleSheet("color: #DC2626; font-size: 11.5px; font-weight: 500;")
            self.btn_submit.setEnabled(False)
        else:
            self.val_status_badge.setText("Sin errores")
            self.val_status_badge.setStyleSheet("background-color: #DCFCE7; color: #15803D; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 4px;")
            self.val_msg.setText(f"{len(records)} meses listos para cargar.")
            self.val_msg.setStyleSheet("color: #15803D; font-size: 11.5px; font-weight: 600;")
            self.btn_submit.setEnabled(self.user and self.user.role == UserRole.ADMIN)

        # Render Table
        self.preview_table.setRowCount(len(records))
        self.preview_count_lbl.setText(f"{len(records)} meses")

        for r, row in enumerate(records):
            excel_row = r + 2
            anio_str = str(row.get("anio", "--"))
            mes_str = str(row.get("mes", "--"))
            casos_str = str(row.get("casos_dengue")) if row.get("casos_dengue") is not None else "— (sin cambio)"
            temp_str = f"{row.get('temperatura_c'):.1f} °C" if row.get("temperatura_c") is not None else "—"
            hum_str = f"{row.get('humedad_pct'):.1f} %" if row.get("humedad_pct") is not None else "—"
            prec_str = f"{row.get('precipitacion_mm'):.1f} mm" if row.get("precipitacion_mm") is not None else "—"

            it_r = QTableWidgetItem(f"Fila {excel_row}")
            it_r.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_a = QTableWidgetItem(anio_str)
            it_a.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_m = QTableWidgetItem(mes_str)
            it_m.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_c = QTableWidgetItem(casos_str)
            it_c.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_t = QTableWidgetItem(temp_str)
            it_t.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_h = QTableWidgetItem(hum_str)
            it_h.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_p = QTableWidgetItem(prec_str)
            it_p.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.preview_table.setItem(r, 0, it_r)
            self.preview_table.setItem(r, 1, it_a)
            self.preview_table.setItem(r, 2, it_m)
            self.preview_table.setItem(r, 3, it_c)
            self.preview_table.setItem(r, 4, it_t)
            self.preview_table.setItem(r, 5, it_h)
            self.preview_table.setItem(r, 6, it_p)

    # -------------------------------------------------------------------------
    # Upload Submission & Response Handling
    # -------------------------------------------------------------------------

    def _confirm_and_upload(self) -> None:
        if not (self.user and self.user.role == UserRole.ADMIN):
            QMessageBox.warning(self, "Acceso denegado", "Solo usuarios con rol Administrador pueden cargar datos.")
            return

        if self.validation_errors:
            QMessageBox.critical(self, "Errores de validación", "Corrige los errores antes de enviar el lote.")
            return

        if not self.parsed_records:
            QMessageBox.warning(self, "Sin datos", "No hay filas para enviar.")
            return

        resp = QMessageBox.question(
            self,
            "Cargar datos",
            f"¿Estás seguro de que deseas enviar {len(self.parsed_records)} registro(s) mensuales al sistema?\n\n"
            + ("El archivo semanal también quedará como los datos del modelo de predicción.\n\n" if self.archivo_semanal else "")
            + "El backend ejecutará una operación de todo o nada: si un solo registro es inválido, no se guardará ninguno.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.is_uploading = True
        self.btn_submit.setEnabled(False)
        self.btn_select_file.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.success_banner.setVisible(False)
        self.error_banner.setVisible(False)

        worker = UploadWorker(self.epi_service, self.parsed_records)
        worker.signals.upload_succeeded.connect(self._on_upload_success)
        worker.signals.error_occurred.connect(self._on_upload_error)
        worker.signals.finished.connect(self._on_upload_finished)

        QThreadPool.globalInstance().start(worker)

    def _on_upload_finished(self) -> None:
        self.is_uploading = False
        self.btn_select_file.setEnabled(True)
        self.btn_submit.setEnabled(len(self.parsed_records) > 0 and len(self.validation_errors) == 0)
        self.loading_bar.setVisible(False)

    def _on_upload_success(self, res: dict[str, Any]) -> None:
        casos = res.get("casos", {})
        clima = res.get("clima", {})

        c_cr = casos.get("creados", 0)
        c_ac = casos.get("actualizados", 0)
        cl_cr = clima.get("creados", 0)
        cl_ac = clima.get("actualizados", 0)

        detail_text = (
            f"• Casos de dengue: <b>{c_cr}</b> creados, <b>{c_ac}</b> actualizados.<br>"
            f"• Registros climáticos: <b>{cl_cr}</b> creados, <b>{cl_ac}</b> actualizados.<br>"
            "La base de datos epidemiológica regional se encuentra actualizada."
        )
        if self.archivo_semanal:
            try:
                shutil.copyfile(self.archivo_semanal, model_runner.DATOS_CARGADOS)
                detail_text += "<br>• El modelo usará este archivo. Ve a <b>Predicciones</b> → <b>Ejecutar modelo</b>."
            except OSError as error:
                detail_text += f"<br>No se pudo guardar el archivo para el modelo: {error}"
        self.success_detail.setText(detail_text)
        self.success_banner.setVisible(True)
        self.error_banner.setVisible(False)

    def _on_upload_error(self, err_data: dict[str, Any], status: int) -> None:
        self.error_banner.setVisible(True)
        self.success_banner.setVisible(False)

        if status == 400:
            # Map backend error indices: index 0 is Excel row 2
            err_lines: list[str] = []
            for k, val in err_data.items():
                if k.isdigit():
                    excel_row = int(k) + 2
                    if isinstance(val, dict):
                        for field, msgs in val.items():
                            msg_str = ", ".join(msgs) if isinstance(msgs, list) else str(msgs)
                            err_lines.append(f"Fila {excel_row} (Excel) · Campo '{field}': {msg_str}")
                    else:
                        err_lines.append(f"Fila {excel_row} (Excel): {val}")
                elif k == "detail":
                    err_lines.append(str(val))
                else:
                    err_lines.append(f"'{k}': {val}")

            self.error_detail.setText("<br>".join(err_lines) if err_lines else "Datos del lote inválidos.")
        elif status == 401:
            self.error_detail.setText("Tu sesión expiró. Vuelve a iniciar sesión.")
            if self.api_client.on_unauthorized:
                self.api_client.on_unauthorized()
        elif status == 403:
            self.error_detail.setText("Solo los administradores pueden cargar datos.")
        else:
            self.error_detail.setText(f"Error al enviar datos (HTTP {status}): {err_data.get('detail', err_data)}")
