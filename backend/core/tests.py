from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (
    Alerta, Contenido, EncuestaRespuesta, Enfermedad, EstadisticaCronica, Municipio,
    Organizacion, Prediccion, RegistroCasos, RegistroClima, Usuario,
)


class Base(APITestCase):
    def setUp(self):
        cache.clear()  # reinicia el límite de la encuesta entre pruebas
        org = Organizacion.objects.create(nombre="Prueba")
        self.admin = Usuario.objects.create(firebase_uid="uid-admin", organizacion=org, nombre="Admin", email="a@t.mx", rol="admin")
        self.consulta = Usuario.objects.create(firebase_uid="uid-consulta", organizacion=org, nombre="Consulta", email="c@t.mx")
        self.pv = Municipio.objects.create(clave_inegi="14067", nombre="Puerto Vallarta", region="Costa-Sierra Occidental", latitud=20.6, longitud=-105.2)
        self.ci = Municipio.objects.create(clave_inegi="14022", nombre="Cihuatlán", region="Costa Sur")
        self.dengue = Enfermedad.objects.create(clave="dengue", nombre="Dengue", tipo="transmisible")
        self.zika = Enfermedad.objects.create(clave="zika", nombre="Zika", tipo="transmisible")
        self.dm2 = Enfermedad.objects.create(clave="dm2", nombre="Diabetes tipo 2", tipo="cronica")
        self.client.force_authenticate(user=self.admin)

    def como(self, usuario):
        self.client.force_authenticate(user=usuario)


# ---------- Autenticación y permisos ----------

