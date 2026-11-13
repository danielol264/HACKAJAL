# HACKAJAL · Aplicación administrativa

Interfaz de escritorio en PySide6 para vigilancia epidemiológica.

## Ejecución rápida en desarrollo (Modo MOCK local)

Por defecto, la aplicación opera en **modo MOCK**, permitiendo desarrollar y probar todos los módulos sin depender de Firebase ni de Django.

1. Iniciar el servicio Mock API independiente (opcional, si no está corriendo `main.py` lo levantará en segundo plano):
   ```powershell
   python run_mock_api.py
   # o bien: python desktop/run_mock_server.py
   ```
2. Iniciar la aplicación de escritorio:
   ```powershell
   python desktop/main.py
   ```

### Credenciales de prueba simuladas:

| Rol | Correo | Contraseña | Capacidades |
|---|---|---|---|
| **admin** | `admin@hackajal.salud.gob.mx` *(o `admin@correo.com`)* | `AdminPassword123!` *(o `admin123`)* | Acceso completo (lectura, confirmación/descarte de alertas, contenido, cargas, predicciones) |
| **consulta** | `consulta@hackajal.salud.gob.mx` *(o `consulta@correo.com`)* | `ConsultaPassword123!` *(o `consulta123`)* | Solo lectura (mapa, estadísticas, alertas, contenido). Acciones administrativas bloqueadas (HTTP 403) |
| **no registrado** | `noregistrado@hackajal.salud.gob.mx` | `Password123!` | Simula cuenta autenticada en Firebase pero no registrada en el sistema (HTTP 401 en `/yo/`) |

---

## Alternar entre MOCK y REAL

Puedes alternar de forma transparente mediante variables de entorno o archivo `.env`:

### Modo MOCK (Desarrollo local):
```powershell
$env:HACKAJAL_MODE = "mock"
# MOCK_API_URL por defecto es http://127.0.0.1:8000/api
```

### Modo REAL (Backend Django + Firebase Authentication):
```powershell
$env:HACKAJAL_MODE = "real"
$env:API_URL = "http://127.0.0.1:8000/api"
$env:FIREBASE_API_KEY = "tu-clave-web-de-firebase"
```

El contrato oficial no se modifica en modo REAL: la app contacta a Firebase Identity Toolkit para obtener el `idToken` y posteriormente consume Django REST Framework con `Authorization: Bearer <token>`.

---

## Ejecutar Pruebas

Para ejecutar la suite completa de pruebas unitarias y de integración del entorno de desarrollo:

```powershell
python -m unittest discover -s desktop/tests
```

Incluye verificación de:
- Arquitectura y permisos por rol.
- Tiempos de respuesta y alternancia de configuración MOCK vs REAL.
- Validación de todos los endpoints de `API_ESCRITORIO.md`.
- Verificación de roles `admin` y `consulta` (incluyendo restricción 403 en acciones administrativas).
- Identificación clara de datos simulados mediante encabezados `X-Mock-Data` y marcas `[SIMULADO]`.
