"""Pruebas de la API según el contrato real (docs/API_ESCRITORIO.md): casos correctos, municipio/enfermedad inexistente
y datos vacíos o inválidos. Sirve para la API simulada del repositorio y para el backend real de Django.
Solo usa la biblioteca estándar de Python.

Qué se considera correcto (del contrato):
  - Casos correctos       -> 200 o 201 con la forma descrita en el contrato.
  - Claves inexistentes   -> 400 (o 404) con un mensaje claro. Nunca 5xx ni una página de error técnico.
  - Datos vacíos/inválidos-> 400 con el mensaje del campo; en /cargas/ las llaves son el índice de la fila desde 0.
  - Sin token o token falso -> 401. Usuario con rol consulta en acciones de administrador -> 403.

SEGURIDAD: por omisión SOLO LEE (no crea ni cambia nada). Las pruebas que escriben (/cargas/ y /predicciones/) usan el
año 2099 para las cargas, pero /predicciones/ SÍ reemplaza la predicción vigente y crea una alerta pendiente.
Úsalas con --escribir solo contra la API simulada o contra una base de pruebas, nunca contra la base real.

Uso:
  python probar_contrato_api.py --url http://127.0.0.1:8000/api --escribir
  (contraseñas por variables de entorno: USUARIO_EMAIL, USUARIO_PASSWORD, CONSULTA_EMAIL, CONSULTA_PASSWORD;
   para Firebase real también FIREBASE_API_KEY. Con una API local, el inicio de sesión se busca en
   <servidor>/identitytoolkit/v1/accounts:signInWithPassword, o usa --login-url)
Salida: tabla en pantalla, reporte CSV y texto sugerido para una tarjeta Bug por cada falla. Código de salida 1 si hay fallas."""
import argparse, csv, json, os, sys, urllib.request, urllib.error, urllib.parse

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True, help="Dirección base de la API terminada en /api")
ap.add_argument("--login-url", default=None)
ap.add_argument("--escribir", action="store_true", help="Incluye las pruebas que crean o cambian datos (solo base de pruebas)")
ap.add_argument("--reporte", default="reporte_contrato_api.csv")
ap.add_argument("--espera", type=float, default=30.0)
args = ap.parse_args()
BASE = args.url.rstrip("/")
HOST = BASE[: BASE.rfind("/api")] if "/api" in BASE else BASE
LOCAL = any(h in BASE for h in ("127.0.0.1", "localhost"))
LOGIN = args.login_url or os.getenv("FIREBASE_LOGIN_URL") or (
    f"{HOST}/identitytoolkit/v1/accounts:signInWithPassword" if LOCAL
    else "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword")

CLAVES_OFICIALES = {"14012", "14020", "14038", "14058", "14062", "14067", "14080", "14084",
                    "14021", "14022", "14027", "14043", "14100", "14068"}   # 14 municipios de la Costa (claves INEGI)

def llamar(metodo, ruta, cuerpo=None, token=None, crudo=None, url=None):
    datos = crudo if crudo is not None else (None if cuerpo is None else json.dumps(cuerpo).encode())
    req = urllib.request.Request(url or (BASE + ruta), data=datos, method=metodo)
    if datos is not None: req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=args.espera) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def js(txt):
    try: return json.loads(txt)
    except Exception: return None

def login(email, password):
    if not email or not password: return None
    c, t = llamar("POST", "", {"email": email, "password": password, "returnSecureToken": True},
                  url=f"{LOGIN}?key={os.getenv('FIREBASE_API_KEY', 'x')}")
    return (js(t) or {}).get("idToken") if c == 200 else None

ADMIN = login(os.getenv("USUARIO_EMAIL"), os.getenv("USUARIO_PASSWORD"))
CONSULTA = login(os.getenv("CONSULTA_EMAIL"), os.getenv("CONSULTA_PASSWORD"))

def tecnico(txt):
    t = txt.lower()
    return any(p in t for p in ["traceback", "<!doctype html", "<html", "exception", "keyerror", "attributeerror", "typeerror", "valueerror"])

PRUEBAS = []   # (id, tipo, descripcion, funcion, necesita_escritura)
def prueba(id_, tipo, desc, escritura=False):
    def deco(f): PRUEBAS.append((id_, tipo, desc, f, escritura)); return f
    return deco

