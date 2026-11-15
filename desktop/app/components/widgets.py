"""Reusable UI components for HACKAJAL PySide6 interface."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class NavButton(QPushButton):
    def __init__(self, icon: str, text: str, parent: QWidget | None = None) -> None:
        self.icon_str = icon
        self.label_str = text
        super().__init__(f"{icon}   {text}", parent)
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self.setText(self.icon_str)
            self.setStyleSheet("QPushButton#navButton { text-align: center; padding: 10px 0; font-size: 15px; }")
        else:
            self.setText(f"{self.icon_str}   {self.label_str}")
            self.setStyleSheet("")


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class MetricCard(Card):
    def __init__(self, label: str, value: str, note: str, accent: str = "#123B4A") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)
        self.heading = QLabel(label)
        self.heading.setObjectName("metricLabel")
        self.heading.setStyleSheet("font-size: 11px; font-weight: 600; color: #647C8C;")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 20px; font-weight: 700;")
        self.value_label.setWordWrap(True)
        self.note_label = QLabel(note)
        self.note_label.setObjectName("muted")
        self.note_label.setStyleSheet("font-size: 10.5px; color: #647C8C;")
        self.note_label.setWordWrap(True)
        layout.addWidget(self.heading)
        layout.addWidget(self.value_label)
        layout.addWidget(self.note_label)

    def update_value(self, value: str) -> None:
        self.value_label.setText(value)


class WeeklyCard(QFrame):
    """Compact card for weekly predictions."""

    def __init__(self, week_title: str, value_text: str, subtitle: str = "Casos estimados") -> None:
        super().__init__()
        self.setStyleSheet("""
            .WeeklyCard {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        title = QLabel(week_title)
        title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        val = QLabel(value_text)
        val.setStyleSheet("font-size: 18px; font-weight: 700; color: #028090;")
        sub = QLabel(subtitle)
        sub.setStyleSheet("font-size: 10px; color: #94A3B8;")
        layout.addWidget(title)
        layout.addWidget(val)
        layout.addWidget(sub)


class PanelTitle(QWidget):
    def __init__(self, title: str, detail: str = "") -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #123B4A;")
        layout.addWidget(title_label)
        layout.addStretch()
        if detail:
            label = QLabel(detail)
            label.setObjectName("muted")
            label.setStyleSheet("font-size: 11px; color: #647C8C;")
            layout.addWidget(label)


class AlertBadge(QLabel):
    def __init__(self, estado: str) -> None:
        super().__init__(estado.capitalize())
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if estado == "pendiente":
            self.setObjectName("statusBadgePending")
        elif estado == "confirmada":
            self.setObjectName("statusBadgeConfirmed")
        else:
            self.setObjectName("statusBadgeDiscarded")


class EmptyStateWidget(QWidget):
    """Informative empty state card with icon, title, description."""

    def __init__(self, icon: str, title: str, description: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #123B4A;")

        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setObjectName("muted")
        desc_label.setStyleSheet("font-size: 12px; color: #64748B;")
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)


# ---------- Ajuste automático al tamaño de la ventana ----------

class GridReflow(QObject):
    """Reacomoda un QGridLayout en 1..max_cols columnas según el ancho disponible de `host`.

    Las tarjetas conservan su orden (fila, columna) original; si la ventana se hace angosta
    bajan a la siguiente fila en lugar de aplastarse o cortarse.
    """

    def __init__(self, host: QWidget, grid: QGridLayout, min_width: int, max_cols: int) -> None:
        super().__init__(host)
        self.host, self.grid, self.min_width, self.max_cols = host, grid, min_width, max_cols
        host.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Resize:
            self.apply()
        return False

    def apply(self) -> None:
        posiciones = []
        for i in range(self.grid.count()):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                fila, col, _, _ = self.grid.getItemPosition(i)
                posiciones.append(((fila, col), widget))
        if not posiciones:
            return
        widgets = [w for _, w in sorted(posiciones, key=lambda p: p[0])]
        ancho = max(self.host.width(), 1)
        cols = max(1, min(self.max_cols, len(widgets), ancho // self.min_width))
        actuales = [tuple(self.grid.getItemPosition(self.grid.indexOf(w))[:2]) for w in widgets]
        deseadas = [(i // cols, i % cols) for i in range(len(widgets))]
        if actuales != deseadas:
            for w in widgets:
                self.grid.removeWidget(w)
            for i, w in enumerate(widgets):
                self.grid.addWidget(w, i // cols, i % cols)
        for c in range(max(self.max_cols, cols)):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)


class SplitterReflow(QObject):
    """Pone un QSplitter en vertical cuando `host` es más angosto que `breakpoint`."""

    def __init__(self, host: QWidget, splitter: QSplitter, breakpoint: int) -> None:
        super().__init__(host)
        self.host, self.splitter, self.breakpoint = host, splitter, breakpoint
        host.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Resize:
            vertical = self.host.width() < self.breakpoint
            orientacion = Qt.Orientation.Vertical if vertical else Qt.Orientation.Horizontal
            if self.splitter.orientation() != orientacion:
                self.splitter.setOrientation(orientacion)
        return False


def scrollable(page: QWidget) -> QScrollArea:
    """Envuelve una pantalla en un área con desplazamiento vertical y horizontal."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(page)
    return area
