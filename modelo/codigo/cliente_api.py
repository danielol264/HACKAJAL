"""Integración del modelo de dengue (región Costa) con la API del proyecto.

Flujo:
  1. El usuario inicia sesión (iniciar_sesion) -> token de Firebase (dura 1 hora).
  2. cargar_plantilla(): sube la plantilla mensual (.xlsx o .csv) para las estadísticas.
  3. El modelo predice con los datos semanales por municipio (archivo "Dengue Clima Semanal.csv").
  4. enviar_prediccion(): manda las 4 semanas; la API decide si genera alerta.

Las cuatro funciones de la API (iniciar_sesion, leer_plantilla, cargar_plantilla, enviar_prediccion)
son las que entregó el CTO. Lo que se agregó aquí es predecir_cuatro_semanas() y la línea de comandos.

Variables de entorno: API_URL, FIREBASE_API_KEY, USUARIO_EMAIL, USUARIO_PASSWORD
(opcional, solo para pruebas: FIREBASE_LOGIN_URL).

Uso (desde la carpeta del repositorio):
  python codigo/cliente_api.py --simular                       # no usa red: muestra lo que se enviaría
  python codigo/cliente_api.py --plantilla datos/plantilla_carga_mensual.xlsx   # con la API de verdad
"""
import argparse, json, os, sys
from collections import Counter
from datetime import date

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nucleo import cargar, REGION_COSTA          # noqa: E402
from predecir import cargar_modelo, predecir     # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.path.dirname(RAIZ), ".env"))  # el .env único de la raíz del proyecto
API = os.getenv("API_URL", "http://127.0.0.1:8000/api")
API_KEY = os.getenv("FIREBASE_API_KEY")
URL_LOGIN = os.getenv("FIREBASE_LOGIN_URL", "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword")


# ----------------------------- Funciones del CTO -----------------------------
def iniciar_sesion(email, password):
    """Devuelve el encabezado Authorization con el token de Firebase del usuario (dura 1 hora)."""
    r = requests.post(f"{URL_LOGIN}?key={API_KEY}",
                      json={"email": email, "password": password, "returnSecureToken": True}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['idToken']}"}


def leer_plantilla(ruta):
    """Lee la hoja Datos del .xlsx (o un .csv con las mismas columnas). Celdas vacías -> None."""
    if ruta.lower().endswith(".csv"):
        df = pd.read_csv(ruta)
    else:
        df = pd.read_excel(ruta, sheet_name="Datos")
    df = df.dropna(subset=["anio", "mes"])
    return df.astype(object).where(df.notna(), None)  # NaN no es JSON válido


def _registros(df):
    """Filas listas para enviar como JSON. Agregado a lo del CTO: si una columna entera tiene alguna celda vacía,
    pandas la lee como decimales (9.0) y algunas validaciones rechazan 9.0 donde piden un entero; aquí los
    valores enteros (anio, mes, casos_dengue) se envían como enteros y las celdas vacías como null."""
    limpias = []
    for fila in df.to_dict(orient="records"):
        nueva = {}
        for k, v in fila.items():
            if v is None or (isinstance(v, float) and v != v):
                v = None
            elif k in ("anio", "mes", "casos_dengue") and float(v).is_integer():
                v = int(v)
            nueva[k] = v
        limpias.append(nueva)
    return limpias


def cargar_plantilla(headers, df):
    """POST /cargas/ - guarda los datos del archivo. Si una fila falla, no se guarda nada."""
    r = requests.post(f"{API}/cargas/", json=_registros(df), headers=headers, timeout=60)
    if r.status_code != 201:
        print("Error al cargar:", r.status_code, r.json())   # llaves = índice de fila desde 0; en Excel es índice + 2
        try:
            for fila, errores in r.json().items():
                print(f"  Fila {int(fila) + 2} del Excel: {errores}")
        except (AttributeError, ValueError):
            pass
        r.raise_for_status()
    return r.json()


def enviar_prediccion(headers, enfermedad, anio, mes, semanas):
    """POST /predicciones/ - semanas = 4 valores del mes predicho."""
    datos = {"enfermedad": enfermedad, "anio": anio, "mes": mes, "semanas": [float(v) for v in semanas]}
    r = requests.post(f"{API}/predicciones/", json=datos, headers=headers, timeout=60)
    if r.status_code != 201:
        print("Error al enviar la predicción:", r.status_code, r.json())
        r.raise_for_status()
    return r.json()


