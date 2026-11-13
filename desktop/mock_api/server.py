"""Independent HTTP Mock API server for the HACKAJAL desktop application.

Simulates all endpoints defined in API_ESCRITORIO.md and Firebase Auth,
enforcing Bearer tokens, admin/consulta roles, and returning clearly marked simulated data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from desktop.mock_api.data import db
from desktop.mock_api.tokens import generate_mock_token, verify_mock_token


class MockRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler implementing the API_ESCRITORIO.md contract."""

    server_version = "HackaJalMockAPI/1.0"

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard stderr request logging unless explicitly desired."""
        pass

    # -------------------------------------------------------------------------
    # Helper response methods
    # -------------------------------------------------------------------------

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept")
        self.send_header("X-Mock-Data", "true")
        self.send_header("X-Mock-Server", "HACKAJAL-Desktop-Mock")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status: int, data: Any) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_no_content(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def _read_json_body(self) -> Any:
        if hasattr(self, "_current_body") and self._current_body is not None:
            return self._current_body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._current_body = None
                return None
            body = self.rfile.read(content_length)
            self._current_body = json.loads(body.decode("utf-8"))
            return self._current_body
        except Exception:
            self._current_body = None
            return None

    # -------------------------------------------------------------------------
    # Authentication & Authorization
    # -------------------------------------------------------------------------

    def _get_authenticated_user(self) -> tuple[dict[str, Any] | None, int | None, dict[str, Any] | None]:
        """Extract and verify token from Authorization header.
        
        Returns (user_dict, error_status, error_payload).
        """
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None, 401, {"detail": "Las credenciales de autenticación no se proveyeron."}

        token = auth_header[7:].strip()
        payload = verify_mock_token(token)
        if not payload:
            return None, 401, {"detail": "Token inválido o expirado."}

        user = db.get_user_by_token(payload)
        if not user:
            return None, 401, {"detail": "Usuario no encontrado."}

        return user, None, None

    def _require_auth(self) -> dict[str, Any] | None:
        user, err_status, err_payload = self._get_authenticated_user()
        if err_status is not None:
            self._send_json(err_status, err_payload)
            return None
        return user

    def _require_admin(self) -> dict[str, Any] | None:
        user = self._require_auth()
        if not user:
            return None
        if user.get("rol") != "admin":
            self._send_json(403, {"detail": "No tienes permiso para esta acción."})
            return None
        return user

    # -------------------------------------------------------------------------
    # Request Dispatchers
    # -------------------------------------------------------------------------

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/") + "/"
        # Normalize: strip /api if present
        if path.startswith("/api/"):
            path = path[4:]
        params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

        # Health
        if path in ("/", "/health/", "/api/health/"):
            self._send_json(200, {"status": "ok", "mock": True, "service": "HACKAJAL Mock API"})
            return

        # 4.2 GET /municipios/ 🔓
        if path == "/municipios/":
            self._send_json(200, db.municipios)
            return

        # 4.3 GET /enfermedades/ 🔓
        if path == "/enfermedades/":
            self._send_json(200, db.enfermedades)
            return

        # Protected endpoints below
        user = self._require_auth()
        if not user:
            return

        # 4.1 GET /yo/ 🔒
        if path == "/yo/":
            if not user.get("is_registered", True):
                self._send_json(401, {"detail": "Tu cuenta no tiene acceso; contacta al administrador."})
                return
            self._send_json(200, {
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
                "organizacion": user["organizacion"],
            })
            return

        # 4.4 GET /mapa/?enfermedad= 🔒
        if path == "/mapa/":
            enfermedad = params.get("enfermedad")
            if not enfermedad:
                self._send_json(400, {"detail": "El parámetro 'enfermedad' es obligatorio."})
                return
            if not any(e["clave"] == enfermedad for e in db.enfermedades):
                self._send_json(400, {"detail": f"Enfermedad '{enfermedad}' no reconocida."})
                return
            # Find current active/pending alert for the disease
            active_alert = next((a for a in db.alertas if a["enfermedad"] == enfermedad and a["estado"] == "pendiente"), None)
            if not active_alert:
                active_alert = next((a for a in db.alertas if a["enfermedad"] == enfermedad and a["estado"] == "confirmada"), None)
            alert_summary = {"id": active_alert["id"], "estado": active_alert["estado"]} if active_alert else None
            self._send_json(200, {
                "enfermedad": enfermedad,
                "prediccion": db.prediccion if enfermedad == "dengue" else None,
                "casos_anio_anterior": 2 if enfermedad == "dengue" else None,
                "alerta": alert_summary,
                "municipios": db.municipios,
            })
            return

        # 4.6 GET /estadisticas/encuesta/ 🔒 (must precede /estadisticas/)
        if path == "/estadisticas/encuesta/":
            self._send_json(200, db.encuesta)
            return

        # 4.5 GET /estadisticas/ 🔒
        if path == "/estadisticas/":
            enfermedad = params.get("enfermedad", "dengue")
            anio_str = params.get("anio", "2026")
            municipio = params.get("municipio")

            try:
                anio = int(anio_str)
            except ValueError:
                self._send_json(400, {"anio": ["El año debe ser un número entero."]})
                return

            if not any(e["clave"] == enfermedad for e in db.enfermedades):
                self._send_json(400, {"enfermedad": [f"Clave de enfermedad '{enfermedad}' inválida."]})
                return

            if enfermedad == "dm2":
                cronicas = db.cronicas
                if municipio:
                    cronicas = [c for c in cronicas if c["municipio__clave_inegi"] == municipio or c["municipio__clave_inegi"] is None]
                self._send_json(200, {
                    "filtros": {"enfermedad": enfermedad, "municipio": municipio, "anio": anio},
                    "casos_por_mes": None,
                    "clima_por_mes": None,
                    "prediccion": None,
                    "cronicas": cronicas,
                })
                return

            # dengue
            casos = db.casos_por_mes.get(anio, [])
            clima = db.clima_por_mes.get(anio, [])
            pred = db.prediccion if anio == db.prediccion.get("anio", 2026) else None
            self._send_json(200, {
                "filtros": {"enfermedad": enfermedad, "municipio": municipio, "anio": anio},
                "casos_por_mes": casos,
                "clima_por_mes": clima,
                "prediccion": pred,
                "cronicas": None,
            })
            return

        # 4.7 GET /predicciones/ 🔒
        if path == "/predicciones/":
            enfermedad = params.get("enfermedad", "dengue")
            pred = db.prediccion if enfermedad == "dengue" else None
            self._send_json(200, {"prediccion": pred})
            return

        # 4.8 GET /alertas/ 🔒
        if path == "/alertas/":
            estado = params.get("estado")
            enfermedad = params.get("enfermedad")
            alertas = db.alertas
            if estado:
                alertas = [a for a in alertas if a["estado"] == estado]
            if enfermedad:
                alertas = [a for a in alertas if a["enfermedad"] == enfermedad]
            # Order newest to oldest
            alertas_sorted = sorted(alertas, key=lambda a: a.get("creada_en", ""), reverse=True)
            self._send_json(200, alertas_sorted)
            return

        # 4.11 GET /contenido/ 🔒
        if path == "/contenido/":
            tipo = params.get("tipo")
            enfermedad = params.get("enfermedad")
            items = db.contenido
            if tipo:
                items = [i for i in items if i["tipo"] == tipo]
            if enfermedad:
                items = [i for i in items if i["enfermedad"] == enfermedad]
            self._send_json(200, items)
            return

        # 4.12 GET /contenido/{id}/ 🔒
        match_contenido = re.match(r"^/contenido/(\d+)/$", path)
        if match_contenido:
            cid = int(match_contenido.group(1))
            item = next((i for i in db.contenido if i["id"] == cid), None)
            if not item:
                self._send_json(404, {"detail": "Contenido no encontrado."})
                return
            self._send_json(200, item)
            return

        self._send_json(404, {"detail": "Ruta no encontrada."})

    def do_POST(self) -> None:
        self._current_body = None
        self._read_json_body()
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/") + "/"
        if path.startswith("/api/"):
            path = path[4:]

        # 3.1 Firebase Login Simulation
        # Matches /accounts:signInWithPassword or /v1/accounts:signInWithPassword or /identitytoolkit/...
        if "accounts:signInWithPassword" in parsed_url.path:
            body = self._read_json_body() or {}
            email = body.get("email", "").strip().lower()
            password = body.get("password", "")
            user = db.get_user_by_email(email)

            if not user or user["password"] != password:
                self._send_json(400, {
                    "error": {
                        "message": "INVALID_LOGIN_CREDENTIALS",
                        "code": 400,
                        "errors": [{"message": "INVALID_LOGIN_CREDENTIALS", "domain": "global", "reason": "invalid"}],
                    }
                })
                return

            token = generate_mock_token(user["email"], user["rol"])
            self._send_json(200, {
                "idToken": token,
                "email": user["email"],
                "refreshToken": f"mock-refresh-{user['rol']}",
                "expiresIn": "3600",
                "localId": user["email"],
            })
            return

        # 4.9 POST /alertas/{id}/confirmar/ 👑
        match_confirmar = re.match(r"^/alertas/(\d+)/confirmar/$", path)
        if match_confirmar:
            user = self._require_admin()
            if not user:
                return
            aid = int(match_confirmar.group(1))
            alert = next((a for a in db.alertas if a["id"] == aid), None)
            if not alert:
                self._send_json(404, {"detail": "Alerta no encontrada."})
                return
            if alert["estado"] in ("confirmada", "descartada"):
                self._send_json(409, {"detail": f"La alerta ya está {alert['estado']}."})
                return
            body = self._read_json_body() or {}
            mensaje = body.get("mensaje_publico", "").strip()
            if not mensaje:
                self._send_json(400, {"mensaje_publico": ["Este campo es obligatorio."]})
                return
            if len(mensaje) > 2000:
                self._send_json(400, {"mensaje_publico": ["Asegúrese de que este campo no tenga más de 2000 caracteres."]})
                return

            alert["estado"] = "confirmada"
            alert["mensaje_publico"] = mensaje
            alert["revisada_por"] = user["nombre"]
            alert["revisada_en"] = datetime.now(timezone.utc).isoformat()
            self._send_json(200, alert)
            return

        # 4.10 POST /alertas/{id}/descartar/ 👑
        match_descartar = re.match(r"^/alertas/(\d+)/descartar/$", path)
        if match_descartar:
            user = self._require_admin()
            if not user:
                return
            aid = int(match_descartar.group(1))
            alert = next((a for a in db.alertas if a["id"] == aid), None)
            if not alert:
                self._send_json(404, {"detail": "Alerta no encontrada."})
                return
            if alert["estado"] in ("confirmada", "descartada"):
                self._send_json(409, {"detail": "La alerta ya fue revisada."})
                return

            alert["estado"] = "descartada"
            alert["revisada_por"] = user["nombre"]
            alert["revisada_en"] = datetime.now(timezone.utc).isoformat()
            self._send_json(200, alert)
            return

        # 4.13 POST /contenido/ 👑
        if path == "/contenido/":
            user = self._require_admin()
            if not user:
                return
            body = self._read_json_body() or {}
            tipo = body.get("tipo")
            titulo = body.get("titulo", "").strip()
            cuerpo = body.get("cuerpo", "").strip()
            enfermedad = body.get("enfermedad")

            errors: dict[str, list[str]] = {}
            if tipo not in ("prevencion", "articulo", "nota"):
                errors["tipo"] = ["Debe ser 'prevencion', 'articulo' o 'nota'." if tipo else "Este campo es obligatorio."]
            if not titulo:
                errors["titulo"] = ["Este campo es obligatorio."]
            elif len(titulo) > 200:
                errors["titulo"] = ["Asegúrese de que este campo no tenga más de 200 caracteres."]
            if not cuerpo:
                errors["cuerpo"] = ["Este campo es obligatorio."]

            if errors:
                self._send_json(400, errors)
                return

            new_item = {
                "id": db.next_contenido_id(),
                "tipo": tipo,
                "enfermedad": enfermedad,
                "titulo": f"{titulo} [SIMULADO]" if "[SIMULADO]" not in titulo else titulo,
                "cuerpo": cuerpo,
                "url_fuente": body.get("url_fuente", ""),
                "imagen_url": body.get("imagen_url", ""),
                "publicado": bool(body.get("publicado", False)),
                "autor": user["nombre"],
                "fecha": datetime.now(timezone.utc).isoformat(),
            }
            db.contenido.append(new_item)
            self._send_json(201, new_item)
            return

        # 4.16 POST /cargas/ 👑
        if path == "/cargas/":
            user = self._require_admin()
            if not user:
                return
            body = self._read_json_body()
            if not isinstance(body, list) or len(body) == 0:
                self._send_json(400, {"detail": "Se esperaba una lista no vacía de filas."})
                return

            row_errors: dict[str, dict[str, list[str]]] = {}
            seen_years_months: set[tuple[int, int]] = set()

            for idx, row in enumerate(body):
                idx_errs: dict[str, list[str]] = {}
                anio = row.get("anio")
                mes = row.get("mes")

                if anio is None:
                    idx_errs["anio"] = ["Este campo es obligatorio."]
                elif not isinstance(anio, int) or anio < 2000 or anio > 2100:
                    idx_errs["anio"] = ["Debe ser un año entre 2000 y 2100."]

                if mes is None:
                    idx_errs["mes"] = ["Este campo es obligatorio."]
                elif not isinstance(mes, int) or mes < 1 or mes > 12:
                    idx_errs["mes"] = ["Asegúrese de que este valor es menor o igual a 12 y mayor o igual a 1."]

                if anio and mes:
                    key = (anio, mes)
                    if key in seen_years_months:
                        idx_errs["mes"] = ["Año y mes duplicados en el envío."]
                    else:
                        seen_years_months.add(key)

                casos = row.get("casos_dengue")
                if casos is not None and (not isinstance(casos, int) or casos < 0):
                    idx_errs["casos_dengue"] = ["Debe ser un entero mayor o igual a 0."]

                temp = row.get("temperatura_c")
                if temp is not None and not (-20 <= float(temp) <= 60):
                    idx_errs["temperatura_c"] = ["Temperatura fuera de rango (-20 a 60)."]

                hum = row.get("humedad_pct")
                if hum is not None and not (0 <= float(hum) <= 100):
                    idx_errs["humedad_pct"] = ["Humedad fuera de rango (0 a 100)."]

                prec = row.get("precipitacion_mm")
                if prec is not None and float(prec) < 0:
                    idx_errs["precipitacion_mm"] = ["Precipitación debe ser mayor o igual a 0."]

                if idx_errs:
                    row_errors[str(idx)] = idx_errs

            if row_errors:
                self._send_json(400, row_errors)
                return

            # Apply batch update
            casos_creados, casos_actualizados = 0, 0
            clima_creados, clima_actualizados = 0, 0

            for row in body:
                anio, mes = row["anio"], row["mes"]
                # Update casos
                if row.get("casos_dengue") is not None:
                    year_casos = db.casos_por_mes.setdefault(anio, [])
                    existing_caso = next((c for c in year_casos if c["mes"] == mes), None)
                    if existing_caso:
                        existing_caso["casos"] = row["casos_dengue"]
                        casos_actualizados += 1
                    else:
                        year_casos.append({"enfermedad": "dengue", "mes": mes, "casos": row["casos_dengue"]})
                        casos_creados += 1

                # Update clima
                if any(row.get(k) is not None for k in ("temperatura_c", "humedad_pct", "precipitacion_mm")):
                    year_clima = db.clima_por_mes.setdefault(anio, [])
                    existing_clima = next((c for c in year_clima if c["mes"] == mes), None)
                    clima_dict = {
                        "mes": mes,
                        "temperatura": row.get("temperatura_c"),
                        "humedad": row.get("humedad_pct"),
                        "precipitacion": row.get("precipitacion_mm"),
                    }
                    if existing_clima:
                        existing_clima.update(clima_dict)
                        clima_actualizados += 1
                    else:
                        year_clima.append(clima_dict)
                        clima_creados += 1

            self._send_json(201, {
                "casos": {"creados": casos_creados, "actualizados": casos_actualizados},
                "clima": {"creados": clima_creados, "actualizados": clima_actualizados},
            })
            return

        # 4.17 POST /predicciones/ 👑
        if path == "/predicciones/":
            user = self._require_admin()
            if not user:
                return
            body = self._read_json_body() or {}
            enfermedad = body.get("enfermedad", "dengue")
            anio = body.get("anio", 2026)
            mes = body.get("mes", 12)
            semanas = body.get("semanas")

            if not isinstance(semanas, list) or len(semanas) != 4 or any(not isinstance(s, (int, float)) or s < 0 for s in semanas):
                self._send_json(400, {"semanas": ["Debe contener exactamente 4 números mayores o iguales a 0."]})
                return

            total = round(float(sum(semanas)), 2)
            db.prediccion = {
                "anio": anio,
                "mes": mes,
                "semanas": semanas,
                "total": total,
                "creado_por": user["nombre"],
                "creado_en": datetime.now(timezone.utc).isoformat(),
            }

            # Generate alert if higher than previous year same month
            casos_prev = 2  # from historical fixture
            new_alert = {
                "id": db.next_alerta_id(),
                "enfermedad": enfermedad,
                "enfermedad_nombre": "Dengue [SIMULADO]",
                "anio": anio,
                "mes": mes,
                "casos_estimados": total,
                "casos_anio_anterior": casos_prev,
                "motivo": f"[SIMULADO] Se estiman {total} casos de {enfermedad} para mes {mes}/{anio}, contra {casos_prev} del periodo anterior.",
                "mensaje_publico": "",
                "estado": "pendiente",
                "revisada_por": None,
                "revisada_en": None,
                "creada_en": datetime.now(timezone.utc).isoformat(),
            }
            db.alertas.insert(0, new_alert)

            self._send_json(201, {
                "enfermedad": enfermedad,
                "anio": anio,
                "mes": mes,
                "semanas": semanas,
                "total": total,
                "alerta": {"id": new_alert["id"], "estado": "pendiente"},
            })
            return

        self._send_json(404, {"detail": "Ruta no encontrada."})

    def do_PATCH(self) -> None:
        self._current_body = None
        self._read_json_body()
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/") + "/"
        if path.startswith("/api/"):
            path = path[4:]

        # 4.14 PATCH /contenido/{id}/ 👑
        match_contenido = re.match(r"^/contenido/(\d+)/$", path)
        if match_contenido:
            user = self._require_admin()
            if not user:
                return
            cid = int(match_contenido.group(1))
            item = next((i for i in db.contenido if i["id"] == cid), None)
            if not item:
                self._send_json(404, {"detail": "Contenido no encontrado."})
                return

            body = self._read_json_body() or {}
            for field in ("tipo", "titulo", "cuerpo", "url_fuente", "imagen_url", "publicado", "enfermedad"):
                if field in body:
                    item[field] = body[field]
            self._send_json(200, item)
            return

        self._send_json(404, {"detail": "Ruta no encontrada."})

    def do_DELETE(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/") + "/"
        if path.startswith("/api/"):
            path = path[4:]

        # 4.15 DELETE /contenido/{id}/ 👑
        match_contenido = re.match(r"^/contenido/(\d+)/$", path)
        if match_contenido:
            user = self._require_admin()
            if not user:
                return
            cid = int(match_contenido.group(1))
            item = next((i for i in db.contenido if i["id"] == cid), None)
            if not item:
                self._send_json(404, {"detail": "Contenido no encontrado."})
                return
            db.contenido.remove(item)
            self._send_no_content()
            return

        self._send_json(404, {"detail": "Ruta no encontrada."})


def create_mock_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Create a threaded HTTP server for the Mock API."""
    return ThreadingHTTPServer((host, port), MockRequestHandler)


class MockServerHandle:
    """Convenience handle for starting and stopping the mock server programmatically."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.server = create_mock_server(host, port)
        self.thread: threading.Thread | None = None

    def start(self) -> MockServerHandle:
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="HACKAJAL Independent Mock API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args()

    server = create_mock_server(args.host, args.port)
    print(f"============================================================")
    print(f" HACKAJAL Mock API Server activo")
    print(f" Escuchando en: http://{args.host}:{args.port}/api/")
    print(f" Firebase Auth: http://{args.host}:{args.port}/identitytoolkit/v1/accounts:signInWithPassword")
    print(f" Usuarios de prueba:")
    print(f"   - Admin:    admin@hackajal.salud.gob.mx   (pwd: AdminPassword123!)")
    print(f"   - Consulta: consulta@hackajal.salud.gob.mx(pwd: ConsultaPassword123!)")
    print(f" Presiona Ctrl+C para detener.")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor Mock API...")
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