def codigo_en(c, t, validos):
    if c is None: return False, f"No hubo respuesta: {t}"
    if c >= 500: return False, f"Error del servidor {c}"
    if tecnico(t) and c >= 400: return False, "La respuesta es un error técnico, no un mensaje claro"
    if c not in validos: return False, f"Se esperaba {'/'.join(map(str, validos))} y llegó {c}: {t[:100]}"
    return True, ""

# ---------------- Casos correctos ----------------
@prueba("A01", "correcto", "GET /municipios/ público: 14 municipios con clave INEGI y región")
def _():
    c, t = llamar("GET", "/municipios/"); ok, m = codigo_en(c, t, (200,))
    d = js(t)
    if not ok: return ok, m
    if not isinstance(d, list) or len(d) != 14: return False, f"Se esperaban 14 municipios y llegaron {len(d) if isinstance(d, list) else 'otra cosa'}"
    faltan = {x.get("clave_inegi") for x in d} ^ CLAVES_OFICIALES
    return (not faltan, f"Claves que no coinciden con las oficiales: {sorted(faltan)}" if faltan else "")
@prueba("A02", "correcto", "GET /enfermedades/ público incluye dengue (transmisible)")
def _():
    c, t = llamar("GET", "/enfermedades/"); ok, m = codigo_en(c, t, (200,))
    if not ok: return ok, m
    return any(e.get("clave") == "dengue" and e.get("tipo") == "transmisible" for e in js(t) or []), "No aparece dengue como transmisible"
@prueba("A03", "correcto", "GET /yo/ con usuario administrador devuelve rol admin")
def _():
    if not ADMIN: return None, "No se pudo iniciar sesión como administrador (revisa USUARIO_EMAIL/USUARIO_PASSWORD)"
    c, t = llamar("GET", "/yo/", token=ADMIN); ok, m = codigo_en(c, t, (200,))
    return (ok and (js(t) or {}).get("rol") == "admin", m or f"Rol recibido: {(js(t) or {}).get('rol')}")
@prueba("A04", "correcto", "GET /yo/ con usuario de consulta devuelve rol consulta")
def _():
    if not CONSULTA: return None, "Sin usuario de consulta (CONSULTA_EMAIL/CONSULTA_PASSWORD)"
    c, t = llamar("GET", "/yo/", token=CONSULTA); ok, m = codigo_en(c, t, (200,))
    return (ok and (js(t) or {}).get("rol") == "consulta", m or f"Rol recibido: {(js(t) or {}).get('rol')}")
@prueba("A05", "correcto", "GET /mapa/?enfermedad=dengue con sesión: forma del contrato")
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    c, t = llamar("GET", "/mapa/?enfermedad=dengue", token=ADMIN); ok, m = codigo_en(c, t, (200,)); d = js(t) or {}
    if not ok: return ok, m
    faltan = [k for k in ("enfermedad", "prediccion", "casos_anio_anterior", "alerta", "municipios") if k not in d]
    return (not faltan, f"Faltan campos: {faltan}" if faltan else "")
@prueba("A06", "correcto", "GET /estadisticas/?enfermedad=dengue&anio=2026 con sesión: forma del contrato")
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    c, t = llamar("GET", "/estadisticas/?enfermedad=dengue&anio=2026", token=ADMIN); ok, m = codigo_en(c, t, (200,)); d = js(t) or {}
    if not ok: return ok, m
    faltan = [k for k in ("filtros", "casos_por_mes", "clima_por_mes", "prediccion") if k not in d]
    return (not faltan, f"Faltan campos: {faltan}" if faltan else "")
@prueba("A07", "correcto", "GET /predicciones/?enfermedad=dengue con sesión: prediccion con 4 semanas o null")
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    c, t = llamar("GET", "/predicciones/?enfermedad=dengue", token=ADMIN); ok, m = codigo_en(c, t, (200,)); d = js(t) or {}
    if not ok: return ok, m
    p = d.get("prediccion", "FALTA")
    return (p is None or (isinstance(p, dict) and len(p.get("semanas", [])) == 4)), f"prediccion inesperada: {str(p)[:100]}"
