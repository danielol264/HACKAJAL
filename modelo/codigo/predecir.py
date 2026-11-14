"""Sprint 2 - Predicciones por municipio y reglas de alerta.
Uso: python predecir.py <dengue_clima_semanal.csv> <modelo.joblib> <carpeta_salida>
Formato de salida = mismo contrato que el mock del sprint 1, con tipo_registro = PREDICCION_MODELO."""
import sys, os, json, unicodedata
import numpy as np, pandas as pd, joblib
from nucleo import *

COLUMNAS = ["clave_municipio", "municipio", "fecha_inicio_semana", "semana_epi",
            "enfermedad", "casos_esperados", "nivel_riesgo", "tipo_registro"]

class MunicipioNoEncontrado(ValueError): pass
class DatosVacios(ValueError): pass

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    return " ".join(s.split())

def semana_epi(fecha):
    """Semana epidemiológica: la semana (domingo a sábado) se numera por su miércoles."""
    return int((pd.Timestamp(fecha) + pd.Timedelta(days=3)).isocalendar().week)

# ---------------- Reglas de alerta (propuesta para validar con el PO) ----------------
def calcular_umbrales(d):
    """Umbrales por municipio a partir de su propio historial semanal (sin semanas con rezago):
       MEDIO si casos esperados >= max(1, percentil 75)   |   ALTO si >= max(3, percentil 90, medio+1)"""
    h = d[d.posible_rezago == "NO"]
    p = h.groupby("clave_municipio")["casos"].quantile([0.75, 0.90]).unstack()
    u = pd.DataFrame(index=p.index)
    p = p.fillna(0)   # municipios sin ningún dato de casos: se usan los umbrales mínimos
    u["umbral_medio"] = np.maximum(1, np.ceil(p[0.75])).astype(int)
    u["umbral_alto"] = np.maximum.reduce([np.full(len(p), 3), np.ceil(p[0.90]), u["umbral_medio"] + 1]).astype(int)
    return u

def nivel(casos_esperados, umbral_medio, umbral_alto):
    c = np.round(casos_esperados)
    return np.where(c >= umbral_alto, "alto", np.where(c >= umbral_medio, "medio", "bajo"))

# ---------------- Predicción ----------------
def cargar_modelo(ruta):
    return joblib.load(ruta)

REQUERIDAS = ["clave_municipio", "municipio", "fecha", "casos", "anio", "posible_rezago"]

