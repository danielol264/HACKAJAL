# Especificación del backend para la APP DE ESCRITORIO (Python) — HackaJal

> **Instrucciones para la IA que lea este documento**
> - Este es el contrato **exacto** del backend. No inventes endpoints, campos, parámetros ni formatos que no estén aquí.
> - Todas las peticiones (salvo `/municipios/` y `/enfermedades/`) llevan `Authorization: Bearer <idToken de Firebase>`.
> - El inicio de sesión lo hace **Firebase Authentication** (correo y contraseña). La app **nunca** manda la contraseña al backend de Django.
> - Los municipios y enfermedades se identifican **por clave** (texto), nunca por id numérico.
> - Casos, clima, predicciones y alertas son de **toda la región costera** (no por municipio). No agregues selector de municipio en mapa, alertas ni predicción.
> - Si algo no está definido aquí, pregunta al equipo de backend en lugar de suponer.

---

## 1. Contexto del proyecto

Hackatón de Jalisco. Predicción epidemiológica de **dengue** para la **región costera de Jalisco** (14 municipios en conjunto).

**Flujo general:**
1. Un usuario de una organización de salud inicia sesión.
2. Carga un CSV/Excel con los datos mensuales de la región (casos y clima).
3. Un modelo en Python predice los casos de las **4 semanas** del mes siguiente.
4. El backend compara el total con el mismo mes del año anterior; si sube (o no hay dato), crea una **alerta pendiente**.
5. La organización revisa la alerta y la **confirma** (se publica en el portal web) o la **descarta**.

**La app de escritorio tiene estas secciones:**
1. Login.
2. Mapa de la región (color según el riesgo).
3. Estadísticas (casos y clima por mes, predicción, enfermedades crónicas, encuesta).
4. Alertas (revisar, confirmar, descartar).
5. Artículos y notas para el portal (crear, editar, publicar, borrar).
6. Carga de datos y predicción *(solo si el modelo corre dentro de la app; aún no definido)*.

---

## 2. Datos técnicos

| Concepto | Valor |
|---|---|
| URL base local | `http://127.0.0.1:8000/api` |
| URL base producción | Pendiente (usar variable de entorno `API_URL`) |
| Formato | JSON. En POST/PATCH: `Content-Type: application/json` |
| Idioma de los errores | Español |
| Fechas | ISO 8601 |

**Todas las URLs terminan en `/`.**

---

## 3. Autenticación

### 3.1 Login con Firebase
```
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<FIREBASE_API_KEY>
Content-Type: application/json

{ "email": "usuario@correo.com", "password": "********", "returnSecureToken": true }
```
**Respuesta:** trae `idToken` (el token). **Dura 1 hora.**

| Error de Firebase (`error.message`) | Qué mostrar |
|---|---|
| `INVALID_LOGIN_CREDENTIALS` | "Correo o contraseña incorrectos" |
| `TOO_MANY_ATTEMPTS_TRY_LATER` | "Demasiados intentos, espera un momento" |

### 3.2 Usar el token
En cada petición a la API:
```
Authorization: Bearer <idToken>
```
Si cualquier petición responde **401**, el token venció o no es válido: volver a pedir login.

### 3.3 Roles

| Rol | Puede |
|---|---|
| `admin` | Todo |
| `consulta` | Solo ver (mapa, estadísticas, alertas, contenido). **Ocultar** los botones de confirmar, descartar, crear, editar, borrar, cargar y predecir |

Justo después del login, llamar a `GET /yo/` para conocer el rol.

| Símbolo | Acceso |
|---|---|
| 🔓 | Público (sin token) |
| 🔒 | Cualquier usuario con sesión |
| 👑 | Solo `admin` (un `consulta` recibe 403) |

---

## 4. Endpoints

| # | Método | Ruta | Acceso | Sección |
|---|---|---|---|---|
| 1 | GET | `/yo/` | 🔒 | Login |
| 2 | GET | `/municipios/` | 🔓 | Mapa |
| 3 | GET | `/enfermedades/` | 🔓 | Selectores |
| 4 | GET | `/mapa/?enfermedad=` | 🔒 | Mapa |
| 5 | GET | `/estadisticas/?enfermedad=&anio=&municipio=` | 🔒 | Estadísticas |
| 6 | GET | `/estadisticas/encuesta/` | 🔒 | Estadísticas |
| 7 | GET | `/predicciones/?enfermedad=` | 🔒 | Estadísticas / Mapa |
| 8 | GET | `/alertas/?estado=&enfermedad=` | 🔒 | Alertas |
| 9 | POST | `/alertas/{id}/confirmar/` | 👑 | Alertas |
| 10 | POST | `/alertas/{id}/descartar/` | 👑 | Alertas |
| 11 | GET | `/contenido/?tipo=&enfermedad=` | 🔒 | Artículos |
| 12 | GET | `/contenido/{id}/` | 🔒 | Artículos |
| 13 | POST | `/contenido/` | 👑 | Artículos |
| 14 | PATCH | `/contenido/{id}/` | 👑 | Artículos |
| 15 | DELETE | `/contenido/{id}/` | 👑 | Artículos |
| 16 | POST | `/cargas/` | 👑 | Carga *(si aplica)* |
| 17 | POST | `/predicciones/` | 👑 | Predicción *(si aplica)* |

