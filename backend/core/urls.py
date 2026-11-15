from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("contenido", views.ContenidoViewSet, basename="contenido")

urlpatterns = [
    # Autenticación
    path("yo/", views.YoView.as_view()),
    # Tarjeta 19
    path("cargas/", views.CargaView.as_view()),
    # Tarjeta 20
    path("municipios/", views.MunicipiosView.as_view()),
    path("enfermedades/", views.EnfermedadesView.as_view()),
    path("mapa/", views.MapaView.as_view()),
    path("estadisticas/", views.EstadisticasView.as_view()),
    path("estadisticas/encuesta/", views.EstadisticasEncuestaView.as_view()),
    # Tarjeta 21
    path("predicciones/", views.PrediccionesView.as_view()),
    path("alertas/", views.AlertasView.as_view()),
    path("alertas/<int:pk>/confirmar/", views.ConfirmarAlertaView.as_view()),
    path("alertas/<int:pk>/descartar/", views.DescartarAlertaView.as_view()),
    path("alertas-publicas/", views.AlertasPublicasView.as_view()),
    # Tarjeta 22
    path("encuesta/", views.EncuestaView.as_view()),
    # Administración de usuarios
    path("organizaciones/", views.OrganizacionesView.as_view()),
    path("usuarios/", views.UsuariosView.as_view()),
    path("usuarios/<int:pk>/", views.UsuarioDetalleView.as_view()),
] + router.urls