@prueba("A08", "correcto", "POST /cargas/ con filas válidas -> 201 y conteo de creados/actualizados", True)
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    filas = [{"anio": 2099, "mes": 1, "casos_dengue": 5, "temperatura_c": 25.5, "humedad_pct": 70, "precipitacion_mm": 10.0},
             {"anio": 2099, "mes": 2, "casos_dengue": 0, "temperatura_c": None, "humedad_pct": None, "precipitacion_mm": None}]
    c, t = llamar("POST", "/cargas/", filas, ADMIN); ok, m = codigo_en(c, t, (201,)); d = js(t) or {}
    return (ok and "casos" in d and "clima" in d), m or f"Respuesta sin 'casos' y 'clima': {t[:100]}"
@prueba("A09", "correcto", "POST /cargas/ con casos como 5.0 (así los manda pandas con celdas vacías) -> se acepta", True)
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    c, t = llamar("POST", "/cargas/", [{"anio": 2099, "mes": 3, "casos_dengue": 5.0}], ADMIN)
    return codigo_en(c, t, (201,))
@prueba("A10", "correcto", "POST /predicciones/ con 4 semanas -> 201, total = suma, trae alerta", True)
def _():
    if not ADMIN: return None, "Sin sesión de administrador"
    c, t = llamar("POST", "/predicciones/", {"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": [1.2, 1.96, 0.8, 0.5]}, ADMIN)
    ok, m = codigo_en(c, t, (201,)); d = js(t) or {}
    if not ok: return ok, m
    return (abs(d.get("total", -1) - 4.46) < 0.01 and "alerta" in d), m or f"total/alerta incorrectos: {t[:120]}"

# ---------------- Permisos ----------------
@prueba("P01", "permisos", "GET /mapa/ sin token -> 401")
def _():
    c, t = llamar("GET", "/mapa/?enfermedad=dengue"); return codigo_en(c, t, (401,))
@prueba("P02", "permisos", "GET /alertas/ con token falso -> 401")
def _():
    c, t = llamar("GET", "/alertas/", token="token-falso"); return codigo_en(c, t, (401,))
@prueba("P03", "permisos", "Usuario de consulta no puede cargar datos (POST /cargas/) -> 403")
def _():
    if not CONSULTA: return None, "Sin usuario de consulta"
    c, t = llamar("POST", "/cargas/", [{"anio": 2099, "mes": 4, "casos_dengue": 1}], CONSULTA); return codigo_en(c, t, (403,))
@prueba("P04", "permisos", "Usuario de consulta no puede registrar predicciones (POST /predicciones/) -> 403")
def _():
    if not CONSULTA: return None, "Sin usuario de consulta"
    c, t = llamar("POST", "/predicciones/", {"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": [1, 1, 1, 1]}, CONSULTA); return codigo_en(c, t, (403,))
@prueba("P05", "permisos", "POST /predicciones/ sin token -> 401")
def _():
    c, t = llamar("POST", "/predicciones/", {"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": [1, 1, 1, 1]}); return codigo_en(c, t, (401,))

# ---------------- Municipio / enfermedad inexistente ----------------
def con_admin(f):
    def g():
        if not ADMIN: return None, "Sin sesión de administrador"
        return f()
    return g
@prueba("N01", "inexistente", "GET /estadisticas/ con enfermedad inexistente -> 400 con mensaje")
@con_admin
def _():
    c, t = llamar("GET", "/estadisticas/?enfermedad=narnia", token=ADMIN); return codigo_en(c, t, (400, 404))
@prueba("N02", "inexistente", "GET /estadisticas/ crónica con municipio inexistente (99999) -> 400")
@con_admin
def _():
    c, t = llamar("GET", "/estadisticas/?enfermedad=dm2&municipio=99999", token=ADMIN); return codigo_en(c, t, (400, 404))
@prueba("N03", "inexistente", "GET /estadisticas/ con municipio con texto raro (inyección) -> 400, nunca error técnico")
@con_admin
def _():
    c, t = llamar("GET", "/estadisticas/?enfermedad=dm2&municipio=" + urllib.parse.quote("14067'; DROP TABLE--"), token=ADMIN); return codigo_en(c, t, (400, 404))
