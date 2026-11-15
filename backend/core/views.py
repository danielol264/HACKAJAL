from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import (
    Alerta, Contenido, EncuestaRespuesta, Enfermedad, EstadisticaCronica, Municipio,
    Organizacion, Prediccion, RegistroCasos, RegistroClima, Usuario,
)
from .permissions import EsAdmin, EsUsuario
from .serializers import (
    AlertaPublicaSerializer, AlertaSerializer, CargaFilaSerializer, ConfirmarAlertaSerializer,
    ContenidoSerializer, EncuestaSerializer, EnfermedadSerializer, MunicipioSerializer,
    OrganizacionSerializer, PrediccionEntradaSerializer, UsuarioAdminSerializer, UsuarioCrearSerializer,
    UsuarioSerializer,
)
from .servicios import casos_anio_anterior, crear_cuenta_firebase, evaluar_alerta, ultima_prediccion


# ---------- Ayudantes para los filtros por URL (?enfermedad=dengue&municipio=14067) ----------

def buscar_por_clave(modelo, campo, valor, nombre):
    """Busca por clave; si no existe responde 400 en lugar de una lista vacía engañosa."""
    try:
        return modelo.objects.get(**{campo: valor})
    except modelo.DoesNotExist:
        raise ValidationError({nombre: [f"{nombre} '{valor}' no existe."]})


def filtro_enfermedad(request, obligatorio=False):
    clave = request.query_params.get("enfermedad")
    if not clave:
        if obligatorio:
            raise ValidationError({"enfermedad": ["Este parámetro es obligatorio."]})
        return None
    return buscar_por_clave(Enfermedad, "clave", clave, "enfermedad")


def filtro_municipio(request, obligatorio=False):
    clave = request.query_params.get("municipio")
    if not clave:
        if obligatorio:
            raise ValidationError({"municipio": ["Este parámetro es obligatorio."]})
        return None
    return buscar_por_clave(Municipio, "clave_inegi", clave, "municipio")


def errores_por_repetidos(filas, clave_de):
    """Marca las filas que repiten la misma clave dentro del mismo envío."""
    vistas, errores = {}, {}
    for i, fila in enumerate(filas):
        clave = clave_de(fila)
        if clave in vistas:
            errores[i] = {"non_field_errors": [f"Repite los datos de la fila {vistas[clave]}."]}
        else:
            vistas[clave] = i
    return errores


# ---------- Autenticación ----------

class YoView(APIView):
    """GET /api/yo/ — quién inició sesión: nombre, correo, rol y organización."""

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


# ---------- Tarjeta 19: carga con la plantilla mensual ----------

CLIMA = {"temperatura_c": "temperatura", "humedad_pct": "humedad", "precipitacion_mm": "precipitacion"}


class CargaView(APIView):
    """POST /api/cargas/ — filas de la plantilla (un mes de la región por fila). Todo o nada; un mes repetido se actualiza."""

    permission_classes = [EsAdmin]

    def post(self, request):
        enfermedades = {e.clave: e for e in Enfermedad.objects.all()}
        serializer = CargaFilaSerializer(
            data=request.data, many=True, allow_empty=False, context={"enfermedades": enfermedades}
        )
        serializer.is_valid(raise_exception=True)
        filas = serializer.validated_data

        repetidas = errores_por_repetidos(filas, lambda f: (f["anio"], f["mes"]))
        if repetidas:
            return Response(repetidas, status=status.HTTP_400_BAD_REQUEST)

        conteo = {"casos": {"creados": 0, "actualizados": 0}, "clima": {"creados": 0, "actualizados": 0}}
        with transaction.atomic():
            for fila in filas:
                anio, mes = fila["anio"], fila["mes"]

                for enfermedad, casos in fila["casos"].items():
                    _, creado = RegistroCasos.objects.update_or_create(
                        enfermedad=enfermedad, anio=anio, mes=mes,
                        defaults={"casos": casos, "cargado_por": request.user},
                    )
                    conteo["casos"]["creados" if creado else "actualizados"] += 1

                # solo se escriben los datos de clima que vienen; los vacíos no borran lo anterior
                clima = {campo: fila[col] for col, campo in CLIMA.items() if fila.get(col) is not None}
                if clima:
                    _, creado = RegistroClima.objects.update_or_create(
                        anio=anio, mes=mes, defaults={**clima, "cargado_por": request.user},
                    )
                    conteo["clima"]["creados" if creado else "actualizados"] += 1

        return Response(conteo, status=status.HTTP_201_CREATED)