class AuthTests(Base):
    def test_yo(self):
        r = self.client.get("/api/yo/")
        self.assertEqual(r.data, {"nombre": "Admin", "email": "a@t.mx", "rol": "admin", "organizacion": "Prueba"})

    def test_privadas_sin_sesion_401(self):
        self.como(None)
        for ruta in ["/api/yo/", "/api/mapa/?enfermedad=dengue", "/api/estadisticas/", "/api/alertas/"]:
            self.assertEqual(self.client.get(ruta).status_code, 401, ruta)

    def test_consulta_no_puede_escribir_403(self):
        self.como(self.consulta)
        self.assertEqual(self.client.post("/api/cargas/", [], format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/predicciones/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/alertas/").status_code, 200)  # pero sí puede ver

    def test_publicas_sin_sesion(self):
        self.como(None)
        for ruta in ["/api/municipios/", "/api/enfermedades/", "/api/alertas-publicas/", "/api/contenido/"]:
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)


@override_settings(FIREBASE_PROJECT_ID="proyecto-prueba")  # no depende del .env de quien corre las pruebas
class FirebaseTokenTests(Base):
    def get_con_token(self, datos=None, error=None):
        self.como(None)
        with patch("core.authentication.id_token.verify_firebase_token", return_value=datos, side_effect=error):
            return self.client.get("/api/yo/", HTTP_AUTHORIZATION="Bearer abc")

    def test_token_valido(self):
        r = self.get_con_token({"sub": "uid-admin", "iss": "https://securetoken.google.com/proyecto-prueba"})
        self.assertEqual(r.status_code, 200)

    def test_token_invalido_o_ajeno(self):
        self.assertEqual(self.get_con_token(error=ValueError()).status_code, 401)
        self.assertEqual(self.get_con_token({"sub": "uid-admin", "iss": "https://securetoken.google.com/otro"}).status_code, 401)
        self.assertEqual(self.get_con_token({"sub": "nadie", "iss": "https://securetoken.google.com/proyecto-prueba"}).status_code, 401)


# ---------- Carga ----------

class CargaTests(Base):
    def fila(self, **cambios):
        base = {"anio": 2026, "mes": 10, "casos_dengue": 14, "casos_zika": 0,
                "temperatura_c": 29.5, "humedad_pct": 72, "precipitacion_mm": None}
        return {**base, **cambios}

    def test_crea_casos_y_clima(self):
        r = self.client.post("/api/cargas/", [self.fila(), self.fila(mes=11)], format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data, {"casos": {"creados": 4, "actualizados": 0}, "clima": {"creados": 2, "actualizados": 0}})
        self.assertEqual(RegistroCasos.objects.get(enfermedad=self.dengue, mes=10).cargado_por, self.admin)
        self.assertIsNone(RegistroClima.objects.get(mes=10).precipitacion)

    def test_actualiza_sin_borrar_lo_vacio(self):
        self.client.post("/api/cargas/", [self.fila()], format="json")
        r = self.client.post("/api/cargas/", [self.fila(casos_dengue=20, casos_zika=None, temperatura_c=None, humedad_pct=None, precipitacion_mm=80)], format="json")
        self.assertEqual(r.data, {"casos": {"creados": 0, "actualizados": 1}, "clima": {"creados": 0, "actualizados": 1}})
        self.assertEqual(RegistroCasos.objects.get(enfermedad=self.dengue).casos, 20)
        self.assertEqual(RegistroCasos.objects.get(enfermedad=self.zika).casos, 0)  # vacío = no se tocó
        clima = RegistroClima.objects.get()
        self.assertEqual((clima.temperatura, clima.precipitacion), (29.5, 80))

    def test_acepta_formatos_de_excel(self):
        r = self.client.post("/api/cargas/", [self.fila(casos_dengue=14.0, casos_zika="")], format="json")
        self.assertEqual(r.status_code, 201)

    def test_todo_o_nada(self):
        r = self.client.post("/api/cargas/", [self.fila(), self.fila(mes=13, casos_dengue=1.5, casos_xyz=3)], format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data[1]), {"mes", "casos_dengue", "casos_xyz"})  # reporta todos los errores de la fila
        self.assertEqual(RegistroCasos.objects.count(), 0)

    def test_filas_repetidas_y_vacias(self):
        r = self.client.post("/api/cargas/", [self.fila(), self.fila()], format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn(1, r.data)
        r = self.client.post("/api/cargas/", [{"anio": 2026, "mes": 1}], format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.post("/api/cargas/", [], format="json").status_code, 400)


# ---------- Predicciones y alertas ----------

class PrediccionAlertaTests(Base):
    def predecir(self, semanas, mes=12, enfermedad="dengue"):
        datos = {"enfermedad": enfermedad, "anio": 2026, "mes": mes, "semanas": semanas}
        return self.client.post("/api/predicciones/", datos, format="json")

    def casos_2025(self, casos, mes=12):
        RegistroCasos.objects.create(enfermedad=self.dengue, anio=2025, mes=mes, casos=casos, cargado_por=self.admin)

    def test_sube_genera_alerta(self):
        self.casos_2025(2)
        r = self.predecir([1.2, 1.96, 0.8, 0.5])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["total"], 4.46)
        self.assertEqual(r.data["alerta"]["estado"], "pendiente")
        self.assertIn("región costera para diciembre 2026, contra 2 en diciembre 2025", Alerta.objects.get().motivo)
        self.assertEqual(Prediccion.objects.count(), 4)

    def test_no_sube_no_hay_alerta(self):
        self.casos_2025(10)
        r = self.predecir([1, 1, 1, 1])
        self.assertIsNone(r.data["alerta"])
        self.assertEqual(Alerta.objects.count(), 0)

    def test_sin_dato_anterior_si_genera(self):
        self.predecir([0.1, 0, 0, 0])
        self.assertIn("Sin datos de diciembre 2025", Alerta.objects.get().motivo)

    def test_volver_a_correr_actualiza_o_quita_la_pendiente(self):
        self.casos_2025(2)
        self.predecir([1, 1, 1, 1])
        self.predecir([2, 2, 2, 2])
        self.assertEqual(Alerta.objects.get().casos_estimados, 8)  # se actualizó, no se duplicó
        self.predecir([0, 0, 0, 0.5])
        self.assertEqual(Alerta.objects.count(), 0)  # ya no sube: la pendiente sin revisar se quita

    def test_confirmada_no_se_duplica(self):
        self.casos_2025(2)
        self.predecir([1, 1, 1, 1])
        alerta = Alerta.objects.get()
        self.client.post(f"/api/alertas/{alerta.id}/confirmar/", {"mensaje_publico": "Usa repelente"}, format="json")
        self.predecir([3, 3, 3, 3])
        self.assertEqual(Alerta.objects.count(), 1)

    def test_validaciones(self):
        self.assertEqual(self.predecir([1, 2, 3]).status_code, 400)          # faltan semanas
        self.assertEqual(self.predecir([1, 2, 3, -1]).status_code, 400)      # negativo
        self.assertEqual(self.predecir([1, 1, 1, 1], enfermedad="xyz").status_code, 400)

    def test_get_ultima_prediccion(self):
        self.predecir([1, 1, 1, 1], mes=11)
        self.predecir([2, 2, 2, 2], mes=12)
        r = self.client.get("/api/predicciones/?enfermedad=dengue")
        self.assertEqual((r.data["prediccion"]["mes"], r.data["prediccion"]["total"]), (12, 8))
        self.assertEqual(self.client.get("/api/predicciones/").status_code, 400)

    def test_confirmar_descartar_y_publicas(self):
        hoy = timezone.localdate()
        vigente = Alerta.objects.create(enfermedad=self.dengue, anio=hoy.year + 1, mes=1, casos_estimados=5, motivo="m")
        vencida = Alerta.objects.create(enfermedad=self.zika, anio=hoy.year - 1, mes=1, casos_estimados=5, motivo="m")

        self.assertEqual(self.client.post(f"/api/alertas/{vigente.id}/confirmar/", {}, format="json").status_code, 400)  # falta mensaje
        r = self.client.post(f"/api/alertas/{vigente.id}/confirmar/", {"mensaje_publico": "Elimina criaderos"}, format="json")
        self.assertEqual((r.status_code, r.data["estado"], r.data["revisada_por"]), (200, "confirmada", "Admin"))
        self.assertEqual(self.client.post(f"/api/alertas/{vigente.id}/descartar/").status_code, 409)  # ya revisada
        self.client.post(f"/api/alertas/{vencida.id}/confirmar/", {"mensaje_publico": "x"}, format="json")

        self.como(None)
        publicas = self.client.get("/api/alertas-publicas/").data
        self.assertEqual([a["id"] for a in publicas], [vigente.id])  # la de un mes pasado no sale
        self.assertNotIn("motivo", publicas[0])

    def test_lista_alertas_filtra(self):
        Alerta.objects.create(enfermedad=self.dengue, anio=2026, mes=12, casos_estimados=5, motivo="m")
        self.assertEqual(len(self.client.get("/api/alertas/?estado=pendiente&enfermedad=dengue").data), 1)
        self.assertEqual(len(self.client.get("/api/alertas/?enfermedad=zika").data), 0)
        self.assertEqual(self.client.get("/api/alertas/?estado=otra").status_code, 400)
        self.assertEqual(self.client.post("/api/alertas/999/descartar/").status_code, 404)


