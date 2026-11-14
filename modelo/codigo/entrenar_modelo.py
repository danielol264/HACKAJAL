"""Sprint 2 - Entrenamiento y comparación de modelos de dengue para la región COSTA de Jalisco
(horizontes de 1 a 4 semanas).
Uso: python entrenar_modelo.py <ruta_dengue_clima_semanal.csv> <carpeta_salida>

Región Costa = 14 municipios (Costa-Sierra Occidental + Costa Sur), definidos en nucleo.py.
Se comparan tres cosas, con las mismas semanas de examen (sin semanas con retraso de captura):
  persistencia -> NO es un modelo: copia los casos de esa semana hacia el futuro (referencia a superar)
  base         -> Gradient Boosting entrenado con los 125 municipios de Jalisco (es el modelo FINAL)
  solo_costa   -> el mismo modelo, pero entrenado solo con los 14 municipios de la Costa
El examen se mide SOLO en los municipios de la Costa.
No se usa clima: la serie de clima que tenemos es de estaciones del Norte y no representa a la Costa.
Brigadas NO se incluyen: no existe historial real (solo 10 registros simulados)."""
import sys, os, joblib
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from nucleo import *

ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_DATOS
salida = sys.argv[2] if len(sys.argv) > 2 else "salida"
os.makedirs(salida, exist_ok=True)
N_MUNICIPIOS = len(REGION_COSTA)

d = variables_base(cargar(ruta)).dropna(subset=VARS_BASE)
PARAMS = dict(loss="squared_error", max_iter=200, learning_rate=0.05, max_depth=4,
              min_samples_leaf=40, l2_regularization=1.0, random_state=0)

def entrena(tr, vs=VARS_BASE):
    # Se modela el CAMBIO respecto a los casos de la última semana: log(1+y) - log(1+casos_lag0).
    # Así el modelo no depende de la escala histórica y puede reaccionar a un brote más grande que los vistos.
    return HistGradientBoostingRegressor(**PARAMS).fit(tr[vs], np.log1p(tr.y) - tr["casos_lag0"])

def predice(m, x, vs=VARS_BASE):
    return np.expm1(np.clip(m.predict(x[vs]) + x["casos_lag0"], 0, None))

PARTICIONES = {  # nombre: (último año de entrenamiento, año de prueba)
    "prueba_2023": (2022, 2023),
    "validacion_2024_brote": (2023, 2024),
    "prueba_2025": (2024, 2025),
    "prueba_2026": (2025, 2026),   # año en curso: solo semanas completas hasta la fecha de corte del archivo
}
filas = []
for h in HORIZONTES:
    t = armar_objetivo(d, h)
    for nombre, (a_tr, a_te) in PARTICIONES.items():
        tr, te = t[t.anio_obj <= a_tr], t[t.anio_obj == a_te]
        variantes = {"persistencia": np.expm1(te.casos_lag0).values,
                     "base": predice(entrena(tr), te)}
        m_costa = entrena(tr[tr.es_costa == 1])
        variantes["solo_costa"] = predice(m_costa, te)
        for modelo, p in variantes.items():
            for zona, mask in [("Costa", (te.es_costa == 1).values), ("Todo Jalisco", np.ones(len(te), bool))]:
                if modelo == "solo_costa" and zona != "Costa":
                    continue
                r = metricas(te.y.values[mask], p[mask])
                r.update(particion=nombre, horizonte_sem=h, modelo=modelo, zona=zona, n=int(mask.sum()))
                filas.append(r)
res = pd.DataFrame(filas)[["particion", "zona", "horizonte_sem", "modelo", "n", "MAE", "RMSE", "WAPE", "casos_reales", "casos_predichos"]]

# ---- Modelo final: entrenado con TODO el historial disponible (2020-2025) de los 125 municipios ----
paquete = {"horizontes": {}, "vars": VARS_BASE, "params": PARAMS, "region": "Costa",
           "municipios_costa": REGION_COSTA}
for h in HORIZONTES:
    paquete["horizontes"][h] = entrena(armar_objetivo(d, h))
paquete["ultima_semana_datos"] = str(d.fecha.max().date())
paquete["ultima_semana_sin_rezago"] = str(d[d.posible_rezago == "NO"].fecha.max().date())
joblib.dump(paquete, os.path.join(salida, "modelo_dengue_final.joblib"))

# ---- Impresión en tablas con rayitas, con nombres completos (una por examen y por tipo de error) ----
NOMBRES_MODELO = {"persistencia": "Comparación: copiar casos de esa semana",
                  "base": "Modelo entrenado con todo Jalisco (el elegido)",
                  "solo_costa": "Modelo entrenado solo con la Costa"}

