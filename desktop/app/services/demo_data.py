"""Dashboard values transcribed from the supplied technical report.

They are historical/cut-off values, not live information from the API.
"""

DASHBOARD_METRICS = [
    ("Registros totales", "15,467", "Expedientes analizados, 2020–2026", "#123B4A"),
    ("Casos confirmados", "2,203", "Confirmación acumulada en el informe", "#1B4E81"),
    ("Casos probables", "9,029", "Registros clasificados como probables", "#356E8A"),
    ("Casos descartados", "4,235", "Registros descartados en el periodo", "#6F7E87"),
    ("Municipios monitoreados", "14", "Costa Sur y Costa-Sierra Occidental", "#123B4A"),
]

HISTORICAL_CONFIRMED = [(2020, 391), (2021, 67), (2022, 2), (2023, 63), (2024, 1384), (2025, 284), (2026, 12)]

MUNICIPAL_CONFIRMED = [
    ("Puerto Vallarta", 1100), ("Cihuatlán", 222), ("La Huerta", 199),
    ("Cuautitlán de García Barragán", 147), ("Tomatlán", 144), ("Casimiro Castillo", 137),
]

MONITORED_MUNICIPALITIES = {
    "Costa Sur": ["Casimiro Castillo", "Cihuatlán", "Cuautitlán de García Barragán", "La Huerta", "Tomatlán", "Villa Purificación"],
    "Costa-Sierra Occidental": ["Atenguillo", "Cabo Corrientes", "Guachinango", "Mascota", "Mixtlán", "Puerto Vallarta", "San Sebastián del Oeste", "Talpa de Allende"],
}

RECENT_ROWS = [
    ("Informe técnico integral", "2020–2026", "Corte al 27 oct. 2026", "Septiembre y octubre concentran las mayores proporciones exploratorias."),
]

ALERT_ROWS = [
    ("Sin alerta emitida", "—", "Información insuficiente", "No existen umbrales aprobados ni modelo validado."),
]

FOLLOW_UP_ROWS = [
    ("Clasificación pendiente", "—", "Información insuficiente"),
]