---

### 4.1 `GET /yo/` 🔒
**Respuesta `200`:**
```json
{ "nombre": "Daniel", "email": "usuario@correo.com", "rol": "admin", "organizacion": "Equipo HackaJal" }
```
`401` = el usuario existe en Firebase pero **no está dado de alta en el sistema** → "Tu cuenta no tiene acceso; contacta al administrador".

### 4.2 `GET /municipios/` 🔓
```json
[ { "clave_inegi": "14067", "nombre": "Puerto Vallarta", "region": "Costa-Sierra Occidental", "latitud": 20.62, "longitud": -105.23 } ]
```
`latitud` y `longitud` pueden ser `null` (aún no se cargan): en ese caso, no dibujar ese municipio.

### 4.3 `GET /enfermedades/` 🔓
```json
[ { "clave": "dengue", "nombre": "Dengue", "tipo": "transmisible" }, { "clave": "dm2", "nombre": "Diabetes mellitus tipo 2", "tipo": "cronica" } ]
```
`tipo`: `transmisible` (se predice) o `cronica` (solo estadística). Hoy solo se predice `dengue`.

### 4.4 `GET /mapa/?enfermedad=dengue` 🔒
`enfermedad` es obligatoria.
```json
{
  "enfermedad": "dengue",
  "prediccion": {
    "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46,
    "creado_por": "Daniel", "creado_en": "2026-11-13T14:15:00Z"
  },
  "casos_anio_anterior": 2,
  "alerta": { "id": 3, "estado": "pendiente" },
  "municipios": [
    { "clave_inegi": "14022", "nombre": "Cihuatlán", "region": "Costa Sur", "latitud": null, "longitud": null }
  ]
}
```
- **Toda la región se pinta del mismo color.** El color lo decide la app. Sugerencia: verde si `alerta` es `null`; amarillo si `alerta.estado == "pendiente"`; rojo si `"confirmada"`.
- `prediccion`, `casos_anio_anterior` y `alerta` pueden ser `null`.
- `semanas` puede traer `null` en alguna posición si faltó esa semana.

### 4.5 `GET /estadisticas/` 🔒
Todos los parámetros son opcionales:

| Parámetro | Efecto |
|---|---|
| `enfermedad` | Filtra casos y trae la predicción. Si es crónica, trae `cronicas` |
| `anio` | Año de casos y clima (por defecto, el actual) |
| `municipio` | **Solo** filtra las crónicas (municipio + estatales) |

Ejemplo: `/estadisticas/?enfermedad=dengue&anio=2026`
```json
{
  "filtros": { "enfermedad": "dengue", "municipio": null, "anio": 2026 },
  "casos_por_mes": [ { "enfermedad": "dengue", "mes": 9, "casos": 14 }, { "enfermedad": "dengue", "mes": 10, "casos": 9 } ],
  "clima_por_mes": [ { "mes": 9, "temperatura": 29.5, "humedad": 72.0, "precipitacion": 180.4 } ],
  "prediccion": { "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46, "creado_por": "Daniel", "creado_en": "..." },
  "cronicas": null
}
```
- **Un mes que no aparece = sin dato** (no dibujar 0).
- En el clima, cualquier valor puede ser `null`.
- Ejemplo de crónicas: `/estadisticas/?enfermedad=dm2` → `cronicas` es una lista de:
```json
{ "indicador": "incidencia", "ambito": "estado", "municipio__clave_inegi": null, "region": "", "anio": 2025,
  "sexo": "total", "grupo_edad": "25-44", "institucion": "total", "valor": 249.28, "unidad": "tasa_100k", "fuente": "SUIVE/DGE Anuario de Morbilidad 2025" }
```
  - `indicador`: `casos_nuevos`, `incidencia`, `mortalidad`, `prevalencia`.
  - `unidad`: `casos`, `defunciones`, `tasa_100k`, `porcentaje`.
  - `grupo_edad`: `<1`, `1-4`, `5-9`, `10-14`, `15-19`, `20-24`, `25-44`, `45-49`, `50-59`, `60-64`, `65 y +`, `Ign.` o `total`.
  - `institucion`: `SSA`, `IMSS Ord.`, `ISSSTE`, `IMSS Bienest.`, `DIF`, `PEMEX`, `SEDENA`, `SEMAR`, `OTRAS` o `total`.