# ---------- Mapa y estadísticas ----------

class MapaEstadisticasTests(Base):
    def test_mapa(self):
        RegistroCasos.objects.create(enfermedad=self.dengue, anio=2025, mes=12, casos=2, cargado_por=self.admin)
        self.client.post("/api/predicciones/", {"enfermedad": "dengue", "anio": 2026, "mes": 12, "semanas": [1, 1, 1, 1]}, format="json")
        r = self.client.get("/api/mapa/?enfermedad=dengue")
        self.assertEqual((r.data["prediccion"]["total"], r.data["casos_anio_anterior"], r.data["alerta"]["estado"]), (4, 2, "pendiente"))
        self.assertEqual([m["clave_inegi"] for m in r.data["municipios"]], ["14022", "14067"])
        self.assertEqual(self.client.get("/api/mapa/").status_code, 400)

    def test_mapa_sin_prediccion(self):
        r = self.client.get("/api/mapa/?enfermedad=zika")
        self.assertEqual((r.data["prediccion"], r.data["alerta"]), (None, None))

    def test_estadisticas_generales(self):
        for mes, casos in ((1, 3), (2, 5)):
            RegistroCasos.objects.create(enfermedad=self.zika, anio=2026, mes=mes, casos=casos, cargado_por=self.admin)
        RegistroCasos.objects.create(enfermedad=self.dengue, anio=2026, mes=1, casos=9, cargado_por=self.admin)
        RegistroClima.objects.create(anio=2026, mes=1, temperatura=28, cargado_por=self.admin)

        r = self.client.get("/api/estadisticas/?enfermedad=zika&anio=2026")
        self.assertEqual(r.data["casos_por_mes"], [{"enfermedad": "zika", "mes": 1, "casos": 3}, {"enfermedad": "zika", "mes": 2, "casos": 5}])
        self.assertEqual(r.data["clima_por_mes"][0]["temperatura"], 28)
        self.assertIsNone(r.data["cronicas"])  # zika no es crónica

        r = self.client.get("/api/estadisticas/?anio=2026")  # sin enfermedad: todas
        self.assertEqual(len(r.data["casos_por_mes"]), 3)

    def test_estadisticas_cronicas_y_errores(self):
        EstadisticaCronica.objects.create(enfermedad=self.dm2, indicador="incidencia", ambito="estado", anio=2025, valor=496.65, unidad="tasa_100k", fuente="DGE")
        r = self.client.get("/api/estadisticas/?enfermedad=dm2&municipio=14067")
        self.assertEqual(r.data["cronicas"][0]["valor"], 496.65)
        self.assertEqual(self.client.get("/api/estadisticas/?enfermedad=xyz").status_code, 400)
        self.assertEqual(self.client.get("/api/estadisticas/?municipio=99999").status_code, 400)
        self.assertEqual(self.client.get("/api/estadisticas/?anio=dos").status_code, 400)


