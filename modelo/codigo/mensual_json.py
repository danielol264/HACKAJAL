"""Convierte el archivo semanal por municipio en los totales mensuales de la región Costa y los escribe como JSON.

Lo usa la app de escritorio en "Carga de datos": del mismo archivo salen las estadísticas mensuales (API /cargas/)
y los datos del modelo. Es el mismo cálculo de generar_plantilla_mensual.py, sin escribir el Excel.

Uso (desde la carpeta modelo):
  python codigo/mensual_json.py "datos/Dengue Clima Semanal.csv"

Salida correcta (código 0):  {"filas": [{"anio": 2026, "mes": 1, "casos_dengue": 47, "temperatura_c": null, ...}, ...]}
Salida con error (código 1): {"error": "texto"}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
COLUMNAS = {"fecha_inicio_semana", "clave_municipio", "casos", "temp_max_c", "temp_min_c", "lluvia_mm"}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Uso: python codigo/mensual_json.py <archivo semanal .csv>"}))
        return 1
    try:
        import pandas as pd
        from generar_plantilla_mensual import mensual_costa

        faltan = COLUMNAS - set(pd.read_csv(sys.argv[1], nrows=0, encoding="utf-8-sig").columns)
        if faltan:
            raise ValueError(f"Al archivo le faltan columnas: {', '.join(sorted(faltan))}. "
                             "Debe tener el formato semanal por municipio (como Dengue Clima Semanal.csv).")
        m = mensual_costa(sys.argv[1])
        if m.empty:
            raise ValueError("El archivo no tiene filas de los municipios de la Costa.")
        filas = [{k: (None if pd.isna(v) else (int(v) if k in ("anio", "mes", "casos_dengue") else float(v)))
                  for k, v in fila.items()} for fila in m.to_dict("records")]
        print(json.dumps({"filas": filas}, ensure_ascii=False))
        return 0
    except ValueError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1
    except Exception as error:  # noqa: BLE001 — la app muestra el texto tal cual
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
