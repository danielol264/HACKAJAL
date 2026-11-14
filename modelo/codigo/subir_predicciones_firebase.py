"""Sprint 2 - Sube las predicciones y los umbrales de alerta de la Costa a Firebase (Cloud Firestore).
IMPORTANTE: este script NO se ha probado contra un Firebase real (no tenemos las llaves). Sí se probó el modo --simular.
Las llaves de Firebase NUNCA se suben a GitHub ni a Drive: se pasan como ruta en --credenciales o en la variable
de entorno GOOGLE_APPLICATION_CREDENTIALS.

Uso:
  python subir_predicciones_firebase.py resultados --simular                      (solo muestra qué se escribiría)
  python subir_predicciones_firebase.py resultados --credenciales C:\\ruta\\llave.json   (escribe de verdad)

Estructura que crea (una colección por tema; el id del documento evita duplicados al volver a correrlo):
  predicciones/{clave}_{fecha_inicio_semana}_dengue   -> clave_municipio, municipio, fecha_inicio_semana, semana_epi,
                                                          enfermedad, casos_esperados, nivel_riesgo, tipo_registro, region
  umbrales_alerta/{clave}                             -> clave_municipio, municipio, umbral_medio, umbral_alto"""
import argparse, csv, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("carpeta", help="Carpeta 'resultados' con predicciones_costa.json y umbrales_alerta.csv")
ap.add_argument("--simular", action="store_true", help="No escribe nada, solo muestra lo que escribiría")
ap.add_argument("--credenciales", default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"), help="Ruta a la llave JSON de Firebase")
args = ap.parse_args()

with open(os.path.join(args.carpeta, "predicciones_costa.json"), encoding="utf-8") as f:
    paquete = json.load(f)
docs = []
for p in paquete["predicciones"]:
    doc_id = f"{p['clave_municipio']}_{p['fecha_inicio_semana']}_{p['enfermedad']}"
    docs.append(("predicciones", doc_id, {**p, "region": "Costa"}))
with open(os.path.join(args.carpeta, "umbrales_alerta.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["region_costa"] == "SI":
            docs.append(("umbrales_alerta", r["clave_municipio"], {"clave_municipio": r["clave_municipio"], "municipio": r["municipio"],
                         "umbral_medio": int(r["umbral_medio"]), "umbral_alto": int(r["umbral_alto"])}))

print(f"Documentos a escribir: {len(docs)} ({sum(c == 'predicciones' for c, _, _ in docs)} predicciones, "
      f"{sum(c == 'umbrales_alerta' for c, _, _ in docs)} umbrales)")
if args.simular or not args.credenciales:
    for c, i, d in docs[:3] + docs[-2:]:
        print(f"  {c}/{i} -> {json.dumps(d, ensure_ascii=False)}")
    print("MODO SIMULACIÓN: no se escribió nada." if args.simular else
          "Falta --credenciales (o GOOGLE_APPLICATION_CREDENTIALS): no se escribió nada.")
    sys.exit(0)

import firebase_admin                                  # pip install firebase-admin
from firebase_admin import credentials, firestore
firebase_admin.initialize_app(credentials.Certificate(args.credenciales))
db = firestore.client()
lote = db.batch()
for n, (coleccion, doc_id, datos) in enumerate(docs, 1):
    lote.set(db.collection(coleccion).document(doc_id), datos)
    if n % 400 == 0:                                   # Firestore permite máximo 500 escrituras por lote
        lote.commit(); lote = db.batch()
lote.commit()
print("Listo: documentos escritos en Firebase.")
