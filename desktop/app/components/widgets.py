"""Reusable UI components for HACKAJAL PySide6 interface."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class NavButton(QPushButton):
    def __init__(self, icon: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(f"{icon}   {text}", parent)
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class MetricCard(Card):
    def __init__(self, label: str, value: str, note: str, accent: str = "#123B4A") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        heading = QLabel(label)
        heading.setObjectName("metricLabel")
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setStyleSheet(f"color: {accent}; font-size: 24px; font-weight: 700;")
        value_label.setWordWrap(True)
        note_label = QLabel(note)
        note_label.setObjectName("muted")
        note_label.setStyleSheet("font-size: 11px;")
        note_label.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(value_label)
        layout.addWidget(note_label)


class WeeklyCard(QFrame):
    """Compact card for weekly predictions."""

    def __init__(self, week_title: str, value_text: str, subtitle: str = "Casos estimados") -> None:
        super().__init__()
        self.setStyleSheet("""
            QFrame {
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

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 28px;")

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")

        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setObjectName("muted")
        desc_label.setStyleSheet("font-size: 12px; color: #64748B;")
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
