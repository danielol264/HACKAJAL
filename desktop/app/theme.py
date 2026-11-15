"""Lenguaje visual de la app de escritorio (misma paleta institucional de siempre)."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

COLORS = {
    "navy": "#123B5D",
    "navy_dark": "#0B2942",
    "teal": "#23658A",
    "teal_light": "#EAF2F8",
    "background": "#F3F6F9",
    "surface": "#FFFFFF",
    "text": "#183447",
    "muted": "#647C8C",
    "border": "#D9E3EA",
    "warning": "#C47A27",
    "danger": "#BD4B4B",
}

STYLESHEET = """
/* Base: solo las ventanas pintan fondo; lo demás es transparente para no dejar recuadros grises */
QWidget {
    background: transparent;
    color: #183447;
    font-family: 'Segoe UI', Arial;
    font-size: 13px;
}

QMainWindow, QDialog, QMessageBox, QWidget#appRoot, QWidget#loginForm {
    background-color: #F3F6F9;
}

QToolTip {
    background-color: #102F4B;
    color: #FFFFFF;
    border: none;
    padding: 6px 8px;
    border-radius: 4px;
}

/* Barra lateral */
QFrame#sidebar {
    background-color: #102F4B;
}

QFrame#identityBlock {
    background-color: #173F63;
    border: 1px solid #2A5476;
    border-radius: 8px;
}

QLabel#brand {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 700;
}

QLabel#brandSubtitle {
    color: #C3D7E6;
    font-size: 10px;
}

QLabel#institutionalPlaceholder {
    color: #D8E4EE;
    font-size: 10px;
}

QPushButton#navButton {
    background: transparent;
    color: #DCE8F1;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 9px 12px;
    font-size: 13px;
}

QPushButton#navButton:hover {
    background-color: #1C527C;
}

QPushButton#navButton:checked {
    background-color: #245F8E;
    color: #FFFFFF;
    font-weight: 600;
}

/* Barra superior y tarjetas */
QFrame#topbar {
    background-color: #FFFFFF;
    border: none;
    border-bottom: 1px solid #D9E3EA;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #D9E3EA;
    border-radius: 8px;
}

/* Textos */
QLabel#pageTitle {
    font-size: 20px;
    font-weight: 700;
    color: #123B5D;
}

QLabel#eyebrow,
QLabel#muted {
    color: #647C8C;
}

QLabel#metricValue {
    color: #174F79;
    font-size: 24px;
    font-weight: 700;
}

QLabel#metricLabel {
    color: #647C8C;
    font-size: 11px;
}

/* Etiquetas de estado */
QLabel#demoBadge {
    background-color: #FFF3E5;
    color: #A65D16;
    border: 1px solid #FCD34D;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusBadge {
    background-color: #EAF2F8;
    color: #205889;
    border-radius: 4px;
    padding: 3px 8px;
    font-weight: 600;
}

QLabel#statusBadgePending {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusBadgeConfirmed {
    background-color: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FCA5A5;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#statusBadgeDiscarded {
    background-color: #F3F4F6;
    color: #4B5563;
    border: 1px solid #E5E7EB;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#predictionBadge {
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1px solid #BAE6FD;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* Campos de captura */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #FFFFFF;
    color: #183447;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 9px;
    selection-background-color: #23658A;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #028090;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
}

QComboBox {
    background-color: #FFFFFF;
    color: #123B4A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #028090;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #183447;
    selection-background-color: #123B4A;
    selection-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    outline: 0;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #94A3B8;
    border-radius: 3px;
    background: #FFFFFF;
}

QCheckBox::indicator:checked {
    background: #028090;
    border-color: #028090;
}

/* Botones: uno principal (oscuro) y el resto secundarios (claros) */
QPushButton {
    background-color: #FFFFFF;
    color: #123B4A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #EAF0F5;
}

QPushButton:disabled {
    color: #94A3B8;
    background-color: #F1F5F9;
    border-color: #E2E8F0;
}

QPushButton#refreshButton,
QPushButton#actionButton {
    background-color: #123B4A;
    color: #FFFFFF;
    border: 1px solid #123B4A;
}

QPushButton#refreshButton:hover,
QPushButton#actionButton:hover {
    background-color: #1B4E81;
}

QPushButton#refreshButton:disabled,
QPushButton#actionButton:disabled {
    background-color: #94A3B8;
    border-color: #94A3B8;
    color: #E2E8F0;
}

QPushButton#secondaryButton {
    background-color: #EAF0F5;
    color: #123B4A;
    border: 1px solid #CBD5E1;
}

QPushButton#secondaryButton:hover {
    background-color: #DDE6ED;
}

QPushButton#retryButton {
    background-color: #BD4B4B;
    color: #FFFFFF;
    border: 1px solid #BD4B4B;
}

QPushButton#retryButton:hover {
    background-color: #A13838;
}

/* Desplazamiento */
QScrollArea {
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 28px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 3px;
    min-width: 28px;
}

QScrollBar::handle:hover {
    background: #94A3B8;
}

QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    width: 0px;
    height: 0px;
    background: none;
}

QSplitter::handle {
    background: transparent;
}

/* Tablas */
QTableWidget, QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    color: #183447;
    border: 1px solid #D9E3EA;
    border-radius: 6px;
    gridline-color: #EDF1F5;
    selection-background-color: #DCEBF2;
    selection-color: #123B4A;
}

QHeaderView {
    background-color: #EAF0F5;
}

QHeaderView::section {
    background-color: #EAF0F5;
    color: #405F76;
    border: none;
    border-bottom: 1px solid #D9E3EA;
    padding: 8px;
    font-weight: 600;
}

QTableWidget::item {
    padding: 6px;
}

QTableCornerButton::section {
    background-color: #EAF0F5;
    border: none;
}
"""


def instalar_estilos(app: QApplication) -> None:
    """Aplica la hoja de estilos global a toda la aplicación."""
    app.setStyleSheet(STYLESHEET)
