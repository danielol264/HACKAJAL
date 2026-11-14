"""Sprint 2 - Pruebas del modelo (tarjeta 'Probar API y modelo', parte del modelo).
Uso: python pruebas_modelo.py <dengue_clima_semanal.csv> <modelo.joblib> <reporte.csv>"""
import sys, os, copy, traceback
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codigo"))  # nucleo.py y predecir.py
import numpy as np, pandas as pd
from nucleo import *
from predecir import *

ruta, modelo, reporte = sys.argv[1], sys.argv[2], sys.argv[3]
D = cargar(ruta); P = cargar_modelo(modelo)
resultados = []

def caso(id_, tipo, descripcion, esperado):
    def deco(f):
        try:
            detalle = f(); ok = True
        except AssertionError as e:
            ok, detalle = False, f"FALLA: {e}"
        except Exception as e:
            ok, detalle = False, f"ERROR NO CONTROLADO: {type(e).__name__}: {e}"
        resultados.append(dict(id=id_, tipo=tipo, caso=descripcion, esperado=esperado, resultado="OK" if ok else "FALLA", detalle=detalle if not ok else (detalle or "")))
        return f
    return deco

def lanza(excs, f):
    try: f()
    except excs as e: return f"{type(e).__name__}: {e}"
    raise AssertionError("no lanzó el error esperado")

@caso("C01", "correcto", "Municipio por nombre: Puerto Vallarta", "4 filas, semanas 1-4, casos>=0, nivel válido")
def _():
    r = predecir_municipio("Puerto Vallarta", D, P)
    assert len(r) == 4 and (r.casos_esperados >= 0).all() and r.nivel_riesgo.isin(["bajo", "medio", "alto"]).all()
    assert r.fecha_inicio_semana.is_monotonic_increasing

@caso("C02", "correcto", "Municipio por clave '067' y '67'", "Misma respuesta que por nombre")
def _():
    a, b, c = predecir_municipio("067", D, P), predecir_municipio("67", D, P), predecir_municipio("Puerto Vallarta", D, P)
    assert a.equals(b) and a.equals(c)

@caso("C03", "correcto", "Nombre sin acentos y en minúsculas: 'cihuatlan', ' TOMATLAN '", "Se reconoce el municipio")
def _():
    assert predecir_municipio("cihuatlan", D, P).municipio.iloc[0] == "Cihuatlán"
    assert predecir_municipio(" TOMATLAN ", D, P).municipio.iloc[0] == "Tomatlán"

@caso("C04", "correcto", "Los 125 municipios y 4 horizontes sin vacíos ni negativos", "500 filas sin NaN")
def _():
    r = predecir(D, P); assert len(r) == 500 and r.casos_esperados.notna().all() and (r.casos_esperados >= 0).all()

@caso("C05", "correcto", "Región Costa = 14 municipios x 4 semanas", "56 filas")
def _():
    r = predecir(D, P); assert (r.region_costa == "SI").sum() == 56 and r[r.region_costa == "SI"].clave_municipio.nunique() == 14

@caso("C06", "correcto", "Formato igual al mock del sprint 1", "8 columnas del contrato")
def _():
    r = predecir(D, P)[COLUMNAS]; assert list(r.columns) == ["clave_municipio", "municipio", "fecha_inicio_semana", "semana_epi", "enfermedad", "casos_esperados", "nivel_riesgo", "tipo_registro"]
    assert r.clave_municipio.str.len().eq(3).all()

@caso("C07", "correcto", "Municipio sin casos históricos (Mixtlán) -> nivel bajo", "bajo en 4 semanas")
def _():
    assert (predecir_municipio("Mixtlán", D, P).nivel_riesgo == "bajo").all()

@caso("C08", "correcto", "Sensibilidad: brote simulado en Puerto Vallarta (150 casos por semana en las 3 semanas hasta la semana de origen)", "El nivel sube a medio/alto")
def _():
    X = D.copy(); fin = X[X.posible_rezago == "NO"].fecha.max()   # semana de origen: la última semana completa
    m = (X.municipio == "Puerto Vallarta") & (X.fecha >= fin - pd.Timedelta(weeks=2)) & (X.fecha <= fin)
    X.loc[m, "casos"] = 150
    r = predecir_municipio("Puerto Vallarta", X, P)
    assert (r.nivel_riesgo != "bajo").any(), f"niveles={list(r.nivel_riesgo)}, casos={list(r.casos_esperados)}"