**Errores:** `400` si una clave no existe o `anio` no es número.

### 4.6 `GET /estadisticas/encuesta/` 🔒
```json
{ "total": 12, "por_municipio": [ { "municipio__clave_inegi": "14022", "municipio__nombre": "Cihuatlán", "respuestas": 7 } ] }
```

### 4.7 `GET /predicciones/?enfermedad=dengue` 🔒
```json
{ "prediccion": { "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46, "creado_por": "Daniel", "creado_en": "..." } }
```
`prediccion` es `null` si no hay. Mostrar como tabla: Semana 1–4 con su valor y el total del mes.

### 4.8 `GET /alertas/` 🔒
Filtros opcionales: `estado` (`pendiente`, `confirmada`, `descartada`), `enfermedad`. Ordenadas de la más nueva a la más vieja.
```json
[
  {
    "id": 3, "enfermedad": "dengue", "enfermedad_nombre": "Dengue", "anio": 2026, "mes": 12,
    "casos_estimados": 4.46, "casos_anio_anterior": 2,
    "motivo": "Se estiman 4.46 casos de Dengue en la región costera para diciembre 2026, contra 2 en diciembre 2025.",
    "mensaje_publico": "", "estado": "pendiente",
    "revisada_por": null, "revisada_en": null, "creada_en": "2026-11-13T08:15:00-06:00"
  }
]
```
`casos_anio_anterior` puede ser `null` (no había dato para comparar).

### 4.9 `POST /alertas/{id}/confirmar/` 👑
```json
{ "mensaje_publico": "Se espera un aumento de dengue en la región costera en diciembre. Elimina recipientes con agua y usa repelente." }
```
- `mensaje_publico` es obligatorio (máximo 2000 caracteres). **Es lo que verá la población**: pedirlo en un cuadro de texto antes de confirmar.
- **Respuesta `200`:** la alerta con `estado: "confirmada"`, `revisada_por` y `revisada_en`.
- **Errores:** `400` sin mensaje · `404` no existe · `409` `{"detail": "La alerta ya está confirmada."}` (otra persona ya la revisó) → refrescar la lista.

### 4.10 `POST /alertas/{id}/descartar/` 👑
Sin body. Mismas respuestas y errores que confirmar, con `estado: "descartada"`.

### 4.11 `GET /contenido/` 🔒
Con sesión trae **publicados y borradores**. Filtros opcionales: `tipo` (`prevencion`, `articulo`, `nota`) y `enfermedad` (clave).
```json
[ { "id": 5, "tipo": "articulo", "enfermedad": "dengue", "titulo": "...", "cuerpo": "...", "url_fuente": "", "imagen_url": "", "publicado": false, "autor": "Daniel", "fecha": "..." } ]
```

### 4.12 `GET /contenido/{id}/` 🔒
Un contenido.

### 4.13 `POST /contenido/` 👑
```json
{ "tipo": "articulo", "enfermedad": "dengue", "titulo": "Título", "cuerpo": "Texto", "url_fuente": "https://...", "imagen_url": "", "publicado": false }
```

| Campo | Obligatorio | Regla |
|---|---|---|
| `tipo` | Sí | `prevencion`, `articulo` o `nota` |
| `titulo` | Sí | Máximo 200 caracteres |
| `cuerpo` | Sí | Texto plano |
| `enfermedad` | No | Clave o `null` |
| `url_fuente`, `imagen_url` | No | URL válida o `""` |
| `publicado` | No | `false` por defecto (borrador) |

No se manda `autor`: lo pone el backend con el usuario del token. **Respuesta `201`:** lo creado.

### 4.14 `PATCH /contenido/{id}/` 👑
Solo los campos que cambian. Para publicar: `{ "publicado": true }`. **Respuesta `200`.** (`PUT` no existe.)

### 4.15 `DELETE /contenido/{id}/` 👑
**Respuesta `204`**, sin cuerpo. Pedir confirmación al usuario antes de borrar.

### 4.16 `POST /cargas/` 👑 *(solo si la app sube los datos)*
Filas del CSV/plantilla: **una fila por mes de toda la región**.
```json
[
  { "anio": 2026, "mes": 9, "casos_dengue": 14, "temperatura_c": 29.5, "humedad_pct": 72, "precipitacion_mm": 180.4 },
  { "anio": 2026, "mes": 10, "casos_dengue": 9, "temperatura_c": null, "humedad_pct": null, "precipitacion_mm": null }
]
```

| Campo | Regla |
|---|---|
| `anio` | 2000 a 2100 (obligatorio) |
| `mes` | 1 a 12 (obligatorio) |
| `casos_dengue` | Entero de 0 o más. `null` = no tocar el dato existente |
| `temperatura_c` | -20 a 60 o `null` |
| `humedad_pct` | 0 a 100 o `null` |
| `precipitacion_mm` | 0 o más, o `null` |

