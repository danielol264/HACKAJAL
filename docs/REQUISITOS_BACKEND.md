# HACKAJAL — Requisitos para el Equipo de Backend (Django + Firebase)

Este documento enumera de forma concisa y estricta la información técnica, credenciales y validaciones de infraestructura que el equipo de desarrollo backend debe suministrar para habilitar la conexión de la aplicación de escritorio HACKAJAL en entorno de producción.

---

## 1. Datos de Configuración e Infraestructura

| Requisito | Descripción | Estado Actual |
|---|---|---|
| **URL Base de Producción (`API_URL`)** | URL HTTPS del servicio Django REST Framework terminada en `/api` (ej. `https://api.hackajal.jalisco.gob.mx/api`). | **PENDIENTE POR PROPORCIONAR** |
| **Clave Web de Firebase (`FIREBASE_API_KEY`)** | Identificador público (*Web API Key*) del proyecto Firebase Console para consumir `identitytoolkit.googleapis.com`. | **PENDIENTE POR PROPORCIONAR** |
| **Certificados SSL / HTTPS** | Garantizar que el dominio cuente con certificados TLS/SSL válidos y de una CA reconocida para evitar rechazos en peticiones HTTPS de Python (`certifi`). | **PENDIENTE POR VERIFICAR** |
| **Configuración de CORS** | Si aplica para clientes web/APIs, permitir los encabezados estándar `Authorization`, `Content-Type` y métodos `GET, POST, PATCH, DELETE`. | **PENDIENTE POR VERIFICAR** |

---

## 2. Configuración de Firebase Authentication

1. **Método de inicio de sesión habilitado:**
   - Debe estar activo el proveedor **Correo electrónico/Contraseña** (*Email/Password*) en Firebase Console.
2. **Duración de Tokens:**
   - La aplicación asume tokens estándar de Firebase (`idToken` con vigencia de 3600 segundos).
3. **Usuarios Iniciales:**
   - Proporcionar al menos un usuario de prueba para cada rol:
     - Rol Administrador (`admin`).
     - Rol Consulta (`consulta`).

---

## 3. Implementación en Django REST Framework

1. **Validación del Bearer Token:**
   - El backend debe validar el token de Firebase (`Authorization: Bearer <idToken>`) utilizando el Firebase Admin SDK de Python (`auth.verify_id_token(id_token)`).
2. **Vinculación con el Endpoint `/yo/`:**
   - Django debe mapear el `uid` o `email` de Firebase con su tabla interna de usuarios y responder a `GET /yo/`:
     ```json
     {
       "nombre": "Nombre Completo",
       "email": "correo@dominio.com",
       "rol": "admin",
       "organizacion": "Nombre de la Organización"
     }
     ```
   - Si el usuario existe en Firebase pero no está dado de alta en la base de datos de Django, el endpoint `/yo/` **debe responder HTTP 401**.
3. **Control de Acceso Basado en Roles (RBAC):**
   - Endpoints administrativos (confirmar/descartar alertas, CRUD de contenido, cargas y predicciones) deben rechazar usuarios con rol `consulta` respondiendo estrictamente **HTTP 403 Forbidden**.
4. **Respuesta en Errores de Validación (HTTP 400):**
   - En el endpoint `POST /cargas/`, los errores de validación de filas deben usar el índice base 0 de la fila como clave JSON (ej. `{"1": {"mes": ["Debe ser menor o igual a 12."]}}`), para que la app de escritorio pueda traducirlos a filas de Excel (`índice + 2`).
5. **Códigos de Conflicto (HTTP 409):**
   - En `POST /alertas/{id}/confirmar/` y `/descartar/`, si la alerta ya fue atendida por otro usuario, retornar `409 Conflict` con `{"detail": "La alerta ya está confirmada."}`.

---

## 4. Checklist de Entrega por el Desarrollador Backend

- [ ] URL base del servidor accesible vía HTTPS.
- [ ] Clave `FIREBASE_API_KEY` válida generada en Firebase Console.
- [ ] Base de datos poblada con los catálogos base (`/municipios/` y `/enfermedades/`).
- [ ] Usuario con rol `admin` creado en Firebase y registrado en Django.
- [ ] Usuario con rol `consulta` creado en Firebase y registrado en Django.
- [ ] Verificación de que los endpoints admiten slash final `/` conforme a la especificación.
