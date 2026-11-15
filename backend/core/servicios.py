"""Reglas del negocio que usan varias vistas: leer la última predicción y decidir si hay alerta."""
import requests
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

from .models import Alerta, Prediccion, RegistroCasos

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def ultima_prediccion(enfermedad):
    """Las 4 semanas del último mes predicho para esa enfermedad en la región, o None."""
    ultima = Prediccion.objects.filter(enfermedad=enfermedad).order_by("-anio", "-mes", "-creado_en").first()
    if ultima is None:
        return None

    filas = Prediccion.objects.filter(
        enfermedad=enfermedad, anio=ultima.anio, mes=ultima.mes
    ).order_by("semana", "-creado_en")
    por_semana = {}
    for fila in filas:
        por_semana.setdefault(fila.semana, fila)  # si se corrió varias veces, gana la más reciente

    semanas = [por_semana[s].casos_estimados if s in por_semana else None for s in range(1, 5)]
    return {
        "anio": ultima.anio,
        "mes": ultima.mes,
        "semanas": semanas,
        "total": round(sum(v for v in semanas if v is not None), 2),
        "creado_por": ultima.creado_por.nombre,
        "creado_en": ultima.creado_en,
    }


def casos_anio_anterior(enfermedad, anio, mes):
    """Casos de la región en el mismo mes del año anterior, o None si no hay dato."""
    registro = RegistroCasos.objects.filter(enfermedad=enfermedad, anio=anio - 1, mes=mes).first()
    return registro.casos if registro else None


def evaluar_alerta(enfermedad, anio, mes, total):
    """
    Opción C: hay alerta si los casos estimados del mes superan a los del mismo mes del año anterior.
    Sin dato del año anterior también se genera (la organización decide al revisarla).
    Devuelve la alerta pendiente creada o actualizada, o None.
    """
    anterior = casos_anio_anterior(enfermedad, anio, mes)
    pendiente = Alerta.objects.filter(enfermedad=enfermedad, anio=anio, mes=mes, estado="pendiente").first()

    hay_alerta = anterior is None or total > anterior
    if not hay_alerta:
        # una corrida anterior la generó, pero con los datos nuevos ya no aplica y nadie la había revisado
        if pendiente:
            pendiente.delete()
        return None

    ya_publicada = Alerta.objects.filter(enfermedad=enfermedad, anio=anio, mes=mes, estado="confirmada").exists()
    if ya_publicada and pendiente is None:
        return None  # la población ya está avisada de ese mes; no se duplica

    nombre_mes = MESES[mes]
    if anterior is None:
        motivo = (
            f"Se estiman {total:.2f} casos de {enfermedad.nombre} en la región costera "
            f"para {nombre_mes} {anio}. Sin datos de {nombre_mes} {anio - 1} para comparar."
        )
    else:
        motivo = (
            f"Se estiman {total:.2f} casos de {enfermedad.nombre} en la región costera "
            f"para {nombre_mes} {anio}, contra {anterior} en {nombre_mes} {anio - 1}."
        )

    alerta = pendiente or Alerta(enfermedad=enfermedad, anio=anio, mes=mes)
    alerta.casos_estimados = total
    alerta.casos_anio_anterior = anterior
    alerta.motivo = motivo
    alerta.save()
    return alerta

# ---------- Cuentas de Firebase ----------

ERRORES_FIREBASE = {
    "EMAIL_EXISTS": {"email": ["Ese correo ya tiene cuenta en Firebase."]},
    "INVALID_EMAIL": {"email": ["Correo inválido."]},
    "WEAK_PASSWORD": {"password": ["La contraseña debe tener al menos 6 caracteres."]},
}


class FirebaseNoDisponible(APIException):
    status_code = 502
    default_detail = "No se pudo crear la cuenta en Firebase. Intenta de nuevo."


def crear_cuenta_firebase(email, password):
    """Crea la cuenta (correo y contraseña) en Firebase y devuelve su UID."""
    if not settings.FIREBASE_API_KEY:
        raise FirebaseNoDisponible("Falta FIREBASE_API_KEY en el .env del backend.")
    try:
        r = requests.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signUp",
            params={"key": settings.FIREBASE_API_KEY},
            json={"email": email, "password": password, "returnSecureToken": False},
            timeout=15,
        )
    except requests.RequestException:
        raise FirebaseNoDisponible()
    if r.ok:
        return r.json()["localId"]
    codigo = r.json().get("error", {}).get("message", "") if r.content else ""
    for clave, error in ERRORES_FIREBASE.items():
        if codigo.startswith(clave):  # WEAK_PASSWORD trae texto extra después del código
            raise ValidationError(error)
    raise FirebaseNoDisponible(f"Firebase respondió: {codigo or r.status_code}")