def tabla_con_rayas(titulo, piv, nombres=NOMBRES_MODELO):
    """piv: filas = modelo, columnas = semanas adelante. El mejor (menor error) de cada columna lleva *."""
    cols = ["Modelo"] + [f"{h} semana" + ("" if h == 1 else "s") + " adelante" for h in piv.columns]
    celdas = []
    for modelo, fila in piv.iterrows():
        celdas.append([nombres[modelo]] + [f"{v:.2f}" + (" *" if v == piv[h].min() else "  ") for h, v in fila.items()])
    anchos = [max(len(str(x)) for x in col) for col in zip(cols, *celdas)]
    raya = "+" + "+".join("-" * (a + 2) for a in anchos) + "+"
    fmt = lambda f: "| " + " | ".join(str(x).ljust(a) for x, a in zip(f, anchos)) + " |"
    print("\n" + titulo); print(raya); print(fmt(cols)); print(raya)
    for f in celdas: print(fmt(f))
    print(raya)

def fecha_txt(f):
    return pd.Timestamp(f).strftime("%d/%m/%Y")

def semanas_validas(anio):   # semanas completas (sin retraso de captura) de un año
    return d[(d.anio == anio) & (d.posible_rezago == "NO")].fecha

TITULOS = {}
for nombre_p, (a_tr, a_te) in PARTICIONES.items():
    TITULOS[nombre_p] = (f"REGIÓN COSTA - EXAMEN CON DATOS DE {a_te}" + (", el año del brote" if a_te == 2024 else ", el año en curso (hasta el corte del archivo)" if a_te == d.anio.max() else "") +
                         f"\nSe compara lo que dijo el modelo con lo que realmente pasó entre el {fecha_txt(semanas_validas(a_te).min())} y el {fecha_txt(semanas_validas(a_te).max())}" +
                         f"\nEl modelo aprendió solo con datos hasta el {fecha_txt(semanas_validas(a_tr).max())}")
print("\nCÓMO LEER LAS TABLAS")
print(f"- Región Costa: {N_MUNICIPIOS} municipios (Costa-Sierra Occidental + Costa Sur). El examen se mide solo en ellos.")
print("- 'Comparación: copiar casos de esa semana' NO es un modelo: para adivinar, repite los casos que hubo la semana en que se hace la predicción.")
print("  Sirve para ver si el modelo se equivoca menos que algo tan simple.")
print("- Los números son el error: entre más chico, mejor. El * marca el mejor de cada columna.")

MEDIDAS = {"MAE": "ERROR PROMEDIO EN CASOS: cuántos casos se equivoca el modelo por municipio y semana",
           "WAPE": "ERROR COMPARADO CON LOS CASOS REALES: error total entre casos reales (0.50 = el error es la mitad de los casos que hubo)"}
costa = res[res.zona == "Costa"]
for part in PARTICIONES:
    a_te = PARTICIONES[part][1]
    for med, expl in MEDIDAS.items():
        piv = costa[costa.particion == part].pivot_table(index="modelo", columns="horizonte_sem", values=med)
        piv = piv.loc[["persistencia", "base", "solo_costa"]]
        nombres = dict(NOMBRES_MODELO)
        nombres["persistencia"] += f" (examen del {fecha_txt(semanas_validas(a_te).min())} al {fecha_txt(semanas_validas(a_te).max())})"
        ref = costa[(costa.particion == part) & (costa.modelo == "persistencia")].sort_values("horizonte_sem")
        n_pred, n_casos = int(ref.n.iloc[0]), int(ref.casos_reales.iloc[0])
        datos = (f"\nCasos que realmente hubo en esas semanas en la Costa (columna 'casos' del archivo): {n_casos:,}"
                 f"\nPredicciones evaluadas en cada columna: {n_pred:,} = {N_MUNICIPIOS} municipios x {n_pred // N_MUNICIPIOS} semanas")
        tabla_con_rayas(f"{TITULOS[part]}{datos}\n{expl}", piv, nombres)
print("\nÚltima semana con datos disponibles:", paquete["ultima_semana_datos"])
print("Última semana completa, sin retraso de captura (desde aquí se hacen las predicciones):", paquete["ultima_semana_sin_rezago"])

# ---- Archivo con todos los resultados, con nombres completos en columnas y modelos ----
completo = res.rename(columns={"particion": "examen", "zona": "zona", "horizonte_sem": "semanas_adelante",
                               "modelo": "modelo", "n": "cantidad_de_municipios_semana_evaluados",
                               "MAE": "error_promedio_en_casos",
                               "RMSE": "error_cuadratico_en_casos",
                               "WAPE": "error_comparado_con_casos_reales",
                               "casos_reales": "casos_reales", "casos_predichos": "casos_predichos_por_el_modelo"})
completo["modelo"] = completo["modelo"].map(NOMBRES_MODELO)
completo.round(4).to_csv(os.path.join(salida, "metricas_comparacion.csv"), index=False, encoding="utf-8-sig")
