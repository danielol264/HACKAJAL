"""Comprehensive test suite for the HACKAJAL Independent Mock API server.

Verifies:
- All endpoints defined in API_ESCRITORIO.md
- Admin and Consulta roles and permissions
- Simulated authentication, tokens, and token expiry
- Simulated statistics, municipalities, predictions, and alerts
- Clear identification of simulated data
- High-level service integrations (AuthService, EpidemiologyService, AlertsService, ContentService)
"""
from __future__ import annotations

import socket
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from app.core.config import AppConfig
from app.core.exceptions import ApiError
from app.models.user import UserRole
from app.services.alerts_service import AlertsService
from app.services.api.client import ApiClient
from app.services.auth_service import AuthService
from app.services.content_service import ContentService
from app.services.epidemiology_service import EpidemiologyService
from desktop.mock_api.data import db
from desktop.mock_api.server import MockServerHandle
from desktop.mock_api.tokens import generate_mock_token


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockApiServerTests(unittest.TestCase):
    server_handle: MockServerHandle
    port: int
    base_url: str
    auth_url: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}/api"
        cls.auth_url = f"http://127.0.0.1:{cls.port}/identitytoolkit/v1/accounts:signInWithPassword"
        cls.server_handle = MockServerHandle("127.0.0.1", cls.port)
        cls.server_handle.start()
        # Wait until server is listening
        for _ in range(50):
            try:
                r = requests.get(f"http://127.0.0.1:{cls.port}/health/", timeout=1)
                if r.ok:
                    break
            except Exception:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server_handle.stop()

    def setUp(self) -> None:
        db.reset()
        self.config = AppConfig(
            mode="mock",
            api_base_url=self.base_url,
            firebase_login_url=self.auth_url,
            firebase_api_key="TEST_MOCK_KEY",
        )

    # -------------------------------------------------------------------------
    # Authentication & Tokens
    # -------------------------------------------------------------------------

    def test_health_check(self) -> None:
        r = requests.get(f"http://127.0.0.1:{self.port}/health/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("mock"))

    def test_login_invalid_credentials_returns_400(self) -> None:
        r = requests.post(self.auth_url, json={"email": "wrong@correo.com", "password": "bad"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["message"], "INVALID_LOGIN_CREDENTIALS")

    def test_login_admin_success(self) -> None:
        r = requests.post(self.auth_url, json={"email": "admin@hackajal.salud.gob.mx", "password": "AdminPassword123!"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("idToken", data)
        self.assertEqual(data["email"], "admin@hackajal.salud.gob.mx")

    def test_login_consulta_success(self) -> None:
        r = requests.post(self.auth_url, json={"email": "consulta@hackajal.salud.gob.mx", "password": "ConsultaPassword123!"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("idToken", data)
        self.assertEqual(data["email"], "consulta@hackajal.salud.gob.mx")

    def test_missing_token_on_protected_endpoint_returns_401(self) -> None:
        r = requests.get(f"{self.base_url}/yo/")
        self.assertEqual(r.status_code, 401)
        self.assertIn("detail", r.json())

    def test_invalid_token_returns_401(self) -> None:
        r = requests.get(f"{self.base_url}/yo/", headers={"Authorization": "Bearer token-invalido"})
        self.assertEqual(r.status_code, 401)

    def test_expired_token_returns_401(self) -> None:
        expired_token = generate_mock_token("admin@hackajal.salud.gob.mx", "admin", expires_in_seconds=-10)
        r = requests.get(f"{self.base_url}/yo/", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(r.status_code, 401)

    def test_unregistered_user_in_system_returns_401_on_yo(self) -> None:
        r_login = requests.post(self.auth_url, json={"email": "noregistrado@hackajal.salud.gob.mx", "password": "Password123!"})
        self.assertEqual(r_login.status_code, 200)
        token = r_login.json()["idToken"]

        r_yo = requests.get(f"{self.base_url}/yo/", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r_yo.status_code, 401)
        self.assertIn("Tu cuenta no tiene acceso", r_yo.json()["detail"])

    # -------------------------------------------------------------------------
    # Public Endpoints (🔓) & Simulated Data Identification
    # -------------------------------------------------------------------------

    def test_get_municipios_public_and_marked_simulated(self) -> None:
        r = requests.get(f"{self.base_url}/municipios/")
        self.assertEqual(r.status_code, 200)
        municipios = r.json()
        self.assertEqual(len(municipios), 14)

        # Verify identification of simulated data
        self.assertEqual(r.headers.get("X-Mock-Data"), "true")
        first = municipios[0]
        self.assertIn("clave_inegi", first)
        self.assertIn("nombre", first)
        self.assertIn("[SIMULADO]", first["nombre"])
        self.assertIn("region", first)

        # Verify Puerto Vallarta and Cihuatlán exist with valid coordinates
        pv = next((m for m in municipios if "Puerto Vallarta" in m["nombre"]), None)
        self.assertIsNotNone(pv)
        self.assertEqual(pv["clave_inegi"], "14067")
        self.assertAlmostEqual(pv["latitud"], 20.62)

    def test_get_enfermedades_public(self) -> None:
        r = requests.get(f"{self.base_url}/enfermedades/")
        self.assertEqual(r.status_code, 200)
        claves = [e["clave"] for e in r.json()]
        self.assertIn("dengue", claves)
        self.assertIn("dm2", claves)

    # -------------------------------------------------------------------------
    # Consulta Role: Read Access & Forbidden Admin Actions
    # -------------------------------------------------------------------------

    def _login_as(self, email: str, pwd: str) -> ApiClient:
        auth = AuthService(app_config=self.config)
        user = auth.login(email, pwd)
        client = auth.api_client
        return client

    def test_consulta_role_can_read_all_read_endpoints(self) -> None:
        client = self._login_as("consulta@hackajal.salud.gob.mx", "ConsultaPassword123!")

        # 4.1 /yo/
        yo = client.get("/yo/")
        self.assertEqual(yo["rol"], "consulta")
        self.assertIn("[SIMULADO]", yo["nombre"])

        # 4.4 /mapa/
        mapa = client.get("/mapa/", enfermedad="dengue")
        self.assertEqual(mapa["enfermedad"], "dengue")
        self.assertEqual(len(mapa["municipios"]), 14)
        self.assertIsNotNone(mapa["prediccion"])

        # 4.5 /estadisticas/ (dengue)
        stats = client.get("/estadisticas/", enfermedad="dengue", anio=2026)
        self.assertEqual(stats["filtros"]["enfermedad"], "dengue")
        self.assertIsInstance(stats["casos_por_mes"], list)
        self.assertIsInstance(stats["clima_por_mes"], list)
        self.assertIsNotNone(stats["prediccion"])

        # 4.5 /estadisticas/ (chronic dm2)
        cronicas = client.get("/estadisticas/", enfermedad="dm2")
        self.assertEqual(cronicas["filtros"]["enfermedad"], "dm2")
        self.assertIsNone(cronicas["casos_por_mes"])
        self.assertIsInstance(cronicas["cronicas"], list)

        # 4.6 /estadisticas/encuesta/
        encuesta = client.get("/estadisticas/encuesta/")
        self.assertIn("total", encuesta)
        self.assertIsInstance(encuesta["por_municipio"], list)

        # 4.7 /predicciones/
        pred = client.get("/predicciones/", enfermedad="dengue")
        self.assertEqual(pred["prediccion"]["anio"], 2026)
        self.assertEqual(len(pred["prediccion"]["semanas"]), 4)

        # 4.8 /alertas/
        alertas = client.get("/alertas/")
        self.assertIsInstance(alertas, list)
        self.assertGreaterEqual(len(alertas), 1)

        # 4.11 /contenido/
        contenido = client.get("/contenido/")
        self.assertIsInstance(contenido, list)

        # 4.12 /contenido/{id}/
        item = client.get("/contenido/1/")
        self.assertEqual(item["id"], 1)

    def test_consulta_role_forbidden_on_admin_actions(self) -> None:
        client = self._login_as("consulta@hackajal.salud.gob.mx", "ConsultaPassword123!")

        # 4.9 Confirm alert -> 403
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/3/confirmar/", {"mensaje_publico": "Mensaje"})
        self.assertEqual(ctx.exception.status, 403)

        # 4.10 Discard alert -> 403
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/3/descartar/")
        self.assertEqual(ctx.exception.status, 403)

        # 4.13 Create content -> 403
        with self.assertRaises(ApiError) as ctx:
            client.post("/contenido/", {"tipo": "nota", "titulo": "T", "cuerpo": "C"})
        self.assertEqual(ctx.exception.status, 403)

        # 4.14 Patch content -> 403
        with self.assertRaises(ApiError) as ctx:
            client.patch("/contenido/1/", {"publicado": True})
        self.assertEqual(ctx.exception.status, 403)

        # 4.15 Delete content -> 403
        with self.assertRaises(ApiError) as ctx:
            client.delete("/contenido/1/")
        self.assertEqual(ctx.exception.status, 403)

        # 4.16 Upload CSV data -> 403
        with self.assertRaises(ApiError) as ctx:
            client.post("/cargas/", [{"anio": 2026, "mes": 9, "casos_dengue": 10}])
        self.assertEqual(ctx.exception.status, 403)

        # 4.17 Create prediction -> 403
        with self.assertRaises(ApiError) as ctx:
            client.post("/predicciones/", {"enfermedad": "dengue", "anio": 2026, "mes": 12, "semanas": [1.0, 1.0, 1.0, 1.0]})
        self.assertEqual(ctx.exception.status, 403)

    # -------------------------------------------------------------------------
    # Admin Role: Full Execution of 👑 Endpoints
    # -------------------------------------------------------------------------

    def test_admin_can_confirm_and_discard_alerts(self) -> None:
        client = self._login_as("admin@hackajal.salud.gob.mx", "AdminPassword123!")

        # Confirm without required message -> 400 Bad Request
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/3/confirmar/", {"mensaje_publico": ""})
        self.assertEqual(ctx.exception.status, 400)

        # Confirm pending alert (id 3)
        confirmed = client.post("/alertas/3/confirmar/", {"mensaje_publico": "Atención preventiva en costa."})
        self.assertEqual(confirmed["estado"], "confirmada")
        self.assertEqual(confirmed["mensaje_publico"], "Atención preventiva en costa.")
        self.assertIn("Daniel", confirmed["revisada_por"])
        self.assertIsNotNone(confirmed["revisada_en"])

        # Repeat confirmation -> 409 Conflict
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/3/confirmar/", {"mensaje_publico": "Otro mensaje"})
        self.assertEqual(ctx.exception.status, 409)

        # Discard already confirmed or discarded alert -> 409 Conflict
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/2/descartar/")
        self.assertEqual(ctx.exception.status, 409)

        # Non-existent alert -> 404
        with self.assertRaises(ApiError) as ctx:
            client.post("/alertas/999/confirmar/", {"mensaje_publico": "Hola"})
        self.assertEqual(ctx.exception.status, 404)

    def test_admin_content_crud_lifecycle(self) -> None:
        client = self._login_as("admin@hackajal.salud.gob.mx", "AdminPassword123!")

        # Create content (POST /contenido/)
        created = client.post("/contenido/", {
            "tipo": "articulo",
            "enfermedad": "dengue",
            "titulo": "Nuevo reporte epidemiológico",
            "cuerpo": "Contenido detallado de vigilancia.",
            "url_fuente": "https://salud.jalisco.gob.mx",
            "publicado": False,
        })
        self.assertIn("id", created)
        self.assertEqual(created["tipo"], "articulo")
        self.assertIn("Daniel", created["autor"])
        cid = created["id"]

        # Read back (GET /contenido/{id}/)
        item = client.get(f"/contenido/{cid}/")
        self.assertEqual(item["titulo"], created["titulo"])

        # Update (PATCH /contenido/{id}/)
        updated = client.patch(f"/contenido/{cid}/", {"publicado": True})
        self.assertTrue(updated["publicado"])

        # Delete (DELETE /contenido/{id}/)
        deleted = client.delete(f"/contenido/{cid}/")
        self.assertIsNone(deleted)

        # Verify not found after deletion
        with self.assertRaises(ApiError) as ctx:
            client.get(f"/contenido/{cid}/")
        self.assertEqual(ctx.exception.status, 404)

    def test_admin_upload_cargas_validation(self) -> None:
        client = self._login_as("admin@hackajal.salud.gob.mx", "AdminPassword123!")

        # Valid payload
        valid_rows = [
            {"anio": 2026, "mes": 11, "casos_dengue": 25, "temperatura_c": 28.0, "humedad_pct": 70.0, "precipitacion_mm": 50.0},
            {"anio": 2026, "mes": 12, "casos_dengue": 10, "temperatura_c": None, "humedad_pct": None, "precipitacion_mm": None},
        ]
        res = client.post("/cargas/", valid_rows)
        self.assertIn("casos", res)
        self.assertIn("clima", res)

        # Invalid row (mes 13) returns 400 with indexed error format
        invalid_rows = [
            {"anio": 2026, "mes": 13, "casos_dengue": 10},
        ]
        with self.assertRaises(ApiError) as ctx:
            client.post("/cargas/", invalid_rows)
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("0", ctx.exception.data)

    def test_admin_create_prediction_triggers_alert(self) -> None:
        client = self._login_as("admin@hackajal.salud.gob.mx", "AdminPassword123!")

        res = client.post("/predicciones/", {
            "enfermedad": "dengue",
            "anio": 2027,
            "mes": 1,
            "semanas": [2.5, 3.0, 1.8, 2.2],
        })
        self.assertEqual(res["total"], 9.5)
        self.assertIsNotNone(res.get("alerta"))
        self.assertEqual(res["alerta"]["estado"], "pendiente")

    # -------------------------------------------------------------------------
    # High-Level Services Integration
    # -------------------------------------------------------------------------

    def test_high_level_services_with_mock_client(self) -> None:
        auth = AuthService(app_config=self.config)
        user = auth.login("admin@hackajal.salud.gob.mx", "AdminPassword123!")
        self.assertEqual(user.role, UserRole.ADMIN)

        epi_service = EpidemiologyService(auth.api_client)
        alert_service = AlertsService(auth.api_client)
        content_service = ContentService(auth.api_client)

        municipios = epi_service.get_municipios()
        self.assertEqual(len(municipios), 14)

        enfermedades = epi_service.get_enfermedades()
        self.assertGreaterEqual(len(enfermedades), 2)

        mapa = epi_service.get_mapa("dengue")
        self.assertIn("municipios", mapa)

        alertas = alert_service.get_alertas()
        self.assertGreaterEqual(len(alertas), 1)

        contenido = content_service.get_contenido()
        self.assertGreaterEqual(len(contenido), 1)


if __name__ == "__main__":
    unittest.main()