# ----------------------------- Parte del modelo -----------------------------
def predecir_cuatro_semanas(ruta_datos, ruta_modelo, origen="ultima"):
    """Corre el modelo y suma los 14 municipios de la Costa, semana por semana.

    Devuelve (anio, mes, [casos_sem1, casos_sem2, casos_sem3, casos_sem4], tabla_por_municipio).
    El mes que se informa es el mes en el que caen la mayoría de las 4 semanas predichas.
    origen: "ultima" parte de la última semana con datos (aunque esté marcada como posible rezago de captura);
            "completa" parte de la última semana sin posible rezago (más segura, pero predice semanas más viejas).
    """
    datos = cargar(ruta_datos)
    pred = predecir(datos, cargar_modelo(ruta_modelo), datos.fecha.max() if origen == "ultima" else None)
    costa = pred[pred.region_costa == "SI"]
    if costa.empty:
        raise ValueError("El modelo no devolvió predicciones para la Costa.")
    por_semana = costa.groupby("fecha_inicio_semana")["casos_esperados"].sum().sort_index()
    if len(por_semana) != 4:
        raise ValueError(f"Se esperaban 4 semanas y salieron {len(por_semana)}.")
    fechas = pd.to_datetime(por_semana.index)
    # mes con más semanas; si empatan, el más reciente
    cuenta = Counter(zip(fechas.year, fechas.month))
    (anio, mes), _ = max(cuenta.items(), key=lambda kv: (kv[1], kv[0]))
    return int(anio), int(mes), [round(float(v), 2) for v in por_semana.values], costa


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default=os.path.join(RAIZ, "datos", "Dengue Clima Semanal.csv"),
                    help="Datos semanales por municipio (formato Dengue Clima Semanal.csv)")
    ap.add_argument("--modelo", default=os.path.join(RAIZ, "resultados", "modelo_dengue_final.joblib"))
    ap.add_argument("--plantilla", default=os.path.join(RAIZ, "datos", "plantilla_carga_mensual.xlsx"),
                    help="Plantilla mensual (.xlsx o .csv) que se guarda en las estadísticas")
    ap.add_argument("--sin-carga", action="store_true", help="No subir la plantilla (solo enviar la predicción)")
    ap.add_argument("--forzar", action="store_true",
                    help="Enviar aunque el mes predicho ya haya pasado (normalmente se detiene: crearía una alerta de un mes pasado)")
    ap.add_argument("--simular", action="store_true", help="No usa red: solo muestra lo que se enviaría")
    ap.add_argument("--enfermedad", default="dengue")
    ap.add_argument("--origen", choices=["ultima", "completa"], default="ultima",
                    help="Semana desde la que se predice: la última con datos (por omisión) o la última sin posible rezago")
    a = ap.parse_args()

    anio, mes, semanas, costa = predecir_cuatro_semanas(a.datos, a.modelo, a.origen)
    carga = {"enfermedad": a.enfermedad, "anio": anio, "mes": mes, "semanas": semanas}
    print(f"Predicción de la región Costa ({len(REGION_COSTA)} municipios), suma de casos esperados por semana:")
    for f, v in zip(sorted(costa.fecha_inicio_semana.unique()), semanas):
        print(f"  semana que inicia el {f}: {v} casos")
    print("Se enviará a /predicciones/:", json.dumps(carga, ensure_ascii=False))
    if a.simular:
        print("(Simulación: no se envió nada.)")
        return 0

    hoy = date.today()
    if (anio, mes) < (hoy.year, hoy.month) and not a.forzar:
        print(f"\nSE DETUVO: el mes predicho ({mes:02d}/{anio}) ya pasó y la API crearía una alerta de un mes pasado.")
        print("Los datos semanales llegan hasta diciembre de 2025. Agrega los datos más recientes (archivo de la Dirección General de")
        print("Epidemiología) o usa --forzar solo para pruebas.")
        return 3
    faltan = [n for n in ("FIREBASE_API_KEY", "USUARIO_EMAIL", "USUARIO_PASSWORD") if not os.getenv(n)]
    if faltan:
        print("Faltan variables de entorno:", ", ".join(faltan)); return 2
    try:
        return _enviar(a, carga, anio, mes, semanas)
    except requests.HTTPError as e:
        print(f"\nLa API respondió con error {e.response.status_code}. No se envió la predicción.")
        return 1
    except requests.ConnectionError:
        print(f"\nNo se pudo conectar a {API}. ¿Está encendida la API? Revisa API_URL.")
        return 1


def _enviar(a, carga, anio, mes, semanas):
    headers = iniciar_sesion(os.getenv("USUARIO_EMAIL"), os.getenv("USUARIO_PASSWORD"))
    if not a.sin_carga:
        df = leer_plantilla(a.plantilla)
        if df.empty:
            print("La plantilla no tiene filas con año y mes: no se sube nada a /cargas/.")
        else:
            print("Carga:", cargar_plantilla(headers, df))
    print("Respuesta de la API:", enviar_prediccion(headers, a.enfermedad, anio, mes, semanas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