@caso("C09", "correcto", "Villa Purificación por nombre y por clave real '068'", "Misma respuesta y pertenece a la Costa")
def _():
    a, b = predecir_municipio("Villa Purificación", D, P), predecir_municipio("068", D, P)
    assert a.equals(b) and (a.region_costa == "SI").all()

@caso("C10", "correcto", "La clave 107 es Tuxcueca (no Villa Purificación) y NO es de la Costa", "region_costa = NO")
def _():
    a = predecir_municipio("107", D, P)
    assert a.municipio.iloc[0] == "Tuxcueca" and (a.region_costa == "NO").all()

@caso("E01", "municipio inexistente", "'Narnia'", "Error claro (MunicipioNoEncontrado)")
def _(): return lanza(MunicipioNoEncontrado, lambda: predecir_municipio("Narnia", D, P))

@caso("E02", "municipio inexistente", "Clave 999 y '000'", "Error claro (MunicipioNoEncontrado)")
def _():
    lanza(MunicipioNoEncontrado, lambda: predecir_municipio("999", D, P)); lanza(MunicipioNoEncontrado, lambda: predecir_municipio("000", D, P))

@caso("E03", "municipio inexistente", "Municipio de otro estado: 'Monterrey'", "Error claro")
def _(): lanza(MunicipioNoEncontrado, lambda: predecir_municipio("Monterrey", D, P))

@caso("E04", "municipio inexistente", "Entrada con caracteres raros: \"Colotlán'; DROP TABLE--\" y '😀'", "Error claro, sin caerse")
def _():
    lanza(MunicipioNoEncontrado, lambda: predecir_municipio("Colotlán'; DROP TABLE--", D, P)); lanza(MunicipioNoEncontrado, lambda: predecir_municipio("😀", D, P))

@caso("E05", "municipio inexistente", "Municipio vacío / None / solo espacios", "ValueError claro")
def _():
    for q in ["", None, "   "]: lanza(ValueError, lambda: predecir_municipio(q, D, P))

@caso("V01", "datos vacíos", "DataFrame sin filas", "DatosVacios")
def _(): lanza(DatosVacios, lambda: predecir(D.iloc[0:0], P))

@caso("V02", "datos vacíos", "None en lugar de datos", "DatosVacios")
def _(): lanza(DatosVacios, lambda: predecir(None, P))

@caso("V03", "datos vacíos", "Casos vacíos (NaN) en todo el municipio Puerto Vallarta", "Error claro o predicción válida, nunca NaN")
def _():
    X = D.copy(); X.loc[X.municipio == "Puerto Vallarta", "casos"] = np.nan
    try: r = predecir_municipio("Puerto Vallarta", X, P)
    except DatosVacios as e: return f"Error controlado: {e}"
    assert r.casos_esperados.notna().all(), "devuelve NaN en casos_esperados sin avisar"

@caso("V04", "datos vacíos", "Sin columnas de clima (el modelo de la Costa no usa clima)", "Predicción válida, sin errores")
def _():
    X = D.drop(columns=["lluvia_mm", "temp_max_c", "temp_min_c"])
    r = predecir(X, P)
    assert len(r) == 500 and r.casos_esperados.notna().all(), "NaN o filas faltantes en las predicciones"

@caso("V05", "datos vacíos", "Solo 2 semanas de historial", "DatosVacios (historial insuficiente)")
def _():
    X = D[D.fecha <= D.fecha.min() + pd.Timedelta(weeks=1)]
    lanza(ValueError, lambda: predecir(X, P))

@caso("V06", "datos vacíos", "Faltan columnas (sin 'casos')", "Error claro (ValueError), no KeyError")
def _():
    lanza(ValueError, lambda: predecir(D.drop(columns=["casos"]), P))

df = pd.DataFrame(resultados); df.to_csv(reporte, index=False, encoding="utf-8-sig")
pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 90)
print(df[["id", "tipo", "resultado", "detalle"]].to_string(index=False)); print(df.resultado.value_counts())