# ---------- Contenido y encuesta ----------

class ContenidoEncuestaTests(Base):
    def test_contenido_borrador_y_publicado(self):
        r = self.client.post("/api/contenido/", {"tipo": "articulo", "enfermedad": "dengue", "titulo": "T", "cuerpo": "C"}, format="json")
        self.assertEqual((r.status_code, r.data["autor"], r.data["publicado"]), (201, "Admin", False))
        id_ = r.data["id"]

        self.como(None)
        self.assertEqual(self.client.get("/api/contenido/").data, [])               # borrador oculto
        self.assertEqual(self.client.get(f"/api/contenido/{id_}/").status_code, 404)
        self.assertEqual(self.client.post("/api/contenido/", {}, format="json").status_code, 401)

        self.como(self.admin)
        self.client.patch(f"/api/contenido/{id_}/", {"publicado": True}, format="json")
        self.como(None)
        self.assertEqual(len(self.client.get("/api/contenido/?tipo=articulo&enfermedad=dengue").data), 1)
        self.assertEqual(self.client.get("/api/contenido/?enfermedad=zika").data, [])

    def test_contenido_sin_autor_ni_enfermedad(self):
        Contenido.objects.create(tipo="prevencion", titulo="Fija", cuerpo="x", publicado=True)
        r = self.client.get("/api/contenido/")
        self.assertEqual((r.data[0]["autor"], r.data[0]["enfermedad"]), (None, None))

    def test_encuesta(self):
        self.como(None)
        r = self.client.post("/api/encuesta/", {"municipio": "14022", "respuestas": {"p1": "si"}, "consentimiento": True}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.post("/api/encuesta/", {"municipio": "14022", "respuestas": {"p1": "si"}, "consentimiento": False}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/encuesta/", {"municipio": "14022", "respuestas": {}, "consentimiento": True}, format="json").status_code, 400)

        self.como(self.consulta)
        r = self.client.get("/api/estadisticas/encuesta/")
        self.assertEqual((r.data["total"], r.data["por_municipio"][0]["municipio__clave_inegi"]), (1, "14022"))

    def test_encuesta_limite_por_ip(self):
        self.como(None)
        datos = {"municipio": "14022", "respuestas": {"p1": "si"}, "consentimiento": True}
        codigos = [self.client.post("/api/encuesta/", datos, format="json").status_code for _ in range(21)]
        self.assertEqual(codigos[-1], 429)
        self.assertEqual(EncuestaRespuesta.objects.count(), 20)


# ---------- Administración de usuarios ----------

class UsuariosTests(Base):
    def firebase_ok(self, uid="uid-nuevo"):
        respuesta = type("R", (), {"ok": True, "content": b"x", "json": lambda self: {"localId": uid}})()
        return patch("core.servicios.requests.post", return_value=respuesta)

    def nuevo(self, **extra):
        return {"nombre": "Ana", "email": "Ana@t.mx", "password": "secreta1", "rol": "consulta",
                "organizacion": self.admin.organizacion_id, **extra}

    def test_crear_usuario(self):
        with self.settings(FIREBASE_API_KEY="k"), self.firebase_ok() as firebase:
            r = self.client.post("/api/usuarios/", self.nuevo(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(firebase.call_args.kwargs["json"]["email"], "ana@t.mx")
        u = Usuario.objects.get(firebase_uid="uid-nuevo")
        self.assertEqual((u.email, u.rol), ("ana@t.mx", "consulta"))
        self.assertNotIn("password", r.data)

    def test_correo_repetido_no_llama_a_firebase(self):
        with self.settings(FIREBASE_API_KEY="k"), self.firebase_ok() as firebase:
            r = self.client.post("/api/usuarios/", self.nuevo(email="C@t.mx"), format="json")
        self.assertEqual(r.status_code, 400)
        firebase.assert_not_called()

    def test_error_de_firebase(self):
        malo = type("R", (), {"ok": False, "status_code": 400, "content": b"x",
                              "json": lambda self: {"error": {"message": "EMAIL_EXISTS"}}})()
        with self.settings(FIREBASE_API_KEY="k"), patch("core.servicios.requests.post", return_value=malo):
            r = self.client.post("/api/usuarios/", self.nuevo(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)
        self.assertFalse(Usuario.objects.filter(email="ana@t.mx").exists())

    def test_sin_api_key_502(self):
        with self.settings(FIREBASE_API_KEY=None):
            self.assertEqual(self.client.post("/api/usuarios/", self.nuevo(), format="json").status_code, 502)

    def test_listar_cambiar_rol_y_eliminar(self):
        self.assertEqual(len(self.client.get("/api/usuarios/").data), 2)
        self.assertEqual(self.client.get("/api/organizaciones/").data[0]["nombre"], "Prueba")
        r = self.client.patch(f"/api/usuarios/{self.consulta.pk}/", {"rol": "admin", "email": "x@x.mx"}, format="json")
        self.assertEqual((r.status_code, r.data["rol"], r.data["email"]), (200, "admin", "c@t.mx"))
        self.assertEqual(self.client.delete(f"/api/usuarios/{self.consulta.pk}/").status_code, 204)
        self.assertFalse(Usuario.objects.filter(pk=self.consulta.pk).exists())

    def test_no_puede_tocarse_a_si_mismo(self):
        self.assertEqual(self.client.patch(f"/api/usuarios/{self.admin.pk}/", {"rol": "consulta"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/usuarios/{self.admin.pk}/").status_code, 400)

    def test_consulta_no_administra_usuarios(self):
        self.como(self.consulta)
        for r in [self.client.get("/api/usuarios/"), self.client.get("/api/organizaciones/"),
                  self.client.post("/api/usuarios/", self.nuevo(), format="json"),
                  self.client.delete(f"/api/usuarios/{self.admin.pk}/")]:
            self.assertEqual(r.status_code, 403)
