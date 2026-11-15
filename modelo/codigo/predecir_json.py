"""Corre el modelo y escribe en pantalla SOLO un JSON con la predicción (lo usa la app de escritorio).

No inicia sesión ni envía nada: la app manda el resultado a la API con la sesión del usuario.

Uso (desde la carpeta modelo):
  python codigo/predecir_json.py
  python codigo/predecir_json.py --datos "otra/ruta.csv"

Salida correcta (código 0):  {"anio": 2026, "mes": 11, "semanas": [..4..], "semanas_inicio": [...]}
Salida con error (código 1): {"error": "texto"}
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=os.path.join(RAIZ, "datos", "Dengue Clima Semanal.csv"))
    ap.add_argument("--modelo", default=os.path.join(RAIZ, "resultados", "modelo_dengue_final.joblib"))
    a = ap.parse_args()
    try:
        from cliente_api import predecir_cuatro_semanas  # noqa: E402 (importa pandas/sklearn: puede tardar)
        anio, mes, semanas, costa = predecir_cuatro_semanas(a.datos, a.modelo)
        inicios = sorted(str(f)[:10] for f in costa.fecha_inicio_semana.unique())
        print(json.dumps({"anio": anio, "mes": mes, "semanas": semanas, "semanas_inicio": inicios}, ensure_ascii=False))
        return 0
    except Exception as error:  # noqa: BLE001 — la app muestra el texto tal cual
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
