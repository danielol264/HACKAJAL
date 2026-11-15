"""Ejecuta los scripts del modelo de P4 (carpeta modelo/) en un proceso aparte.

Todo el proyecto usa un solo entorno virtual (requirements.txt de la raíz), así que se usa el mismo Python
que corre la app. Cada script responde con una sola línea JSON.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]  # .../HackaJal
CARPETA_MODELO = RAIZ_PROYECTO / "modelo"
DATOS_ORIGINALES = CARPETA_MODELO / "datos" / "Dengue Clima Semanal.csv"
# copia del último archivo semanal cargado desde "Carga de datos": es el que usa el modelo
DATOS_CARGADOS = CARPETA_MODELO / "datos" / "datos_semanales_cargados.csv"
COLUMNAS_SEMANALES = {"fecha_inicio_semana", "clave_municipio"}


def datos_del_modelo() -> Path:
    """El último archivo cargado en la app; si nunca se ha cargado uno, el original de P4."""
    return DATOS_CARGADOS if DATOS_CARGADOS.exists() else DATOS_ORIGINALES


def es_archivo_semanal(ruta: Path) -> bool:
    if ruta.suffix.lower() != ".csv":
        return False
    with ruta.open(encoding="utf-8-sig", errors="replace") as archivo:
        encabezado = {c.strip().lower() for c in archivo.readline().split(",")}
    return COLUMNAS_SEMANALES <= encabezado


def python_del_modelo() -> Path:
    """El mismo Python de la app; MODELO_PYTHON permite usar otro entorno si hiciera falta."""
    return Path(os.getenv("MODELO_PYTHON") or sys.executable)


def correr_script(script: str, *args: str) -> dict[str, Any]:
    """Corre modelo/codigo/<script> y devuelve su JSON. Lanza RuntimeError con un mensaje para el usuario."""
    python = python_del_modelo()
    if not python.exists():
        raise RuntimeError(
            f"No se encontró Python en {python}. Revisa la variable MODELO_PYTHON del .env."
        )
    try:
        proceso = subprocess.run(
            [str(python), str(CARPETA_MODELO / "codigo" / script), *args],
            cwd=CARPETA_MODELO, capture_output=True, text=True, encoding="utf-8", timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # sin ventana negra en Windows
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("El modelo tardó más de 5 minutos y se detuvo.") from None
    lineas = [linea for linea in proceso.stdout.splitlines() if linea.strip().startswith("{")]
    if not lineas:
        raise RuntimeError(f"El modelo no respondió.\n{(proceso.stderr or proceso.stdout).strip()[-600:]}")
    resultado = json.loads(lineas[-1])
    if "error" in resultado:
        mensaje = resultado["error"]
        if "ModuleNotFoundError" in mensaje:
            mensaje += "\nInstala las dependencias desde la raíz del proyecto: pip install -r requirements.txt"
        raise RuntimeError(mensaje)
    return resultado


def predecir(ruta_datos: Path) -> dict[str, Any]:
    """{"anio", "mes", "semanas": [4 valores], "semanas_inicio": [4 fechas]}"""
    return correr_script("predecir_json.py", "--datos", str(ruta_datos))


def resumen_mensual(ruta_datos: Path) -> list[dict[str, Any]]:
    """Filas mensuales de la Costa con el formato de la plantilla (anio, mes, casos_dengue, temperatura_c, ...)."""
    return correr_script("mensual_json.py", str(ruta_datos))["filas"]
