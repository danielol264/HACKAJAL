from django.db import models


# ---------- Catálogos ----------

class Municipio(models.Model):
    clave_inegi = models.CharField(max_length=5, unique=True)
    nombre = models.CharField(max_length=100)
    region = models.CharField(max_length=50, blank=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Enfermedad(models.Model):
    TIPOS = [("transmisible", "Transmisible"), ("cronica", "Crónica")]

    clave = models.SlugField(max_length=30, unique=True)  # dengue, zika, dm2, has, obesidad
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS)

    def __str__(self):
        return self.nombre


# ---------- Usuarios ----------

class Organizacion(models.Model):
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    ROLES = [("admin", "Administrador"), ("consulta", "Consulta")]

    firebase_uid = models.CharField(max_length=128, unique=True)
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=150)
    email = models.EmailField()
    rol = models.CharField(max_length=10, choices=ROLES, default="consulta")

    def __str__(self):
        return self.nombre


# ---------- Estadísticas de crónicas (DGE / INEGI) ----------

class EstadisticaCronica(models.Model):
    INDICADORES = [
        ("casos_nuevos", "Casos nuevos"),
        ("incidencia", "Incidencia"),
        ("mortalidad", "Mortalidad"),
        ("prevalencia", "Prevalencia"),
    ]
    AMBITOS = [("municipio", "Municipio"), ("region", "Región"), ("estado", "Estado")]
    UNIDADES = [
        ("casos", "Casos"),
        ("defunciones", "Defunciones"),
        ("tasa_100k", "Tasa por 100 mil hab."),
        ("porcentaje", "Porcentaje"),
    ]
    SEXOS = [("total", "Total"), ("hombre", "Hombre"), ("mujer", "Mujer")]

    enfermedad = models.ForeignKey(Enfermedad, on_delete=models.PROTECT)
    indicador = models.CharField(max_length=20, choices=INDICADORES)
    ambito = models.CharField(max_length=20, choices=AMBITOS)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, null=True, blank=True)
    region = models.CharField(max_length=50, blank=True)
    anio = models.PositiveSmallIntegerField()
    sexo = models.CharField(max_length=10, choices=SEXOS, default="total")
    grupo_edad = models.CharField(max_length=20, default="total")      # "<1", "25-44", "65 y +"
    institucion = models.CharField(max_length=30, default="total")     # SSA, IMSS Ord., ISSSTE...
    valor = models.FloatField()
    unidad = models.CharField(max_length=20, choices=UNIDADES)
    fuente = models.CharField(max_length=100)

    class Meta:
        constraints = [
            # municipio solo cuando el ámbito es municipio
            models.CheckConstraint(
                condition=(
                    models.Q(ambito="municipio", municipio__isnull=False)
                    | (~models.Q(ambito="municipio") & models.Q(municipio__isnull=True))
                ),
                name="municipio_segun_ambito",
            ),
        ]

    def __str__(self):
        lugar = self.municipio or self.region or "Jalisco"
        return f"{self.enfermedad} · {self.indicador} · {lugar} · {self.anio}"


# ---------- Datos de la región costera ----------
# shortcut: todo es de una sola región (los 14 municipios costeros); si se agregan regiones, sumar una FK a región

class RegistroCasos(models.Model):
    enfermedad = models.ForeignKey(Enfermedad, on_delete=models.PROTECT)
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()  # 1-12
    casos = models.PositiveIntegerField()     # total de la región en el mes
    cargado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    cargado_en = models.DateTimeField(auto_now=True)  # se actualiza si se vuelve a cargar el mes

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enfermedad", "anio", "mes"], name="casos_unico_por_mes"),
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="casos_mes_valido"),
        ]

    def __str__(self):
        return f"{self.enfermedad} · {self.anio}-{self.mes}: {self.casos}"


class RegistroClima(models.Model):
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    temperatura = models.FloatField(null=True, blank=True)    # °C promedio del mes
    humedad = models.FloatField(null=True, blank=True)        # % promedio del mes
    precipitacion = models.FloatField(null=True, blank=True)  # mm acumulados en el mes
    cargado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    cargado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["anio", "mes"], name="clima_unico_por_mes"),
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="clima_mes_valido"),
        ]

    def __str__(self):
        return f"Clima {self.anio}-{self.mes}"


class Prediccion(models.Model):
    enfermedad = models.ForeignKey(Enfermedad, on_delete=models.PROTECT)
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()            # mes predicho
    semana = models.PositiveSmallIntegerField()         # 1-4
    casos_estimados = models.FloatField()               # valor "con clima" del modelo, ej. 1.96
    creado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="pred_mes_valido"),
            models.CheckConstraint(condition=models.Q(semana__gte=1, semana__lte=4), name="pred_semana_valida"),
            models.CheckConstraint(condition=models.Q(casos_estimados__gte=0), name="pred_casos_no_negativos"),
        ]

    def __str__(self):
        return f"{self.enfermedad} · {self.anio}-{self.mes} sem {self.semana} = {self.casos_estimados}"


class Alerta(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("confirmada", "Confirmada"),
        ("descartada", "Descartada"),
    ]

    enfermedad = models.ForeignKey(Enfermedad, on_delete=models.PROTECT)
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    casos_estimados = models.FloatField()                        # total de las 4 semanas
    casos_anio_anterior = models.PositiveIntegerField(null=True, blank=True)  # vacío = sin dato
    motivo = models.TextField()                                  # lo ve la organización
    mensaje_publico = models.TextField(blank=True)               # lo ve la población
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    revisada_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)
    revisada_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # nunca dos alertas pendientes de la misma enfermedad y mes
            models.UniqueConstraint(
                fields=["enfermedad", "anio", "mes"],
                condition=models.Q(estado="pendiente"),
                name="una_alerta_pendiente_por_mes",
            ),
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="alerta_mes_valido"),
        ]

    def __str__(self):
        return f"{self.enfermedad} · {self.anio}-{self.mes} [{self.estado}]"


# ---------- Portal de la población ----------

class Contenido(models.Model):
    TIPOS = [("prevencion", "Prevención"), ("articulo", "Artículo"), ("nota", "Nota")]

    tipo = models.CharField(max_length=12, choices=TIPOS)
    enfermedad = models.ForeignKey(Enfermedad, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    url_fuente = models.URLField(blank=True)
    imagen_url = models.URLField(blank=True)
    autor = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)
    publicado = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo


class EncuestaRespuesta(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)
    respuestas = models.JSONField()   # shortcut: preguntas sin definir; pasar a columnas cuando estén fijas
    consentimiento = models.BooleanField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(consentimiento=True), name="requiere_consentimiento"),
        ]

    def __str__(self):
        return f"Respuesta {self.id} · {self.municipio}"