@prueba("N04", "inexistente", "GET /mapa/ con enfermedad inexistente -> 400")
@con_admin
def _():
    c, t = llamar("GET", "/mapa/?enfermedad=narnia", token=ADMIN); return codigo_en(c, t, (400, 404))
@prueba("N05", "inexistente", "GET /mapa/ sin el parámetro obligatorio enfermedad -> 400")
@con_admin
def _():
    c, t = llamar("GET", "/mapa/", token=ADMIN); return codigo_en(c, t, (400,))
@prueba("N06", "inexistente", "GET /estadisticas/ con año que no es número -> 400")
@con_admin
def _():
    c, t = llamar("GET", "/estadisticas/?enfermedad=dengue&anio=abc", token=ADMIN); return codigo_en(c, t, (400,))
@prueba("N07", "inexistente", "POST /alertas/999999/confirmar/ (alerta inexistente) -> 404", True)
@con_admin
def _():
    c, t = llamar("POST", "/alertas/999999/confirmar/", {"mensaje_publico": "x"}, ADMIN); return codigo_en(c, t, (404,))
@prueba("N08", "inexistente", "POST /predicciones/ con enfermedad inexistente -> 400", True)
@con_admin
def _():
    c, t = llamar("POST", "/predicciones/", {"enfermedad": "narnia", "anio": 2099, "mes": 1, "semanas": [1, 1, 1, 1]}, ADMIN); return codigo_en(c, t, (400, 404))
@prueba("N09", "inexistente", "GET /contenido/999999/ (no existe) -> 404")
@con_admin
def _():
    c, t = llamar("GET", "/contenido/999999/", token=ADMIN); return codigo_en(c, t, (404,))

# ---------------- Datos vacíos o inválidos ----------------
def cargas(filas, validos=(400,)):
    c, t = llamar("POST", "/cargas/", filas, ADMIN); return codigo_en(c, t, validos)
@prueba("E01", "datos vacíos", "POST /cargas/ con lista vacía [] -> 400 con mensaje", True)
@con_admin
def _(): return cargas([])
@prueba("E02", "datos vacíos", "POST /cargas/ con un objeto en vez de una lista -> 400", True)
@con_admin
def _(): return cargas({"anio": 2099, "mes": 1})
@prueba("E03", "datos vacíos", "POST /cargas/ con fila vacía {} -> 400 (anio y mes son obligatorios)", True)
@con_admin
def _(): return cargas([{}])
@prueba("E04", "datos vacíos", "POST /cargas/ con mes 13 -> 400 y la llave es el índice de la fila (0)", True)
@con_admin
def _():
    c, t = llamar("POST", "/cargas/", [{"anio": 2099, "mes": 13, "casos_dengue": 1}], ADMIN); ok, m = codigo_en(c, t, (400,))
    return (ok and "0" in (js(t) or {})), m or f"La respuesta no usa el índice de fila como llave: {t[:100]}"
@prueba("E05", "datos vacíos", "POST /cargas/ con casos negativos -> 400", True)
@con_admin
def _(): return cargas([{"anio": 2099, "mes": 5, "casos_dengue": -3}])
@prueba("E06", "datos vacíos", "POST /cargas/ con casos como texto -> 400", True)
@con_admin
def _(): return cargas([{"anio": 2099, "mes": 5, "casos_dengue": "muchos"}])
@prueba("E07", "datos vacíos", "POST /cargas/ con humedad 150 -> 400", True)
@con_admin
def _(): return cargas([{"anio": 2099, "mes": 5, "humedad_pct": 150}])
@prueba("E08", "datos vacíos", "POST /cargas/ con año y mes repetidos -> 400", True)
@con_admin
def _(): return cargas([{"anio": 2099, "mes": 6, "casos_dengue": 1}, {"anio": 2099, "mes": 6, "casos_dengue": 2}])
@prueba("E09", "datos vacíos", "POST /cargas/ todo o nada: una fila buena y una mala -> 400 y la buena NO se guarda", True)
@con_admin
def _():
    c, t = llamar("POST", "/cargas/", [{"anio": 2098, "mes": 7, "casos_dengue": 11}, {"anio": 2098, "mes": 99, "casos_dengue": 1}], ADMIN)
    ok, m = codigo_en(c, t, (400,))
    if not ok: return ok, m
    c2, t2 = llamar("GET", "/estadisticas/?enfermedad=dengue&anio=2098", token=ADMIN)
    meses = [x.get("mes") for x in (js(t2) or {}).get("casos_por_mes", [])]
    return (7 not in meses), "La fila buena se guardó aunque otra falló (no es todo o nada)"
