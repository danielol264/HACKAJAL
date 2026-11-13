"""Central visual language for the desktop application."""

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
QMainWindow, QWidget {
    background-color: #F3F6F9;
    color: #183447;
    font-family: 'Segoe UI', Arial;
    font-size: 13px;
}

/* BARRA LATERAL */
QFrame#sidebar {
    background-color: #102F4B;
}

/* IDENTIDAD INSTITUCIONAL */
QFrame#identityBlock {
    background-color: #173F63;
    border: 1px solid #42698B;
    border-radius: 9px;
}

QLabel#brand {
    background: transparent;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
}

QLabel#brandSubtitle {
    background: transparent;
    color: #C3D7E6;
    font-size: 10px;
}

QLabel#institutionalPlaceholder {
    background: transparent;
    color: #D8E4EE;
    font-size: 10px;
}

/* NAVEGACIÓN */
QPushButton#navButton {
    background: transparent;
    color: #DCE8F1;
    border: none;
    border-radius: 7px;
    text-align: left;
    padding: 11px 14px;
    font-size: 13px;
}

QPushButton#navButton:hover {
    background-color: #1C527C;
}

QPushButton#navButton:checked {
    background-color: #245F8E;
    color: white;
    font-weight: 600;
}

/* ENCABEZADO Y TARJETAS */
QFrame#topbar,
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #D9E3EA;
    border-radius: 10px;
}

/* TEXTOS */
QLabel#pageTitle {
    background: transparent;
    font-size: 23px;
    font-weight: 700;
    color: #123B5D;
}

QLabel#eyebrow,
QLabel#muted {
    background: transparent;
    color: #647C8C;
}

QLabel#metricValue {
    background: transparent;
    color: #174F79;
    font-size: 25px;
    font-weight: 700;
}

QLabel#metricLabel {
    background: transparent;
    color: #647C8C;
    font-size: 11px;
}

/* ETIQUETAS */
QLabel#demoBadge {
    background-color: #FFF3E5;
    color: #A65D16;
    border: 1px solid #FCD34D;
    border-radius: 8px;
    padding: 4px 10px;
    font-weight: 600;
}

QLabel#statusBadge {
    background-color: #EAF2F8;
    color: #205889;
    border-radius: 8px;
    padding: 4px 8px;
    font-weight: 600;
}

QLabel#statusBadgePending {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#statusBadgeConfirmed {
    background-color: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FCA5A5;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#statusBadgeDiscarded {
    background-color: #F3F4F6;
    color: #4B5563;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#predictionBadge {
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1px solid #BAE6FD;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}

/* COMBOBOX Y SELECTORES */
QComboBox {
    background-color: #FFFFFF;
    color: #123B4A;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #028090;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #183447;
    selection-background-color: #123B4A;
    selection-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
}

/* BOTONES */
QPushButton#refreshButton,
QPushButton#actionButton {
    background-color: #123B4A;
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#refreshButton:hover,
QPushButton#actionButton:hover {
    background-color: #1B4E81;
}

QPushButton#refreshButton:disabled,
QPushButton#actionButton:disabled {
    background-color: #94A3B8;
    color: #E2E8F0;
}

QPushButton#secondaryButton {
    background-color: #EAF0F5;
    color: #123B4A;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#secondaryButton:hover {
    background-color: #DDE6ED;
}

QPushButton#retryButton {
    background-color: #BD4B4B;
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#retryButton:hover {
    background-color: #A13838;
}

/* SCROLL AREA */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #EAF0F5;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* TABLAS */
QTableWidget {
    background-color: #FFFFFF;
    color: #183447;
    border: 1px solid #D9E3EA;
    border-radius: 8px;
    gridline-color: #EDF1F5;
}

QHeaderView::section {
    background-color: #EAF0F5;
    color: #405F76;
    border: none;
    padding: 9px;
    font-weight: 600;
}

QTableWidget::item {
    padding: 7px;
}
"""