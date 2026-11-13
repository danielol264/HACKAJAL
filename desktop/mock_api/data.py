"""Simulated database and fixtures for HACKAJAL Mock API.

All mock data is explicitly identified with [SIMULADO] or similar markers
to ensure zero ambiguity between mock data and real production records.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

# Default Mock Users
# Note: aliases allow both official institutional email and simplified email.
DEFAULT_USERS = {
    "admin@hackajal.salud.gob.mx": {
        "email": "admin@hackajal.salud.gob.mx",
        "password": "AdminPassword123!",
        "nombre": "Daniel Ramos [SIMULADO]",
        "rol": "admin",
        "organizacion": "Secretaría de Salud Jalisco [SIMULADO]",
        "is_registered": True,
    },
    "admin@correo.com": {
        "email": "admin@correo.com",
        "password": "admin123",
        "nombre": "Daniel Ramos [SIMULADO]",
        "rol": "admin",
        "organizacion": "Equipo HackaJal [SIMULADO]",
        "is_registered": True,
    },
    "consulta@hackajal.salud.gob.mx": {
        "email": "consulta@hackajal.salud.gob.mx",
        "password": "ConsultaPassword123!",
        "nombre": "Dra. Elena Vega [SIMULADO]",
        "rol": "consulta",
        "organizacion": "Región Sanitaria VIII Costa Sur [SIMULADO]",
        "is_registered": True,
    },
    "consulta@correo.com": {
        "email": "consulta@correo.com",
        "password": "consulta123",
        "nombre": "Dra. Elena Vega [SIMULADO]",
        "rol": "consulta",
        "organizacion": "Región Sanitaria VIII Costa Sur [SIMULADO]",
        "is_registered": True,
    },
    "noregistrado@hackajal.salud.gob.mx": {
        "email": "noregistrado@hackajal.salud.gob.mx",
        "password": "Password123!",
        "nombre": "Usuario Sin Registro [SIMULADO]",
        "rol": "consulta",
        "organizacion": "Externo [SIMULADO]",
        "is_registered": False,
    },
    "no_registrado@correo.com": {
        "email": "no_registrado@correo.com",
        "password": "password123",
        "nombre": "Usuario Sin Registro [SIMULADO]",
        "rol": "consulta",
        "organizacion": "Externo [SIMULADO]",
        "is_registered": False,
    },
}

# 14 Monitored Municipalities of Jalisco Coastal Region (Costa Sur & Costa-Sierra Occidental)
DEFAULT_MUNICIPIOS = [
    {"clave_inegi": "14021", "nombre": "Casimiro Castillo [SIMULADO]", "region": "Costa Sur", "latitud": 19.60, "longitud": -104.43},
    {"clave_inegi": "14022", "nombre": "Cihuatlán [SIMULADO]", "region": "Costa Sur", "latitud": 19.23, "longitud": -104.57},
    {"clave_inegi": "14027", "nombre": "Cuautitlán de García Barragán [SIMULADO]", "region": "Costa Sur", "latitud": 19.46, "longitud": -104.38},
    {"clave_inegi": "14056", "nombre": "La Huerta [SIMULADO]", "region": "Costa Sur", "latitud": 19.48, "longitud": -104.64},
    {"clave_inegi": "14101", "nombre": "Tomatlán [SIMULADO]", "region": "Costa Sur", "latitud": 19.93, "longitud": -105.25},
    {"clave_inegi": "14113", "nombre": "Villa Purificación [SIMULADO]", "region": "Costa Sur", "latitud": 19.72, "longitud": -104.61},
    {"clave_inegi": "14012", "nombre": "Atenguillo [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.35, "longitud": -104.51},
    {"clave_inegi": "14020", "nombre": "Cabo Corrientes [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.45, "longitud": -105.42},
    {"clave_inegi": "14037", "nombre": "Guachinango [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.75, "longitud": -104.42},
    {"clave_inegi": "14058", "nombre": "Mascota [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.53, "longitud": -104.79},
    {"clave_inegi": "14061", "nombre": "Mixtlán [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.60, "longitud": -104.53},
    {"clave_inegi": "14067", "nombre": "Puerto Vallarta [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.62, "longitud": -105.23},
    {"clave_inegi": "14079", "nombre": "San Sebastián del Oeste [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.76, "longitud": -104.85},
    {"clave_inegi": "14106", "nombre": "Talpa de Allende [SIMULADO]", "region": "Costa-Sierra Occidental", "latitud": 20.38, "longitud": -104.82},
]

# Registered Diseases
DEFAULT_ENFERMEDADES = [
    {"clave": "dengue", "nombre": "Dengue [SIMULADO]", "tipo": "transmisible"},
    {"clave": "dm2", "nombre": "Diabetes mellitus tipo 2 [SIMULADO]", "tipo": "cronica"},
]

# Active Prediction for Dengue
DEFAULT_PREDICCION = {
    "anio": 2026,
    "mes": 12,
    "semanas": [1.2, 1.96, 0.8, 0.5],
    "total": 4.46,
    "creado_por": "Daniel Ramos [SIMULADO]",
    "creado_en": "2026-11-13T14:15:00Z",
}

# Historical Dengue Cases by Year and Month
DEFAULT_CASOS_POR_MES = {
    2026: [
        {"enfermedad": "dengue", "mes": 1, "casos": 18},
        {"enfermedad": "dengue", "mes": 2, "casos": 15},
        {"enfermedad": "dengue", "mes": 3, "casos": 12},
        {"enfermedad": "dengue", "mes": 4, "casos": 9},
        {"enfermedad": "dengue", "mes": 5, "casos": 14},
        {"enfermedad": "dengue", "mes": 6, "casos": 22},
        {"enfermedad": "dengue", "mes": 7, "casos": 35},
        {"enfermedad": "dengue", "mes": 8, "casos": 48},
        {"enfermedad": "dengue", "mes": 9, "casos": 64},
        {"enfermedad": "dengue", "mes": 10, "casos": 42},
        {"enfermedad": "dengue", "mes": 11, "casos": 19},
    ],
    2025: [
        {"enfermedad": "dengue", "mes": 9, "casos": 14},
        {"enfermedad": "dengue", "mes": 10, "casos": 9},
        {"enfermedad": "dengue", "mes": 12, "casos": 2},
    ],
    2024: [
        {"enfermedad": "dengue", "mes": 1, "casos": 85},
        {"enfermedad": "dengue", "mes": 2, "casos": 92},
        {"enfermedad": "dengue", "mes": 3, "casos": 110},
        {"enfermedad": "dengue", "mes": 4, "casos": 74},
        {"enfermedad": "dengue", "mes": 5, "casos": 98},
        {"enfermedad": "dengue", "mes": 6, "casos": 142},
        {"enfermedad": "dengue", "mes": 7, "casos": 180},
        {"enfermedad": "dengue", "mes": 8, "casos": 220},
        {"enfermedad": "dengue", "mes": 9, "casos": 195},
        {"enfermedad": "dengue", "mes": 10, "casos": 118},
        {"enfermedad": "dengue", "mes": 11, "casos": 50},
        {"enfermedad": "dengue", "mes": 12, "casos": 20},
    ],
}

# Climate by Year and Month
DEFAULT_CLIMA_POR_MES = {
    2026: [
        {"mes": 9, "temperatura": 29.5, "humedad": 72.0, "precipitacion": 180.4},
        {"mes": 10, "temperatura": 28.1, "humedad": 68.5, "precipitacion": 110.2},
        {"mes": 11, "temperatura": 26.3, "humedad": 62.0, "precipitacion": 45.0},
    ],
    2025: [
        {"mes": 9, "temperatura": 29.0, "humedad": 70.0, "precipitacion": 175.0},
        {"mes": 10, "temperatura": 27.5, "humedad": 65.0, "precipitacion": 95.0},
        {"mes": 12, "temperatura": 24.5, "humedad": 58.0, "precipitacion": 12.0},
    ],
    2024: [
        {"mes": 6, "temperatura": 28.5, "humedad": 75.0, "precipitacion": 150.0},
        {"mes": 7, "temperatura": 29.0, "humedad": 80.0, "precipitacion": 210.0},
        {"mes": 8, "temperatura": 29.2, "humedad": 82.0, "precipitacion": 235.0},
        {"mes": 9, "temperatura": 28.8, "humedad": 78.0, "precipitacion": 190.0},
        {"mes": 10, "temperatura": 27.2, "humedad": 70.0, "precipitacion": 80.0},
    ],
}

# Chronic Disease Indicators (SUIVE / DGE)
DEFAULT_CRONICAS = [
    {
        "indicador": "incidencia",
        "ambito": "estado",
        "municipio__clave_inegi": None,
        "region": "",
        "anio": 2025,
        "sexo": "total",
        "grupo_edad": "25-44",
        "institucion": "total",
        "valor": 249.28,
        "unidad": "tasa_100k",
        "fuente": "SUIVE/DGE Anuario de Morbilidad 2025 [SIMULADO]",
    },
    {
        "indicador": "mortalidad",
        "ambito": "estado",
        "municipio__clave_inegi": None,
        "region": "",
        "anio": 2025,
        "sexo": "total",
        "grupo_edad": "65 y +",
        "institucion": "SSA",
        "valor": 84.15,
        "unidad": "tasa_100k",
        "fuente": "SUIVE/DGE Anuario de Morbilidad 2025 [SIMULADO]",
    },
    {
        "indicador": "incidencia",
        "ambito": "municipio",
        "municipio__clave_inegi": "14067",
        "region": "Costa-Sierra Occidental",
        "anio": 2025,
        "sexo": "total",
        "grupo_edad": "45-49",
        "institucion": "total",
        "valor": 312.40,
        "unidad": "tasa_100k",
        "fuente": "SUIVE/DGE Anuario de Morbilidad 2025 [SIMULADO]",
    },
    {
        "indicador": "incidencia",
        "ambito": "municipio",
        "municipio__clave_inegi": "14022",
        "region": "Costa Sur",
        "anio": 2025,
        "sexo": "total",
        "grupo_edad": "45-49",
        "institucion": "total",
        "valor": 198.10,
        "unidad": "tasa_100k",
        "fuente": "SUIVE/DGE Anuario de Morbilidad 2025 [SIMULADO]",
    },
]

# Survey Statistics
DEFAULT_ENCUESTA = {
    "total": 12,
    "por_municipio": [
        {"municipio__clave_inegi": "14022", "municipio__nombre": "Cihuatlán [SIMULADO]", "respuestas": 7},
        {"municipio__clave_inegi": "14067", "municipio__nombre": "Puerto Vallarta [SIMULADO]", "respuestas": 5},
    ],
}

# Epidemiological Alerts
DEFAULT_ALERTAS = [
    {
        "id": 1,
        "enfermedad": "dengue",
        "enfermedad_nombre": "Dengue [SIMULADO]",
        "anio": 2026,
        "mes": 11,
        "casos_estimados": 19.0,
        "casos_anio_anterior": 12,
        "motivo": "[SIMULADO] Se estiman 19 casos de Dengue en la región costera para noviembre 2026, contra 12 en noviembre 2025.",
        "mensaje_publico": "[SIMULADO] Alerta sanitaria emitida por la Secretaría de Salud Jalisco ante incremento de casos.",
        "estado": "confirmada",
        "revisada_por": "Daniel Ramos [SIMULADO]",
        "revisada_en": "2026-11-01T10:00:00-06:00",
        "creada_en": "2026-10-31T08:00:00-06:00",
    },
    {
        "id": 2,
        "enfermedad": "dengue",
        "enfermedad_nombre": "Dengue [SIMULADO]",
        "anio": 2026,
        "mes": 10,
        "casos_estimados": 8.0,
        "casos_anio_anterior": 9,
        "motivo": "[SIMULADO] Se estiman 8 casos de Dengue para octubre 2026, cifra menor a los 9 registrados en octubre 2025.",
        "mensaje_publico": "",
        "estado": "descartada",
        "revisada_por": "Daniel Ramos [SIMULADO]",
        "revisada_en": "2026-10-02T12:00:00-06:00",
        "creada_en": "2026-10-01T08:00:00-06:00",
    },
    {
        "id": 3,
        "enfermedad": "dengue",
        "enfermedad_nombre": "Dengue [SIMULADO]",
        "anio": 2026,
        "mes": 12,
        "casos_estimados": 4.46,
        "casos_anio_anterior": 2,
        "motivo": "[SIMULADO] Se estiman 4.46 casos de Dengue en la región costera para diciembre 2026, contra 2 en diciembre 2025.",
        "mensaje_publico": "",
        "estado": "pendiente",
        "revisada_por": None,
        "revisada_en": None,
        "creada_en": "2026-11-13T08:15:00-06:00",
    },
]

# Content / Articles
DEFAULT_CONTENIDO = [
    {
        "id": 1,
        "tipo": "prevencion",
        "enfermedad": "dengue",
        "titulo": "[SIMULADO] Medidas clave contra el mosquito Aedes aegypti",
        "cuerpo": "[SIMULADO] Lava, tapa, voltea y tira todos los recipientes que puedan acumular agua en patios y azoteas.",
        "url_fuente": "https://salud.jalisco.gob.mx",
        "imagen_url": "",
        "publicado": True,
        "autor": "Daniel Ramos [SIMULADO]",
        "fecha": "2026-11-01T10:00:00Z",
    },
    {
        "id": 2,
        "tipo": "articulo",
        "enfermedad": "dengue",
        "titulo": "[SIMULADO] Balance epidemiológico en la región costera de Jalisco",
        "cuerpo": "[SIMULADO] Informe descriptivo del comportamiento del dengue en los 14 municipios de las regiones Costa Sur y Costa-Sierra Occidental.",
        "url_fuente": "",
        "imagen_url": "",
        "publicado": True,
        "autor": "Daniel Ramos [SIMULADO]",
        "fecha": "2026-11-10T12:00:00Z",
    },
    {
        "id": 3,
        "tipo": "nota",
        "enfermedad": "dengue",
        "titulo": "[SIMULADO] Borrador: Medidas para la temporada seca",
        "cuerpo": "[SIMULADO] Recomendaciones para almacenamiento seguro de agua de uso doméstico.",
        "url_fuente": "",
        "imagen_url": "",
        "publicado": False,
        "autor": "Daniel Ramos [SIMULADO]",
        "fecha": "2026-11-12T16:00:00Z",
    },
]


class MockDatabase:
    """In-memory database with state reset for reliable automated testing."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.users = copy.deepcopy(DEFAULT_USERS)
        self.municipios = copy.deepcopy(DEFAULT_MUNICIPIOS)
        self.enfermedades = copy.deepcopy(DEFAULT_ENFERMEDADES)
        self.prediccion = copy.deepcopy(DEFAULT_PREDICCION)
        self.casos_por_mes = copy.deepcopy(DEFAULT_CASOS_POR_MES)
        self.clima_por_mes = copy.deepcopy(DEFAULT_CLIMA_POR_MES)
        self.cronicas = copy.deepcopy(DEFAULT_CRONICAS)
        self.encuesta = copy.deepcopy(DEFAULT_ENCUESTA)
        self.alertas = copy.deepcopy(DEFAULT_ALERTAS)
        self.contenido = copy.deepcopy(DEFAULT_CONTENIDO)
        self._next_alerta_id = max(a["id"] for a in self.alertas) + 1 if self.alertas else 1
        self._next_contenido_id = max(c["id"] for c in self.contenido) + 1 if self.contenido else 1

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users.get(email.strip().lower())

    def get_user_by_token(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        email = payload.get("email", "").strip().lower()
        return self.users.get(email)

    def next_alerta_id(self) -> int:
        current = self._next_alerta_id
        self._next_alerta_id += 1
        return current

    def next_contenido_id(self) -> int:
        current = self._next_contenido_id
        self._next_contenido_id += 1
        return current


# Global singleton instance for in-memory operations
db = MockDatabase()
