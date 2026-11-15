"""Llena la plantilla mensual de la API con los datos semanales del modelo (región Costa).

Suma los casos de los 14 municipios de la Costa por mes y promedia el clima, para que /cargas/ tenga datos reales
(estadísticas y comparación contra el mismo mes del año anterior al generar alertas).

Uso (desde la carpeta modelo):
  python codigo/generar_plantilla_mensual.py
  python codigo/generar_plantilla_mensual.py "datos/Dengue Clima Semanal.csv" datos/plantilla_carga_mensual.xlsx
"""
import os
import sys

import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nucleo import REGION_COSTA  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mensual_costa(ruta_datos):
    d = pd.read_csv(ruta_datos, dtype={"clave_municipio": str})
    d = d[d.clave_municipio.isin(REGION_COSTA)].copy()
    fecha = pd.to_datetime(d.fecha_inicio_semana)
    d["anio"], d["mes"] = fecha.dt.year, fecha.dt.month  # la semana cuenta en el mes en que inicia
    d["temp_media"] = (d.temp_max_c + d.temp_min_c) / 2
    # el clima es el mismo para todos los municipios de una semana: se toma una vez por semana
    semanas = d.drop_duplicates("fecha_inicio_semana").groupby(["anio", "mes"])
    clima = pd.DataFrame({
        "temperatura_c": semanas["temp_media"].mean(),
        "precipitacion_mm": semanas["lluvia_mm"].sum(min_count=1),  # sin datos de lluvia = vacío, no 0
    })
    casos = d.groupby(["anio", "mes"])["casos"].sum().rename("casos_dengue")
    m = pd.concat([casos, clima], axis=1).reset_index()
    m["humedad_pct"] = None  # no viene en los datos
    m["temperatura_c"] = m.temperatura_c.round(1)
    m["precipitacion_mm"] = m.precipitacion_mm.round(1)
    return m[["anio", "mes", "casos_dengue", "temperatura_c", "humedad_pct", "precipitacion_mm"]]


def escribir_plantilla(m, ruta_plantilla):
    wb = load_workbook(ruta_plantilla)
    ws = wb["Datos"]
    for fila in ws.iter_rows(min_row=2):  # limpia lo anterior
        for celda in fila:
            celda.value = None
    for i, fila in enumerate(m.itertuples(index=False), start=2):
        for j, valor in enumerate(fila, start=1):
            ws.cell(i, j, None if pd.isna(valor) else (int(valor) if j <= 3 else float(valor)))
    wb.save(ruta_plantilla)


if __name__ == "__main__":
    datos = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "datos", "Dengue Clima Semanal.csv")
    plantilla = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "datos", "plantilla_carga_mensual.xlsx")
    m = mensual_costa(datos)
    assert m.duplicated(["anio", "mes"]).sum() == 0 and m.mes.between(1, 12).all() and (m.casos_dengue >= 0).all()
    escribir_plantilla(m, plantilla)
    print(f"Plantilla llena: {len(m)} meses ({m.anio.min()}-{m.mes.iloc[0]:02d} a {m.anio.max()}-{m.mes.iloc[-1]:02d}) -> {plantilla}")