@prueba("E10", "datos vacíos", "POST /cargas/ con fila sin casos ni clima (solo año y mes) -> 400 con mensaje", True)
@con_admin
def _():
    c, t = llamar("POST", "/cargas/", [{"anio": 2099, "mes": 8, "casos_dengue": None, "temperatura_c": None, "humedad_pct": None, "precipitacion_mm": None}], ADMIN)
    return codigo_en(c, t, (400,))
@prueba("E11", "datos vacíos", "POST /cargas/ con JSON mal formado -> 400, no error del servidor", True)
@con_admin
def _():
    c, t = llamar("POST", "/cargas/", crudo=b"[{anio: 2099", token=ADMIN); return codigo_en(c, t, (400,))
def pred(cuerpo): 
    c, t = llamar("POST", "/predicciones/", cuerpo, ADMIN); return codigo_en(c, t, (400,))
@prueba("E12", "datos vacíos", "POST /predicciones/ con solo 3 semanas -> 400", True)
@con_admin
def _(): return pred({"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": [1, 2, 3]})
@prueba("E13", "datos vacíos", "POST /predicciones/ con semanas negativas -> 400", True)
@con_admin
def _(): return pred({"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": [1, -2, 3, 4]})
@prueba("E14", "datos vacíos", "POST /predicciones/ con semanas como texto -> 400", True)
@con_admin
def _(): return pred({"enfermedad": "dengue", "anio": 2099, "mes": 1, "semanas": ["a", "b", "c", "d"]})
@prueba("E15", "datos vacíos", "POST /predicciones/ sin el campo semanas -> 400", True)
@con_admin
def _(): return pred({"enfermedad": "dengue", "anio": 2099, "mes": 1})
@prueba("E16", "datos vacíos", "POST /predicciones/ con cuerpo vacío {} -> 400 (faltan enfermedad, anio, mes y semanas)", True)
@con_admin
def _(): return pred({})
@prueba("E17", "datos vacíos", "POST /predicciones/ con mes 13 -> 400", True)
@con_admin
def _(): return pred({"enfermedad": "dengue", "anio": 2099, "mes": 13, "semanas": [1, 1, 1, 1]})

# ---------------- Ejecución ----------------
filas, bugs = [], []
for id_, tipo, desc, f, escritura in PRUEBAS:
    if escritura and not args.escribir:
        filas.append({"id": id_, "tipo": tipo, "prueba": desc, "resultado": "OMITIDA", "motivo": "Escribe datos: usa --escribir en una base de pruebas"}); continue
    try:
        ok, motivo = f()
    except Exception as e:
        ok, motivo = False, f"La prueba falló al ejecutarse: {type(e).__name__}: {e}"
    res = "OMITIDA" if ok is None else ("OK" if ok else "FALLA")
    filas.append({"id": id_, "tipo": tipo, "prueba": desc, "resultado": res, "motivo": "" if ok else motivo})
    if ok is False: bugs.append((id_, desc, motivo))

with open(args.reporte, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)
for r in filas:
    print(f"{r['id']:4} {r['tipo']:13} {r['resultado']:8} {r['prueba'][:85]}" + (f"\n{'':27}-> {r['motivo']}" if r["motivo"] and r["resultado"] != "OMITIDA" else ""))
n = lambda x: sum(r["resultado"] == x for r in filas)
print(f"\nResultado: {n('OK')} correctas, {n('FALLA')} fallas, {n('OMITIDA')} omitidas. Reporte: {args.reporte}")
if bugs:
    print("\nTEXTO SUGERIDO PARA TARJETAS BUG (una por falla):")
    for id_, desc, motivo in bugs:
        print(f"- Bug {id_}: {desc}\n  Esperado: según docs/API_ESCRITORIO.md.\n  Pasó: {motivo}")
sys.exit(1 if bugs else 0)