# ---------- Tarjeta 20: catálogos, mapa y estadísticas ----------

class MunicipiosView(generics.ListAPIView):
    """GET /api/municipios/ — público."""

    permission_classes = [AllowAny]
    serializer_class = MunicipioSerializer
    queryset = Municipio.objects.order_by("nombre")


class EnfermedadesView(generics.ListAPIView):
    """GET /api/enfermedades/ — público."""

    permission_classes = [AllowAny]
    serializer_class = EnfermedadSerializer
    queryset = Enfermedad.objects.order_by("nombre")


class MapaView(APIView):
    """GET /api/mapa/?enfermedad=dengue — la predicción y la alerta de la región, más los municipios a pintar."""

    def get(self, request):
        enfermedad = filtro_enfermedad(request, obligatorio=True)
        prediccion = ultima_prediccion(enfermedad)
        anterior = alerta = None
        if prediccion:
            anterior = casos_anio_anterior(enfermedad, prediccion["anio"], prediccion["mes"])
            alerta = (
                Alerta.objects.filter(enfermedad=enfermedad, anio=prediccion["anio"], mes=prediccion["mes"])
                .exclude(estado="descartada")
                .order_by("-creada_en")
                .first()
            )
        return Response({
            "enfermedad": enfermedad.clave,
            "prediccion": prediccion,
            "casos_anio_anterior": anterior,
            "alerta": {"id": alerta.id, "estado": alerta.estado} if alerta else None,
            "municipios": MunicipioSerializer(Municipio.objects.order_by("nombre"), many=True).data,
        })


class EstadisticasView(APIView):
    """
    GET /api/estadisticas/?enfermedad=dengue&anio=2026&municipio=14067
    Todo es opcional. Casos y clima son de la región; "municipio" solo filtra las crónicas.
    """

    def get(self, request):
        enfermedad = filtro_enfermedad(request)
        municipio = filtro_municipio(request)
        try:
            anio = int(request.query_params.get("anio", timezone.localdate().year))
        except ValueError:
            raise ValidationError({"anio": ["Debe ser un número, ej. 2026."]})

        casos = RegistroCasos.objects.filter(anio=anio)
        if enfermedad:
            casos = casos.filter(enfermedad=enfermedad)
        casos_por_mes = [
            {"enfermedad": fila["enfermedad__clave"], "mes": fila["mes"], "casos": fila["casos"]}
            for fila in casos.order_by("enfermedad__clave", "mes").values("enfermedad__clave", "mes", "casos")
        ]

        clima_por_mes = list(
            RegistroClima.objects.filter(anio=anio).order_by("mes").values("mes", "temperatura", "humedad", "precipitacion")
        )

        prediccion = ultima_prediccion(enfermedad) if enfermedad else None

        cronicas = None
        if enfermedad and enfermedad.tipo == "cronica":
            filas = EstadisticaCronica.objects.filter(enfermedad=enfermedad)
            if municipio:
                filas = filas.filter(Q(municipio=municipio) | Q(municipio__isnull=True))
            # no se filtra por año: las crónicas son anuales y pueden ser de otro año (ej. DGE 2025)
            cronicas = list(
                filas.order_by("indicador", "anio", "id").values(
                    "indicador", "ambito", "municipio__clave_inegi", "region", "anio", "sexo",
                    "grupo_edad", "institucion", "valor", "unidad", "fuente",
                )
            )

        return Response({
            "filtros": {
                "enfermedad": enfermedad.clave if enfermedad else None,
                "municipio": municipio.clave_inegi if municipio else None,
                "anio": anio,
            },
            "casos_por_mes": casos_por_mes,
            "clima_por_mes": clima_por_mes,
            "prediccion": prediccion,
            "cronicas": cronicas,
        })


