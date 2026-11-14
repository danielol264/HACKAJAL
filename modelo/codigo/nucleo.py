"""Núcleo del modelo predictivo de dengue (región Costa de Jalisco).
Funciones compartidas: carga, construcción de variables, métricas."""
import numpy as np, pandas as pd

RUTA_DATOS = "Dengue Clima Semanal.csv"   # ruta por omisión (relativa); los scripts aceptan otra por argumento
HORIZONTES = [1, 2, 3, 4]

# Región Costa = Costa-Sierra Occidental (8 municipios) + Costa Sur (6), tal como la definió el equipo.
# Ojo: en la tabla del equipo Villa Purificación aparece con clave 107, pero en los datos la 107 es Tuxcueca;
# la clave real de Villa Purificación es 068, por eso aquí se usa 068.
REGION_COSTA = {"012": "Atenguillo", "020": "Cabo Corrientes", "038": "Guachinango", "058": "Mascota",
                "062": "Mixtlán", "067": "Puerto Vallarta", "080": "San Sebastián del Oeste", "084": "Talpa de Allende",
                "021": "Casimiro Castillo", "022": "Cihuatlán", "027": "Cuautitlán de García Barragán",
                "043": "La Huerta", "100": "Tomatlán", "068": "Villa Purificación"}

def cargar(ruta=RUTA_DATOS):
    d = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"clave_municipio": str})
    d["fecha"] = pd.to_datetime(d["fecha_inicio_semana"])
    d["region_costa"] = np.where(d["clave_municipio"].isin(REGION_COSTA), "SI", "NO")
    return d.sort_values(["clave_municipio", "fecha"]).reset_index(drop=True)

def variables_base(d):
    """Variables que usan solo casos pasados (modelo base)."""
    d = d.copy()
    g = d.groupby("clave_municipio")["casos"]
    for k in range(0, 4):
        d[f"casos_lag{k}"] = np.log1p(g.shift(k))
    for w in (4, 8, 12):
        d[f"casos_media{w}"] = np.log1p(g.transform(lambda s: s.rolling(w, min_periods=1).mean()))
    d["casos_52sem"] = np.log1p(g.transform(lambda s: s.rolling(52, min_periods=8).sum().shift(1)))
    est = d.groupby("fecha")["casos"].sum().rename("estado_casos")
    est4 = est.rolling(4, min_periods=1).mean().rename("estado_media4")
    d = d.join(np.log1p(est).rename("estado_lag0"), on="fecha").join(np.log1p(est4), on="fecha")
    d["es_costa"] = d["clave_municipio"].isin(REGION_COSTA).astype(int)
    costa = d[d.es_costa == 1].groupby("fecha")["casos"].sum()
    d = d.join(np.log1p(costa).rename("costa_lag0"), on="fecha")
    sem = d["fecha"].dt.isocalendar().week.astype(int)
    d["sem_sin"] = np.sin(2 * np.pi * sem / 52.18)
    d["sem_cos"] = np.cos(2 * np.pi * sem / 52.18)
    return d

VARS_BASE = ["casos_lag0", "casos_lag1", "casos_lag2", "casos_lag3", "casos_media4", "casos_media8",
             "casos_media12", "casos_52sem", "estado_lag0", "estado_media4", "costa_lag0", "es_costa",
             "sem_sin", "sem_cos"]

def variables_clima(d):
    """Agrega clima (serie única de estaciones del NORTE; NO sirve para la Costa, por eso el modelo de la Costa no lo usa)."""
    d = d.copy()
    clima = d.drop_duplicates("fecha").set_index("fecha")[["lluvia_mm", "temp_max_c", "temp_min_c"]].sort_index()
    clima = clima.interpolate(limit_direction="both")  # 2 semanas de lluvia y 3 de temperatura vacías
    f = pd.DataFrame(index=clima.index)
    f["lluvia_4s"] = clima.lluvia_mm.rolling(4, min_periods=1).sum()
    f["lluvia_8s"] = clima.lluvia_mm.rolling(8, min_periods=1).sum()
    f["lluvia_4s_rez4"] = f.lluvia_4s.shift(4)
    f["tmax_4s"] = clima.temp_max_c.rolling(4, min_periods=1).mean()
    f["tmin_4s"] = clima.temp_min_c.rolling(4, min_periods=1).mean()
    f["tmin_4s_rez4"] = f.tmin_4s.shift(4)
    f = f.bfill()
    return d.join(f, on="fecha")

VARS_CLIMA = ["lluvia_4s", "lluvia_8s", "lluvia_4s_rez4", "tmax_4s", "tmin_4s", "tmin_4s_rez4"]

def armar_objetivo(d, h):
    """Para cada semana-origen t, el objetivo es los casos en t+h (mismo municipio)."""
    d = d.copy()
    g = d.groupby("clave_municipio")
    d["y"] = g["casos"].shift(-h)
    d["anio_obj"] = g["anio"].shift(-h)
    d["rezago_obj"] = g["posible_rezago"].shift(-h)
    d["fecha_obj"] = g["fecha"].shift(-h)
    return d.dropna(subset=["y"]).query("rezago_obj == 'NO'")  # se excluyen semanas con rezago de captura

def metricas(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"MAE": float(np.mean(np.abs(y - p))),
            "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
            "WAPE": float(np.abs(y - p).sum() / max(y.sum(), 1)),
            "casos_reales": int(y.sum()), "casos_predichos": float(p.sum())}
