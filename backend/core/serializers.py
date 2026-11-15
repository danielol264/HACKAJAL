from collections.abc import Mapping

from rest_framework import serializers

from .models import Alerta, Contenido, EncuestaRespuesta, Enfermedad, Municipio, Organizacion, Usuario


# ---------- Campos que reciben y devuelven claves en lugar de IDs ----------

class MunicipioPorClave(serializers.SlugRelatedField):
    """Municipio por su clave INEGI ("14067")."""

    def __init__(self, **kwargs):
        super().__init__(slug_field="clave_inegi", queryset=Municipio.objects.all(), **kwargs)


class EnfermedadPorClave(serializers.SlugRelatedField):
    """Enfermedad por su clave ("dengue")."""

    def __init__(self, **kwargs):
        super().__init__(slug_field="clave", queryset=Enfermedad.objects.all(), **kwargs)


# ---------- Catálogos y usuario ----------

class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ["clave_inegi", "nombre", "region", "latitud", "longitud"]


class EnfermedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enfermedad
        fields = ["clave", "nombre", "tipo"]


class UsuarioSerializer(serializers.ModelSerializer):
    organizacion = serializers.CharField(source="organizacion.nombre")

    class Meta:
        model = Usuario
        fields = ["nombre", "email", "rol", "organizacion"]


# ---------- Administración de usuarios (solo admin) ----------

class OrganizacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizacion
        fields = ["id", "nombre", "tipo"]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """Lista y edición: el admin puede cambiar el rol y la organización."""
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "email", "rol", "organizacion", "organizacion_nombre"]
        read_only_fields = ["id", "nombre", "email"]


class UsuarioCrearSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    rol = serializers.ChoiceField(choices=Usuario.ROLES)
    organizacion = serializers.PrimaryKeyRelatedField(queryset=Organizacion.objects.all())

    def validate_email(self, valor):
        valor = valor.lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError("Ya hay un usuario registrado con este correo.")
        return valor


# ---------- Tarjeta 19: una fila de la plantilla mensual ----------

class CargaFilaSerializer(serializers.Serializer):
    """
    Una fila de la plantilla tal cual (un mes de toda la región): anio, mes, casos_<enfermedad>..., clima.
    Columnas vacías = "no tocar". Columnas que no conoce se ignoran.
    """

    anio = serializers.IntegerField(min_value=2000, max_value=2100)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    temperatura_c = serializers.FloatField(required=False, allow_null=True, min_value=-20, max_value=60)
    humedad_pct = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=100)
    precipitacion_mm = serializers.FloatField(required=False, allow_null=True, min_value=0)

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)  # DRF responde "se esperaba un objeto"

        errores = {}
        try:
            validado = super().to_internal_value(data)
        except serializers.ValidationError as e:
            errores.update(e.detail)
            validado = {}

        # columnas casos_<clave>: una por enfermedad
        enfermedades = self.context["enfermedades"]
        casos = {}
        for columna, valor in data.items():
            if not columna.startswith("casos_") or valor in (None, ""):
                continue
            clave = columna.removeprefix("casos_")
            enfermedad = enfermedades.get(clave)
            if enfermedad is None:
                errores[columna] = [f"La enfermedad '{clave}' no existe."]
                continue
            try:
                numero = float(valor)
                if isinstance(valor, bool) or not numero.is_integer() or numero < 0:
                    raise ValueError
            except (TypeError, ValueError):
                errores[columna] = ["Debe ser un número entero de 0 o más."]
                continue
            casos[enfermedad] = int(numero)  # Excel/pandas suele mandar 14.0 en lugar de 14

        if errores:
            raise serializers.ValidationError(errores)

        clima = [validado.get(c) for c in ("temperatura_c", "humedad_pct", "precipitacion_mm")]
        if not casos and all(v is None for v in clima):
            raise serializers.ValidationError({"non_field_errors": ["La fila no trae casos ni clima."]})

        validado["casos"] = casos
        return validado


# ---------- Tarjeta 21: predicciones y alertas ----------

class PrediccionEntradaSerializer(serializers.Serializer):
    enfermedad = EnfermedadPorClave()
    anio = serializers.IntegerField(min_value=2000, max_value=2100)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    semanas = serializers.ListField(
        child=serializers.FloatField(min_value=0), min_length=4, max_length=4
    )


class AlertaSerializer(serializers.ModelSerializer):
    """Vista completa, para la organización (incluye el motivo)."""

    enfermedad = serializers.CharField(source="enfermedad.clave")
    enfermedad_nombre = serializers.CharField(source="enfermedad.nombre")
    revisada_por = serializers.CharField(source="revisada_por.nombre", allow_null=True)

    class Meta:
        model = Alerta
        fields = [
            "id", "enfermedad", "enfermedad_nombre", "anio", "mes", "casos_estimados", "casos_anio_anterior",
            "motivo", "mensaje_publico", "estado", "revisada_por", "revisada_en", "creada_en",
        ]


class AlertaPublicaSerializer(serializers.ModelSerializer):
    """Vista para la población: sin motivo interno ni quién la revisó."""

    enfermedad = serializers.CharField(source="enfermedad.clave")
    enfermedad_nombre = serializers.CharField(source="enfermedad.nombre")
    publicada_en = serializers.DateTimeField(source="revisada_en")

    class Meta:
        model = Alerta
        fields = [
            "id", "enfermedad", "enfermedad_nombre", "anio", "mes", "mensaje_publico", "publicada_en",
        ]


class ConfirmarAlertaSerializer(serializers.Serializer):
    mensaje_publico = serializers.CharField(max_length=2000)  # obligatorio y no vacío


# ---------- Tarjeta 22: contenido y encuesta ----------

class ContenidoSerializer(serializers.ModelSerializer):
    enfermedad = EnfermedadPorClave(required=False, allow_null=True)
    autor = serializers.CharField(source="autor.nombre", read_only=True, allow_null=True)

    class Meta:
        model = Contenido
        fields = [
            "id", "tipo", "enfermedad", "titulo", "cuerpo", "url_fuente", "imagen_url",
            "publicado", "autor", "fecha",
        ]
        read_only_fields = ["fecha"]


class EncuestaSerializer(serializers.ModelSerializer):
    municipio = MunicipioPorClave()

    class Meta:
        model = EncuestaRespuesta
        fields = ["municipio", "respuestas", "consentimiento"]

    def validate_respuestas(self, valor):
        if not isinstance(valor, dict) or not valor:
            raise serializers.ValidationError("Debe ser un objeto con al menos una respuesta.")
        return valor

    def validate_consentimiento(self, valor):
        if valor is not True:
            raise serializers.ValidationError("Se requiere el consentimiento para guardar la respuesta.")
        return valor