class EstadisticasEncuestaView(APIView):
    """GET /api/estadisticas/encuesta/ — cuántas respuestas hay por municipio."""

    def get(self, request):
        por_municipio = list(
            EncuestaRespuesta.objects.values("municipio__clave_inegi", "municipio__nombre")
            .annotate(respuestas=Count("id"))
            .order_by("-respuestas")
        )
        total = sum(fila["respuestas"] for fila in por_municipio)
        return Response({"total": total, "por_municipio": por_municipio})


# ---------- Tarjeta 21: predicciones y alertas ----------

class PrediccionesView(APIView):
    """
    POST /api/predicciones/ — resultado del modelo para la región (admin). Guarda y evalúa la alerta.
    GET  /api/predicciones/?enfermedad=dengue — la última predicción (con sesión).
    """

    def get_permissions(self):
        return [EsAdmin()] if self.request.method == "POST" else [EsUsuario()]

    def get(self, request):
        enfermedad = filtro_enfermedad(request, obligatorio=True)
        return Response({"prediccion": ultima_prediccion(enfermedad)})

    def post(self, request):
        serializer = PrediccionEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enfermedad, anio, mes, semanas = (serializer.validated_data[k] for k in ("enfermedad", "anio", "mes", "semanas"))

        with transaction.atomic():
            Prediccion.objects.bulk_create([
                Prediccion(
                    enfermedad=enfermedad, anio=anio, mes=mes, semana=numero,
                    casos_estimados=valor, creado_por=request.user,
                )
                for numero, valor in enumerate(semanas, start=1)
            ])
            total = round(sum(semanas), 2)
            alerta = evaluar_alerta(enfermedad, anio, mes, total)

        return Response({
            "enfermedad": enfermedad.clave,
            "anio": anio,
            "mes": mes,
            "semanas": semanas,
            "total": total,
            "alerta": {"id": alerta.id, "estado": alerta.estado} if alerta else None,
        }, status=status.HTTP_201_CREATED)


class AlertasView(generics.ListAPIView):
    """GET /api/alertas/?estado=pendiente&enfermedad=dengue — para la organización."""

    serializer_class = AlertaSerializer

    def get_queryset(self):
        alertas = Alerta.objects.select_related("enfermedad", "revisada_por").order_by("-creada_en")
        estado = self.request.query_params.get("estado")
        if estado:
            if estado not in dict(Alerta.ESTADOS):
                raise ValidationError({"estado": ["Usa pendiente, confirmada o descartada."]})
            alertas = alertas.filter(estado=estado)
        enfermedad = filtro_enfermedad(self.request)
        if enfermedad:
            alertas = alertas.filter(enfermedad=enfermedad)
        return alertas


class RevisarAlertaView(APIView):
    """Base para confirmar o descartar: solo admin y solo si sigue pendiente."""

    permission_classes = [EsAdmin]
    nuevo_estado = None

    def aplicar(self, alerta, request):
        pass

    def post(self, request, pk):
        with transaction.atomic():
            alerta = Alerta.objects.select_for_update().filter(pk=pk).first()  # evita que dos la revisen a la vez
            if alerta is None:
                return Response({"detail": "La alerta no existe."}, status=status.HTTP_404_NOT_FOUND)
            if alerta.estado != "pendiente":
                return Response(
                    {"detail": f"La alerta ya está {alerta.estado}."}, status=status.HTTP_409_CONFLICT
                )
            self.aplicar(alerta, request)
            alerta.estado = self.nuevo_estado
            alerta.revisada_por = request.user
            alerta.revisada_en = timezone.now()
            alerta.save()
        return Response(AlertaSerializer(alerta).data)


class ConfirmarAlertaView(RevisarAlertaView):
    """POST /api/alertas/{id}/confirmar/ — body: {"mensaje_publico": "..."}. Se publica en el portal."""

    nuevo_estado = "confirmada"

    def aplicar(self, alerta, request):
        datos = ConfirmarAlertaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        alerta.mensaje_publico = datos.validated_data["mensaje_publico"]


