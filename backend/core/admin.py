from django.contrib import admin

from . import models

for modelo in (
    models.Municipio, models.Enfermedad, models.Organizacion, models.Usuario,
    models.EstadisticaCronica, models.RegistroCasos, models.RegistroClima,
    models.Prediccion, models.Alerta, models.Contenido, models.EncuestaRespuesta,
):
    admin.site.register(modelo)