- **Todo o nada:** si una fila falla, no se guarda ninguna.
- Una fila que solo trae `anio` y `mes` (sin casos ni clima) es un error: `400` con `"La fila no trae casos ni clima."`. Quita esas filas antes de enviar.
- Si el mes ya existía, se actualiza.
- No repetir el mismo año y mes en un envío.
- **Respuesta `201`:** `{ "casos": { "creados": 2, "actualizados": 0 }, "clima": { "creados": 1, "actualizados": 0 } }`
- **Error `400`:** las llaves son el índice de la fila desde 0. **Fila en Excel = índice + 2.**
```json
{ "1": { "mes": ["Asegúrese de que este valor es menor o igual a 12."] } }
```
- Con pandas, convertir las celdas vacías a `None` (`NaN` no es JSON válido):
```python
df = pd.read_excel(ruta, sheet_name="Datos").dropna(subset=["anio", "mes"])
filas = df.astype(object).where(df.notna(), None).to_dict(orient="records")
```

### 4.17 `POST /predicciones/` 👑 *(solo si la app corre el modelo)*
```json
{ "enfermedad": "dengue", "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5] }
```
`semanas` = exactamente 4 números de 0 en adelante (casos estimados "con clima").
**Respuesta `201`:**
```json
{ "enfermedad": "dengue", "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46, "alerta": { "id": 3, "estado": "pendiente" } }
```
`alerta` es `null` si no se generó. Si se generó, avisar al usuario: "Se generó una alerta pendiente de revisión".

---

## 5. Errores generales

| Código | Significado | Qué hacer |
|---|---|---|
| `400` | Datos inválidos: `{"campo": ["mensaje"]}` | Mostrar el mensaje |
| `401` | Token vencido o inválido, o usuario no registrado | Volver al login |
| `403` | Sin permiso (rol `consulta`) | "No tienes permiso para esta acción" |
| `404` | No existe | Refrescar la lista |
| `409` | La alerta ya fue revisada | Refrescar la lista |
| Sin conexión / `500` | Servidor caído | "No se pudo conectar con el servidor" |

---

## 6. Código base sugerido (Python)

```python
# api_cliente.py
import os

import requests

API = os.getenv("API_URL", "http://127.0.0.1:8000/api")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")


class ErrorApi(Exception):
    def __init__(self, status, datos):
        super().__init__(f"{status}: {datos}")
        self.status, self.datos = status, datos


class Cliente:
    def __init__(self):
        self.token = None

    def login(self, email, password):
        r = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=30,
        )
        if not r.ok:
            raise ErrorApi(r.status_code, r.json().get("error", {}).get("message"))
        self.token = r.json()["idToken"]
        return self.get("/yo/")  # {nombre, email, rol, organizacion}

    def _pedir(self, metodo, ruta, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.request(metodo, f"{API}{ruta}", headers=headers, timeout=60, **kwargs)
        datos = None if r.status_code == 204 else r.json()
        if not r.ok:
            raise ErrorApi(r.status_code, datos)  # 401 → volver al login
        return datos

    def get(self, ruta, **params):
        return self._pedir("GET", ruta, params=params)

    def post(self, ruta, datos=None):
        return self._pedir("POST", ruta, json=datos)

    def patch(self, ruta, datos):
        return self._pedir("PATCH", ruta, json=datos)

    def delete(self, ruta):
        return self._pedir("DELETE", ruta)


# Ejemplos:
# c = Cliente(); usuario = c.login("correo", "contraseña")
# c.get("/mapa/", enfermedad="dengue")
# c.get("/estadisticas/", enfermedad="dengue", anio=2026)
# c.get("/alertas/", estado="pendiente")
# c.post("/alertas/3/confirmar/", {"mensaje_publico": "..."})
# c.post("/contenido/", {"tipo": "articulo", "titulo": "T", "cuerpo": "C"})
# c.patch("/contenido/5/", {"publicado": True})
```

---

## 7. Resumen de pantallas

| Pantalla | Endpoints | Solo admin |
|---|---|---|
| Login | Firebase + `GET /yo/` | — |
| Mapa | `GET /mapa/?enfermedad=dengue` | — |
| Estadísticas | `GET /estadisticas/`, `GET /estadisticas/encuesta/`, `GET /predicciones/` | — |
| Alertas | `GET /alertas/` | Confirmar y descartar |
| Artículos | `GET /contenido/`, `GET /contenido/{id}/` | Crear, editar, publicar, borrar |
| Carga y predicción *(si aplica)* | `POST /cargas/`, `POST /predicciones/` | Todo |