def validar_datos(d_crudo):
    if d_crudo is None or len(d_crudo) == 0:
        raise DatosVacios("No hay datos históricos para predecir.")
    faltan = [c for c in REQUERIDAS if c not in d_crudo.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en los datos: {faltan}")
    if d_crudo["fecha"].nunique() < 13:
        raise DatosVacios("Historial insuficiente: se necesitan al menos 13 semanas de datos.")

def preparar(d_crudo):
    validar_datos(d_crudo)
    return variables_base(d_crudo.sort_values(["clave_municipio", "fecha"]))

def predecir(d_crudo, paquete, origen=None):
    """Predice h=1..4 semanas para TODOS los municipios desde la semana-origen
       (por omisión, la última semana sin rezago de captura)."""
    d = preparar(d_crudo)
    vs = paquete["vars"]
    if origen is None:
        origen = d[d.posible_rezago == "NO"].fecha.max()
    base = d[d.fecha == pd.Timestamp(origen)].dropna(subset=vs)
    if base.empty:
        raise DatosVacios(f"No hay datos completos en la semana de origen {pd.Timestamp(origen).date()}.")
    u = calcular_umbrales(d_crudo)
    salida = []
    for h, m in paquete["horizontes"].items():
        p = np.expm1(np.clip(m.predict(base[vs]) + base["casos_lag0"], 0, None))
        f = pd.Timestamp(origen) + pd.Timedelta(weeks=h)
        t = pd.DataFrame({"clave_municipio": base.clave_municipio.values, "municipio": base.municipio.values,
                          "fecha_inicio_semana": f.date().isoformat(), "semana_epi": semana_epi(f),
                          "enfermedad": "dengue", "casos_esperados": np.round(p, 1)})
        t = t.join(u, on="clave_municipio")
        t["nivel_riesgo"] = nivel(t.casos_esperados, t.umbral_medio, t.umbral_alto)
        t["tipo_registro"] = "PREDICCION_MODELO"
        salida.append(t)
    r = pd.concat(salida).sort_values(["clave_municipio", "fecha_inicio_semana"]).reset_index(drop=True)
    r["region_costa"] = np.where(r.clave_municipio.isin(REGION_COSTA), "SI", "NO")
    return r

def buscar_municipio(consulta, catalogo):
    """catalogo: DataFrame con clave_municipio y municipio. Acepta nombre (sin importar acentos/mayúsculas) o clave ('25' o '025')."""
    if consulta is None or str(consulta).strip() == "":
        raise ValueError("Debes indicar un municipio (nombre o clave).")
    q = str(consulta).strip()
    if q.isdigit():
        clave = q.zfill(3)
        hit = catalogo[catalogo.clave_municipio == clave]
    else:
        hit = catalogo[catalogo.municipio.map(_norm) == _norm(q)]
    if hit.empty:
        raise MunicipioNoEncontrado(f"El municipio '{consulta}' no existe en el catálogo de Jalisco (125 municipios).")
    return hit.iloc[0].clave_municipio

def predecir_municipio(consulta, d_crudo, paquete, origen=None):
    validar_datos(d_crudo)
    cat = d_crudo.drop_duplicates("clave_municipio")[["clave_municipio", "municipio"]]
    clave = buscar_municipio(consulta, cat)
    pred = predecir(d_crudo, paquete, origen)
    r = pred[pred.clave_municipio == clave].reset_index(drop=True)
    if r.empty:
        raise DatosVacios(f"No hay datos de casos suficientes para el municipio '{consulta}' en la semana de origen.")
    return r

if __name__ == "__main__":
    ruta, modelo, salida = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(salida, exist_ok=True)
    d = cargar(ruta); paq = cargar_modelo(modelo)
    # Por omisión se parte de la última semana completa (sin posible rezago). Con --origen-ultima se parte de la última
    # semana con datos, aunque sea de las marcadas como posible rezago (predice semanas más recientes; puede subestimar).
    origen = d.fecha.max() if "--origen-ultima" in sys.argv else None
    pred = predecir(d, paq, origen)
    u = calcular_umbrales(d)
    est = pred[COLUMNAS]
    costa = pred[pred.region_costa == "SI"][COLUMNAS]
    for nombre, t in [("predicciones_costa", costa), ("predicciones_estado", est)]:
        t.to_csv(os.path.join(salida, nombre + ".csv"), index=False, encoding="utf-8-sig")
    meta = {"tipo_registro": "PREDICCION_MODELO",
            "descripcion": "Predicción del modelo de dengue (Gradient Boosting, 1 a 4 semanas). Orienta, no diagnostica.",
            "ultima_semana_con_datos": paq["ultima_semana_datos"],
            "semana_origen_prediccion": str(pd.Timestamp(origen).date()) if origen is not None else paq["ultima_semana_sin_rezago"],
            "region": "Costa (14 municipios: Costa-Sierra Occidental + Costa Sur)",
            "predicciones": json.loads(costa.to_json(orient="records", force_ascii=False))}
    json.dump(meta, open(os.path.join(salida, "predicciones_costa.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    u2 = u.join(d.drop_duplicates("clave_municipio").set_index("clave_municipio")[["municipio", "region_costa"]])
    u2.reset_index()[["clave_municipio", "municipio", "region_costa", "umbral_medio", "umbral_alto"]].to_csv(
        os.path.join(salida, "umbrales_alerta.csv"), index=False, encoding="utf-8-sig")
    print(costa.to_string(index=False)); print(pred.groupby("nivel_riesgo").size())
    print(u2[u2.region_costa == "SI"])
    print(u2.sort_values("umbral_alto").tail(5))
