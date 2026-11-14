"""Construye las filas semanales por municipio (125 municipios de Jalisco) a partir de una base abierta de dengue
de la Dirección General de Epidemiología (un archivo por año) y las agrega al archivo "Dengue Clima Semanal.csv".

Criterio (el mismo de los años 2020 a 2025; se comprobó que reproduce los datos de 2025 exactamente):
  - Solo Jalisco (ENTIDAD_RES = 14), municipio de residencia (MUNICIPIO_RES).
  - casos        = registros con ESTATUS_CASO 1 (probable) o 2 (confirmado). El 3 es descartado y no se cuenta.
  - confirmados  = registros con ESTATUS_CASO 2.
  - defunciones  = registros con DEFUNCION = 1 entre los casos (probables y confirmados).
  - Semana       = semana epidemiológica (domingo a sábado) de FECHA_SIGN_SINTOMAS (inicio de síntomas).
  - Solo se incluyen semanas completas al momento del corte del archivo (que terminen a más tardar en FECHA_ACTUALIZACION).
  - posible_rezago = "SI" en las últimas 3 semanas incluidas: los casos se capturan con retraso y esas semanas pueden estar incompletas.
  - Los 125 municipios aparecen en todas las semanas (con 0 si no hubo casos).

Uso:
  python construir_datos_semanales.py <base_dengue_del_año.csv> <Dengue Clima Semanal.csv> <salida.csv>
      Agrega (o reemplaza) el año de la base en el archivo semanal y escribe <salida.csv>.
  python construir_datos_semanales.py <base.csv> <Dengue Clima Semanal.csv> --validar
      No escribe nada: reconstruye ese año y lo compara con lo que ya hay en el archivo semanal."""
import sys
import numpy as np, pandas as pd

TIPO = "REAL_DGE"
SEMANAS_REZAGO = 3

def inicio_semana1(anio):
    """Domingo con el que inicia la semana epidemiológica 1 (la semana que contiene el 4 de enero)."""
    e = pd.Timestamp(anio, 1, 4)
    return e - pd.Timedelta(days=(e.weekday() + 1) % 7)

def semanas_del_anio(anio, corte):
    s1 = inicio_semana1(anio)
    inicios = [s1 + pd.Timedelta(weeks=i) for i in range(53)]
    inicios = [d for d in inicios if d + pd.Timedelta(days=6) <= corte and d < inicio_semana1(anio + 1)]
    return pd.DataFrame({"fecha_inicio_semana": inicios, "semana_epi": range(1, len(inicios) + 1)})

def construir(raw, catalogo):
    """raw: base abierta del año. catalogo: DataFrame con clave_municipio, municipio, region_norte (125 filas)."""
    corte = pd.Timestamp(str(raw["FECHA_ACTUALIZACION"].dropna().iloc[0]))
    f = pd.to_datetime(raw["FECHA_SIGN_SINTOMAS"], errors="coerce")
    anio = int(f.dropna().dt.year.mode().iloc[0])
    r = raw[(raw.ENTIDAD_RES == 14) & raw.ESTATUS_CASO.isin([1, 2])].copy()
    f = pd.to_datetime(r["FECHA_SIGN_SINTOMAS"], errors="coerce")
    r["fecha_inicio_semana"] = (f - pd.to_timedelta((f.dt.weekday + 1) % 7, unit="D")).dt.normalize()
    r["clave_municipio"] = r["MUNICIPIO_RES"].astype("Int64").astype(str).str.zfill(3)
    r["confirmados"] = (r.ESTATUS_CASO == 2).astype(int)
    r["defunciones"] = (r.DEFUNCION == 1).astype(int)
    g = r.groupby(["clave_municipio", "fecha_inicio_semana"]).agg(
        casos=("ESTATUS_CASO", "size"), confirmados=("confirmados", "sum"), defunciones=("defunciones", "sum")).reset_index()
    semanas = semanas_del_anio(anio, corte)
    malla = catalogo.assign(_k=1).merge(semanas.assign(_k=1), on="_k").drop(columns="_k")
    t = malla.merge(g, on=["clave_municipio", "fecha_inicio_semana"], how="left")
    for c in ["casos", "confirmados", "defunciones"]:
        t[c] = t[c].fillna(0).astype(int)
    ultimas = sorted(semanas.fecha_inicio_semana)[-SEMANAS_REZAGO:]
    t["posible_rezago"] = np.where(t.fecha_inicio_semana.isin(ultimas), "SI", "NO")
    t["anio"] = anio
    t["fecha_corte_archivo"] = corte.date().isoformat()
    t["tipo_registro"] = TIPO
    t["fecha_inicio_semana"] = t.fecha_inicio_semana.dt.date.astype(str)
    sin_municipio = int((~r.clave_municipio.isin(catalogo.clave_municipio)).sum())
    return t, anio, corte, sin_municipio

COLUMNAS = ["anio", "semana_epi", "fecha_inicio_semana", "clave_municipio", "municipio", "region_norte", "casos",
            "confirmados", "defunciones", "posible_rezago", "fecha_corte_archivo", "tipo_registro",
            "lluvia_mm", "temp_max_c", "temp_min_c", "n_est_lluvia", "n_est_temp"]

if __name__ == "__main__":
    base, semanal = sys.argv[1], sys.argv[2]
    validar = "--validar" in sys.argv
    w = pd.read_csv(semanal, encoding="utf-8-sig", dtype={"clave_municipio": str})
    cat = w.drop_duplicates("clave_municipio")[["clave_municipio", "municipio", "region_norte"]]
    raw = pd.read_csv(base, encoding="latin-1", low_memory=False)
    nuevo, anio, corte, sin_muni = construir(raw, cat)
    print(f"Año {anio}, corte del archivo {corte.date()}: {nuevo.semana_epi.nunique()} semanas x {nuevo.clave_municipio.nunique()} municipios, "
          f"{int(nuevo.casos.sum()):,} casos, {int(nuevo.confirmados.sum()):,} confirmados, {int(nuevo.defunciones.sum())} defunciones.")
    if sin_muni:
        print(f"Aviso: {sin_muni} casos sin municipio válido de Jalisco (clave fuera de los 125) no se cuentan.")
    if validar:
        v = w[w.anio == anio].merge(nuevo, on=["clave_municipio", "fecha_inicio_semana"], suffixes=("", "_nuevo"), how="outer", indicator=True)
        print("Filas solo en un lado:", v["_merge"].value_counts().to_dict())
        ok = v[v["_merge"] == "both"]
        for c in ["casos", "confirmados", "defunciones", "semana_epi", "posible_rezago", "fecha_corte_archivo"]:
            print(f"  {c:20} diferencias: {int((ok[c] != ok[c + '_nuevo']).sum())}")
        sys.exit(0)
    previo = w[w.anio != anio]
    nuevo = nuevo.assign(**{c: np.nan for c in ["lluvia_mm", "temp_max_c", "temp_min_c", "n_est_lluvia", "n_est_temp"]})
    out = pd.concat([previo[COLUMNAS], nuevo[COLUMNAS]]).sort_values(["clave_municipio", "fecha_inicio_semana"])
    out.to_csv(sys.argv[3], index=False, encoding="utf-8-sig")
    print(f"Escrito {sys.argv[3]}: {len(out):,} filas, {out.fecha_inicio_semana.nunique()} semanas, de {out.fecha_inicio_semana.min()} a {out.fecha_inicio_semana.max()}.")