class DescartarAlertaView(RevisarAlertaView):
    """POST /api/alertas/{id}/descartar/ — no se publica."""

    nuevo_estado = "descartada"


class AlertasPublicasView(generics.ListAPIView):
    """GET /api/alertas-publicas/ — público. Solo confirmadas y del mes actual en adelante."""

    permission_classes = [AllowAny]
    serializer_class = AlertaPublicaSerializer

    def get_queryset(self):
        hoy = timezone.localdate()
        return (
            Alerta.objects.filter(estado="confirmada")
            .filter(Q(anio__gt=hoy.year) | Q(anio=hoy.year, mes__gte=hoy.month))  # las de meses pasados ya no aplican
            .select_related("enfermedad")
            .order_by("anio", "mes")
        )


# ---------- Tarjeta 22: contenido y encuesta ----------

class ContenidoViewSet(viewsets.ModelViewSet):
    """
    GET    /api/contenido/?tipo=prevencion&enfermedad=dm2  público (sin sesión solo ve lo publicado)
    GET    /api/contenido/{id}/                            público
    POST   /api/contenido/                                 admin
    PATCH  /api/contenido/{id}/                            admin
    DELETE /api/contenido/{id}/                            admin
    """

    serializer_class = ContenidoSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):
        return [AllowAny()] if self.action in ("list", "retrieve") else [EsAdmin()]

    def get_queryset(self):
        contenido = Contenido.objects.select_related("enfermedad", "autor").order_by("-fecha")
        if not isinstance(self.request.user, Usuario):
            contenido = contenido.filter(publicado=True)  # los borradores solo los ve la organización
        tipo = self.request.query_params.get("tipo")
        if tipo:
            contenido = contenido.filter(tipo=tipo)
        enfermedad = self.request.query_params.get("enfermedad")
        if enfermedad:
            contenido = contenido.filter(enfermedad__clave=enfermedad)
        return contenido

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


class EncuestaView(generics.CreateAPIView):
    """POST /api/encuesta/ — público y anónimo. Limitado por IP para evitar spam."""

    permission_classes = [AllowAny]
    serializer_class = EncuestaSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "encuesta"

# ---------- Administración de usuarios (solo admin) ----------

class OrganizacionesView(generics.ListAPIView):
    """GET /api/organizaciones/ — para elegir la organización del usuario nuevo."""
    permission_classes = [EsAdmin]
    serializer_class = OrganizacionSerializer
    queryset = Organizacion.objects.order_by("nombre")


class UsuariosView(APIView):
    """
    GET  /api/usuarios/ — todos los usuarios.
    POST /api/usuarios/ — crea la cuenta en Firebase y el usuario en la base.
    """
    permission_classes = [EsAdmin]

    def get(self, request):
        usuarios = Usuario.objects.select_related("organizacion").order_by("nombre")
        return Response(UsuarioAdminSerializer(usuarios, many=True).data)

    def post(self, request):
        datos = UsuarioCrearSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        d = datos.validated_data
        uid = crear_cuenta_firebase(d["email"], d["password"])
        usuario = Usuario.objects.create(
            firebase_uid=uid, nombre=d["nombre"], email=d["email"], rol=d["rol"], organizacion=d["organizacion"],
        )
        return Response(UsuarioAdminSerializer(usuario).data, status=status.HTTP_201_CREATED)


class UsuarioDetalleView(APIView):
    """
    PATCH  /api/usuarios/<id>/ — cambia rol u organización.
    DELETE /api/usuarios/<id>/ — le quita el acceso (la cuenta de Firebase queda, pero /yo/ ya no la reconoce).
    Nadie puede cambiarse el rol ni borrarse a sí mismo, para no dejar el sistema sin admin.
    """
    permission_classes = [EsAdmin]

    def objeto(self, request, pk):
        usuario = generics.get_object_or_404(Usuario.objects.select_related("organizacion"), pk=pk)
        if usuario.pk == request.user.pk:
            raise ValidationError({"detail": "No puedes cambiar tu propio rol ni eliminar tu propia cuenta."})
        return usuario

    def patch(self, request, pk):
        serializer = UsuarioAdminSerializer(self.objeto(request, pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        self.objeto(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
