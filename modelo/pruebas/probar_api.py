"""Sprint 2 - Pruebas de la API (tarjeta 'Probar API y modelo', parte de la API).
Prueba los tres tipos de caso de la tarjeta: casos correctos, municipio inexistente y datos vacíos.
No necesita instalar nada (usa solo la biblioteca estándar de Python).

Uso (ejemplos; la ruta se ajusta a como la haya hecho el CTO, con {municipio} donde va el nombre o la clave):
  python probar_api.py --url http://127.0.0.1:8000 --ruta "/api/prediccion/{municipio}/"
  python probar_api.py --url http://127.0.0.1:8000 --ruta "/api/predicciones/?municipio={municipio}" --reporte reporte_api.csv

Qué se considera correcto:
  - Municipio válido (nombre o clave de la Costa)  -> código 200 y una respuesta JSON con contenido.
  - Municipio inexistente / entrada vacía o rara     -> código 400 o 404 con un mensaje claro. NUNCA 500 ni páginas de error técnico.
Cada falla debe convertirse en una tarjeta Bug en Trello (el programa imprime el texto sugerido)."""
import argparse, csv, json, sys, urllib.request, urllib.error, urllib.parse

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True, help="Dirección base de la API, por ejemplo http://127.0.0.1:8000")
ap.add_argument("--ruta", required=True, help="Ruta con {municipio}, por ejemplo /api/prediccion/{municipio}/")
ap.add_argument("--metodo", default="GET")
ap.add_argument("--reporte", default="reporte_api.csv")
ap.add_argument("--espera", type=float, default=15.0, help="Segundos máximos de espera por respuesta")
args = ap.parse_args()

def llamar(municipio):
    ruta = args.ruta.replace("{municipio}", urllib.parse.quote(str(municipio), safe=""))
    req = urllib.request.Request(args.url.rstrip("/") + ruta, method=args.metodo)
    try:
        with urllib.request.urlopen(req, timeout=args.espera) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def json_ok(txt):
    try:
        x = json.loads(txt); return x not in (None, [], {}, "")
    except Exception:
        return False

def parece_error_tecnico(txt):
    t = txt.lower()
    return any(p in t for p in ["traceback", "<!doctype html", "<html", "exception at", "keyerror", "attributeerror", "typeerror", "valueerror at"])

CASOS = [  # id, tipo, municipio, esperado ('ok' o 'rechazo'), descripción
    ("A01", "correcto", "Puerto Vallarta", "ok", "Municipio de la Costa por nombre"),
    ("A02", "correcto", "067", "ok", "Municipio de la Costa por clave"),
    ("A03", "correcto", "Villa Purificación", "ok", "Municipio con acento (clave real 068)"),
    ("A04", "correcto", "cihuatlan", "ok", "Nombre sin acento y en minúsculas"),
    ("B01", "municipio inexistente", "Narnia", "rechazo", "Nombre que no existe"),
    ("B02", "municipio inexistente", "999", "rechazo", "Clave que no existe"),
    ("B03", "municipio inexistente", "Monterrey", "rechazo", "Municipio de otro estado"),
    ("B04", "municipio inexistente", "Puerto Vallarta'; DROP TABLE--", "rechazo", "Texto malicioso/raro"),
    ("C01", "datos vacíos", "", "rechazo", "Municipio vacío"),
    ("C02", "datos vacíos", "   ", "rechazo", "Municipio con solo espacios"),
    ("C03", "datos vacíos", "Mixtlán", "ok_o_rechazo", "Municipio válido sin casos históricos: respuesta clara (200 con casos en 0, o mensaje claro), nunca error 500"),
]

filas, bugs = [], []
for id_, tipo, muni, esperado, desc in CASOS:
    codigo, cuerpo = llamar(muni)
    motivo = ""
    if codigo is None:
        ok, motivo = False, f"No hubo respuesta: {cuerpo}"
    elif codigo >= 500:
        ok, motivo = False, f"La API respondió error {codigo} (error del servidor)"
    elif parece_error_tecnico(cuerpo):
        ok, motivo = False, "La respuesta muestra un error técnico (página de error o traza) en lugar de un mensaje claro"
    elif esperado == "ok":
        ok = codigo == 200 and json_ok(cuerpo)
        if not ok: motivo = f"Se esperaba 200 con contenido y llegó {codigo}"
    elif esperado == "rechazo":
        ok = codigo in (400, 404, 422) and len(cuerpo.strip()) > 0
        if not ok: motivo = f"Se esperaba 400/404 con un mensaje claro y llegó {codigo}"
    else:
        ok = codigo in (200, 400, 404, 422) and len(cuerpo.strip()) > 0
        if not ok: motivo = f"Respuesta inesperada: {codigo}"
    filas.append({"id": id_, "tipo": tipo, "municipio_enviado": muni, "descripcion": desc,
                  "codigo_http": codigo, "resultado": "OK" if ok else "FALLA", "motivo": motivo,
                  "respuesta_inicio": cuerpo[:150].replace("\n", " ")})
    if not ok:
        bugs.append((id_, desc, muni, codigo, motivo))

with open(args.reporte, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)

print(f"{'id':4} {'tipo':22} {'enviado':34} {'http':5} resultado")
for r in filas:
    print(f"{r['id']:4} {r['tipo']:22} {r['municipio_enviado'][:32]!r:34} {str(r['codigo_http']):5} {r['resultado']}  {r['motivo']}")
print(f"\nResultado: {sum(r['resultado'] == 'OK' for r in filas)} correctas, {len(bugs)} fallas. Reporte: {args.reporte}")
if bugs:
    print("\nTEXTO SUGERIDO PARA TARJETAS BUG (una por falla):")
    for id_, desc, muni, codigo, motivo in bugs:
        print(f"- Bug {id_} - {desc}\n  Pasos: pedir a la API el municipio {muni!r}.\n  Esperado: respuesta clara (200 con datos, o 400/404 con mensaje).\n  Pasó: {motivo}.")
sys.exit(1 if bugs else 0)
