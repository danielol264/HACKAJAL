# Arquitectura de la aplicación de escritorio

## Antes y después

La aplicación de escritorio se diseñó para operar de forma desacoplada y desacoplar la interfaz gráfica (PySide6) de las llamadas HTTP. Para habilitar el desarrollo local sin dependencias externas, se incorpora un **Mock API independiente** que implementa el contrato de `API_ESCRITORIO.md` y simula Firebase Authentication.

```text
UI (MainWindow, LoginWindow, páginas y componentes)
        │ solicita
        ▼
Services (AuthService, EpidemiologyService, AlertsService, ContentService)
        │ usa                         │ evalúa
        ▼                              ▼
ApiClient (app/services/api)         PermissionManager
        │                              │
        ├── MODO REAL ───────────────► Django REST Framework ──► Firebase Authentication
        │
        └── MODO MOCK (Local) ───────► Mock API Server (desktop/mock_api)
```

## Responsabilidades

- `app/core`: Configuración de entorno y modos (`AppConfig`), y excepciones tipadas (`ApiError`, `ApiNotConfiguredError`, `ApiRequestError`). Permite alternar entre `MOCK` y `REAL` sin alterar el contrato.
- `app/services/api`: Cliente HTTP genérico (`ApiClient`), con métodos `GET`, `POST`, `PATCH`, `DELETE`. Gestiona el token Bearer en memoria.
- `desktop/mock_api`: Servicio Mock API HTTP independiente basado en `http.server.ThreadingHTTPServer`. Simula todos los endpoints de `API_ESCRITORIO.md`, validación de tokens y reglas de autorización para roles `admin` y `consulta`.
- `app/services`: Servicios de aplicación para cada dominio (`AuthService`, `EpidemiologyService`, `AlertsService`, `ContentService`, `StatisticsService`).
- `app/models`: Perfil autenticado (`User`) y roles (`UserRole.ADMIN`, `UserRole.CONSULTA`).
- `app/permissions`: Definición centralizada de módulos por rol (`ROLE_MODULES`) y control de acceso visual (`PermissionManager`).
- `app/navigation.py`: Catálogo único de elementos de navegación.

## Sesión, Autenticación y Roles

1. `LoginWindow` envía correo y contraseña a la URL de autenticación configurada:
   - **En modo REAL:** `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<FIREBASE_API_KEY>`.
   - **En modo MOCK:** `http://127.0.0.1:8000/identitytoolkit/v1/accounts:signInWithPassword?key=MOCK_KEY`.
2. `AuthService` guarda el `idToken` únicamente en memoria y realiza la consulta a `GET /yo/`.
3. El backend (o Mock API) responde con el perfil (`nombre`, `email`, `rol`, `organizacion`).
4. Si el usuario no tiene rol `admin`, cualquier intento de ejecutar endpoints protegidos (confirmar/descartar alertas, crear contenidos, predicciones, cargas) recibe `403 Forbidden`.
5. `PermissionManager` oculta los módulos administrativos en la interfaz gráfica para el rol `consulta`.
