"""API SIMULADA solo para probar cliente_api.py sin la API real del CTO.
Imita los tres puntos que se usan: inicio de sesión, POST /api/cargas/ y POST /api/predicciones/.
Las reglas de validación están supuestas a partir de lo que dice la plantilla y el cliente; la API real puede diferir.
Uso: python pruebas/api_simulada.py [puerto]   (por omisión 8765)"""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "token-de-prueba"
CARGAS, PREDICCIONES = [], []

class H(BaseHTTPRequestHandler):
    def _resp(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"null")
        if self.path.startswith("/login"):
            if cuerpo.get("password") == "bien":
                return self._resp(200, {"idToken": TOKEN})
            return self._resp(400, {"error": {"message": "INVALID_PASSWORD"}})
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self._resp(401, {"detalle": "Token inválido o vencido"})
        if self.path == "/api/cargas/":
            errores = {}
            vistos = set()
            for i, f in enumerate(cuerpo if isinstance(cuerpo, list) else []):
                e = []
                if not isinstance(f.get("anio"), (int, float)) or f["anio"] < 2000: e.append("anio inválido")
                if not isinstance(f.get("mes"), (int, float)) or not 1 <= f["mes"] <= 12: e.append("mes debe ser de 1 a 12")
                if f.get("casos_dengue") is not None and f["casos_dengue"] < 0: e.append("casos_dengue no puede ser negativo")
                if (f.get("anio"), f.get("mes")) in vistos: e.append("año y mes repetidos")
                vistos.add((f.get("anio"), f.get("mes")))
                if e: errores[str(i)] = e
            if not isinstance(cuerpo, list) or not cuerpo:
                return self._resp(400, {"detalle": "Se esperaba una lista de filas"})
            if errores:
                return self._resp(400, errores)    # una fila mala: no se guarda nada
            CARGAS.extend(cuerpo)
            return self._resp(201, {"filas_guardadas": len(cuerpo)})
        if self.path == "/api/predicciones/":
            s = cuerpo.get("semanas")
            if cuerpo.get("enfermedad") != "dengue": return self._resp(400, {"enfermedad": "no existe"})
            if not (isinstance(s, list) and len(s) == 4 and all(isinstance(v, (int, float)) for v in s)):
                return self._resp(400, {"semanas": "deben ser 4 números"})
            if not 1 <= cuerpo.get("mes", 0) <= 12: return self._resp(400, {"mes": "de 1 a 12"})
            total = round(sum(s), 2)
            PREDICCIONES.append(cuerpo)
            return self._resp(201, {"total": total, "alerta": {"nivel": "alto"} if total >= 30 else None})
        self._resp(404, {"detalle": "No existe"})

    def log_message(self, *a): pass

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
