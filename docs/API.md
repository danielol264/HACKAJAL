# Documentación de la API — HackaJal

Backend en Django REST Framework. Lo consumen dos clientes:

- **App de escritorio** (organizaciones): con inicio de sesión.
- **Portal web en React** (población): sin inicio de sesión.

---

## 1. Información general

| Concepto | Valor |
|---|---|
| URL base (local) | `http://127.0.0.1:8000/api` |
| URL base (producción) | *Pendiente de despliegue* |
| Formato | JSON en peticiones y respuestas (`Content-Type: application/json`) |
| Idioma de los errores | Español |
| Zona horaria | `America/Mexico_City` |

### Claves en lugar de IDs

En toda la API, municipios y enfermedades se identifican **por clave**, nunca por ID interno.

| Dato | Clave | Ejemplo |
|---|---|---|
| Municipio | Clave INEGI de 5 dígitos (14 = Jalisco + 3 del municipio) | `"14067"` (Puerto Vallarta) |
| Enfermedad | Clave corta | `"dengue"`, `"zika"`, `"chikungunya"`, `"dm1"`, `"dm2"`, `"has"`, `"obesidad"` |

Los catálogos completos se obtienen con `GET /municipios/` y `GET /enfermedades/`.

### Alcance: región costera

Casos, clima, predicciones y alertas son de **toda la región costera** (los 14 municipios en conjunto), por mes. Por ahora solo se trabaja **dengue**. Los municipios se usan en la encuesta, en las crónicas de INEGI y para dibujar la región en el mapa.

### Municipios de la región costera

| Región | Municipios |
|---|---|
| Costa Sur | Casimiro Castillo, Cihuatlán, Cuautitlán de García Barragán, La Huerta, Tomatlán, Villa Purificación |
| Costa-Sierra Occidental | Atenguillo, Cabo Corrientes, Guachinango, Mascota, Mixtlán, Puerto Vallarta, San Sebastián del Oeste, Talpa de Allende |

---

## 2. Autenticación y roles

El inicio de sesión lo hace **Firebase Authentication** (correo y contraseña). Django nunca recibe la contraseña: solo verifica el token que entrega Firebase.

### Cómo obtener el token

```
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<API_KEY_DE_FIREBASE>
```
```json
{ "email": "usuario@correo.com", "password": "********", "returnSecureToken": true }
```
La respuesta trae `idToken`. **Dura 1 hora**; después hay que pedir otro.

### Cómo usarlo

En cada petición que requiere sesión:
```
Authorization: Bearer <idToken>
```

### Niveles de acceso

| Símbolo | Nivel | Quién |
|---|---|---|
| 🔓 | Público | Cualquiera, sin token (portal web) |
| 🔒 | Usuario | Cualquier usuario de una organización con sesión |
| 👑 | Admin | Solo usuarios con rol `admin` |

| Rol | Puede |
|---|---|
| `admin` | Todo: cargar datos, guardar predicciones, confirmar o descartar alertas, administrar contenido |
| `consulta` | Solo ver: mapa, estadísticas, alertas, predicciones |

### Alta de usuarios

1. El administrador crea la cuenta en la consola de Firebase (Authentication → Usuarios).
2. Copia el **UID** que asigna Firebase.
3. Crea el `Usuario` en el admin de Django (`/admin`) con ese UID, su organización y su rol.

Un usuario que existe en Firebase pero no en Django recibe `401`.

---

## 3. Errores

### Códigos de respuesta

| Código | Significado |
|---|---|
| `200` | Correcto |
| `201` | Creado |
| `204` | Borrado (sin contenido) |
| `400` | Datos inválidos. El cuerpo dice qué campo falló |
| `401` | Sin token, token inválido o vencido, o usuario no registrado en el sistema |
| `403` | Con sesión, pero sin permiso (rol `consulta` intentando una acción de admin) |
| `404` | No existe (o es un borrador y se pidió sin sesión) |
| `409` | Conflicto: la alerta ya fue revisada |
| `429` | Demasiadas peticiones (límite de la encuesta) |

### Formato de los errores

**Error en un campo:**
```json
{ "enfermedad": ["enfermedad 'xyz' no existe."] }
```

**Error en un envío de varias filas** (`/cargas/`, `/predicciones/`): la llave es el **índice de la fila, empezando en 0**. Solo aparecen las filas con error.
```json
{
  "1": {
    "mes": ["Asegúrese de que este valor es menor o igual a 12."],
    "casos_dengue": ["Debe ser un número entero de 0 o más."]
  }
}
```
En la plantilla de Excel: **fila de Excel = índice + 2** (por el encabezado y porque Excel empieza en 1).

**Error general:**
```json
{ "detail": "La alerta ya está confirmada." }
```

---

## 4. Resumen de endpoints

| # | Método | Ruta | Acceso | Cliente | Para qué |
|---|---|---|---|---|---|
| 1 | GET | `/yo/` | 🔒 | Escritorio | Datos del usuario que inició sesión |
| 2 | GET | `/municipios/` | 🔓 | Ambos | Catálogo de municipios |
| 3 | GET | `/enfermedades/` | 🔓 | Ambos | Catálogo de enfermedades |
| 4 | POST | `/cargas/` | 👑 | Escritorio / modelo | Subir la plantilla mensual de la región (casos y clima) |
| 5 | POST | `/predicciones/` | 👑 | Escritorio / modelo | Guardar el resultado del modelo y evaluar alerta |
| 6 | GET | `/predicciones/` | 🔒 | Escritorio | Última predicción de la región |
| 7 | GET | `/alertas/` | 🔒 | Escritorio | Alertas para revisar |
| 8 | POST | `/alertas/{id}/confirmar/` | 👑 | Escritorio | Publicar una alerta |
| 9 | POST | `/alertas/{id}/descartar/` | 👑 | Escritorio | No publicar una alerta |
| 10 | GET | `/alertas-publicas/` | 🔓 | Portal | Alertas confirmadas y vigentes |
| 11 | GET | `/mapa/` | 🔒 | Escritorio | Predicción y alerta de la región, con los municipios a pintar |
| 12 | GET | `/estadisticas/` | 🔒 | Escritorio | Casos, clima, predicción y crónicas |
| 13 | GET | `/estadisticas/encuesta/` | 🔒 | Escritorio | Resumen de la encuesta |
| 14 | GET | `/contenido/` | 🔓 | Ambos | Lista de prevención, artículos y notas |
| 15 | GET | `/contenido/{id}/` | 🔓 | Ambos | Un contenido |
| 16 | POST | `/contenido/` | 👑 | Escritorio | Crear contenido |
| 17 | PATCH | `/contenido/{id}/` | 👑 | Escritorio | Editar o publicar |
| 18 | DELETE | `/contenido/{id}/` | 👑 | Escritorio | Borrar |
| 19 | POST | `/encuesta/` | 🔓 | Portal | Enviar una respuesta anónima |

---

## 5. Sesión y catálogos

### 5.1 `GET /yo/` 🔒

Devuelve quién inició sesión. La app lo usa para mostrar u ocultar opciones según el rol.

**Respuesta `200`:**
```json
{ "nombre": "Daniel", "email": "usuario@correo.com", "rol": "admin", "organizacion": "Equipo HackaJal" }
```

### 5.2 `GET /municipios/` 🔓

**Respuesta `200`:**
```json
[
  { "clave_inegi": "14067", "nombre": "Puerto Vallarta", "region": "Costa-Sierra Occidental", "latitud": null, "longitud": null }
]
```
`latitud` y `longitud` pueden venir en `null` mientras no se carguen las coordenadas.

### 5.3 `GET /enfermedades/` 🔓

**Respuesta `200`:**
```json
[
  { "clave": "dengue", "nombre": "Dengue", "tipo": "transmisible" },
  { "clave": "dm2", "nombre": "Diabetes mellitus tipo 2", "tipo": "cronica" }
]
```
`tipo`: `transmisible` (se predice) o `cronica` (solo estadística).

---

## 6. Carga de datos

### 6.1 `POST /cargas/` 👑

Recibe las filas de la **plantilla mensual** (`plantilla_carga_mensual.xlsx`). Cada fila es **un mes de toda la región costera**, con los casos de cada enfermedad y el clima.

**Body:** lista de filas.
```json
[
  { "anio": 2026, "mes": 9, "casos_dengue": 14, "temperatura_c": 29.5, "humedad_pct": 72, "precipitacion_mm": 180.4 },
  { "anio": 2026, "mes": 10, "casos_dengue": 9, "temperatura_c": null, "humedad_pct": null, "precipitacion_mm": null }
]
```

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `anio` | entero | Sí | 2000 a 2100 |
| `mes` | entero | Sí | 1 a 12 |
| `casos_<clave>` | entero | No | 0 o más. Una columna por enfermedad (`casos_dengue`; después `casos_zika`, etc.). La clave debe existir |
| `temperatura_c` | decimal | No | -20 a 60 (°C promedio del mes) |
| `humedad_pct` | decimal | No | 0 a 100 (% promedio del mes) |
| `precipitacion_mm` | decimal | No | 0 o más (mm acumulados en el mes) |

**Reglas:**
- **Vacío (`null`) significa "no tocar"**: no borra el dato que ya existía. `0` significa "hubo 0 casos".
- Si el mes ya existía, **se actualiza** (sirve para corregir).
- **Todo o nada**: si una fila tiene error, no se guarda ninguna.
- Una fila sin casos ni clima es un error.
- No se puede repetir el mismo año y mes dentro del mismo envío.
- Se acepta `14.0` como `14` (formato común al leer Excel con pandas).
- Las columnas que no reconoce se ignoran.

**Respuesta `201`:**
```json
{ "casos": { "creados": 2, "actualizados": 0 }, "clima": { "creados": 1, "actualizados": 0 } }
```

**Lectura de la plantilla en Python:**
```python
import pandas as pd
import requests

df = pd.read_excel(ruta, sheet_name="Datos").dropna(subset=["anio", "mes"])
filas = df.astype(object).where(df.notna(), None).to_dict(orient="records")  # celdas vacías → None
r = requests.post(f"{API}/cargas/", json=filas, headers={"Authorization": f"Bearer {token}"})
```
La conversión de celdas vacías a `None` es obligatoria: pandas usa `NaN`, que no es JSON válido.

---

## 7. Predicciones y alertas

### 7.1 `POST /predicciones/` 👑

Resultado del modelo para **toda la región**: los casos estimados de las **4 semanas** del mes que se predice. Lo manda la app (o el script del modelo) con el token del usuario que inició la predicción.

**Body:** un solo objeto.
```json
{ "enfermedad": "dengue", "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5] }
```

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `enfermedad` | clave | Sí | Debe existir |
| `anio` | entero | Sí | 2000 a 2100 |
| `mes` | entero | Sí | 1 a 12 (el mes predicho) |
| `semanas` | lista de 4 decimales | Sí | Exactamente 4 valores, 0 o más (valor "con clima" del modelo) |

**Qué hace el backend:**
1. Guarda las 4 semanas, con quién y cuándo.
2. Suma el **total estimado del mes** (ejemplo: 1.2 + 1.96 + 0.8 + 0.5 = 4.46).
3. Lo compara con los **casos de la región en el mismo mes del año anterior** (ejemplo: diciembre 2025).
4. Decide si hay alerta:

| Caso | Resultado |
|---|---|
| Total estimado > año anterior | Crea o actualiza una alerta **pendiente** |
| No hay dato del año anterior | Crea o actualiza una alerta **pendiente** ("sin datos para comparar") |
| Total estimado ≤ año anterior | No hay alerta. Si había una pendiente sin revisar del mismo mes, se elimina |
| Ya hay una alerta **confirmada** de ese mes | No se crea otra |

Nunca hay dos alertas pendientes de la misma enfermedad y mes: si se corre el modelo varias veces, se actualiza la misma.

**Respuesta `201`:**
```json
{
  "enfermedad": "dengue", "anio": 2026, "mes": 12,
  "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46,
  "alerta": { "id": 3, "estado": "pendiente" }
}
```
`alerta` es `null` si no se generó.

### 7.2 `GET /predicciones/?enfermedad=` 🔒

Última predicción de la región para esa enfermedad. `enfermedad` es **obligatoria**.

**Respuesta `200`:**
```json
{
  "prediccion": {
    "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46,
    "creado_por": "Daniel", "creado_en": "2026-11-13T14:15:00.123456Z"
  }
}
```
`prediccion` es `null` si no hay ninguna. Las fechas van en formato ISO 8601; en este bloque vienen en UTC (`Z`).

### 7.3 `GET /alertas/?estado=&enfermedad=` 🔒

Lista de alertas para la organización, de la más nueva a la más vieja. Los filtros son opcionales. `estado`: `pendiente`, `confirmada` o `descartada`.

**Respuesta `200`:**
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

### 7.4 `POST /alertas/{id}/confirmar/` 👑

Publica la alerta en el portal. Solo funciona si está **pendiente**.

**Body:**
```json
{ "mensaje_publico": "Se espera un aumento de dengue en Puerto Vallarta en diciembre. Elimina recipientes con agua y usa repelente." }
```
`mensaje_publico` es obligatorio (máximo 2000 caracteres). Es lo que verá la población.

**Respuesta `200`:** la alerta completa, con `estado: "confirmada"`, `revisada_por` y `revisada_en`.
**Errores:** `404` si no existe · `409` si ya fue confirmada o descartada · `400` si falta el mensaje.

### 7.5 `POST /alertas/{id}/descartar/` 👑

No la publica. Sin body. Mismas respuestas que confirmar, con `estado: "descartada"`.

### 7.6 `GET /alertas-publicas/` 🔓

Para el portal. Solo alertas **confirmadas** y **del mes actual en adelante** (las de meses pasados ya no se muestran). **No incluye el motivo interno** ni quién la revisó.

**Respuesta `200`:**
```json
[
  {
    "id": 3, "enfermedad": "dengue", "enfermedad_nombre": "Dengue", "anio": 2026, "mes": 12,
    "mensaje_publico": "Se espera un aumento de dengue en la región costera...", "publicada_en": "2026-11-13T08:20:00-06:00"
  }
]
```

---

## 8. Mapa y estadísticas

### 8.1 `GET /mapa/?enfermedad=` 🔒

La predicción y la alerta de **toda la región**, más los municipios para dibujarla. `enfermedad` es **obligatoria**. Todos los municipios se pintan con el mismo nivel; el color lo decide la app con estos datos.

**Respuesta `200`:**
```json
{
  "enfermedad": "dengue",
  "prediccion": { "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46, "...": "..." },
  "casos_anio_anterior": 2,
  "alerta": { "id": 3, "estado": "pendiente" },
  "municipios": [
    { "clave_inegi": "14022", "nombre": "Cihuatlán", "region": "Costa Sur", "latitud": null, "longitud": null },
    { "clave_inegi": "14067", "nombre": "Puerto Vallarta", "region": "Costa-Sierra Occidental", "latitud": null, "longitud": null }
  ]
}
```
`prediccion`, `casos_anio_anterior` y `alerta` pueden venir en `null`. `alerta` solo considera las pendientes o confirmadas.

### 8.2 `GET /estadisticas/?enfermedad=&anio=&municipio=` 🔒

Endpoint general: **se le pasan las claves y regresa todo lo que haya**. Todos los parámetros son opcionales; si no se manda `anio`, usa el año actual.

| Se manda | Se recibe |
|---|---|
| `enfermedad=dengue&anio=2026` | Casos de dengue de la región por mes, clima por mes y la última predicción |
| `anio=2026` | Casos de todas las enfermedades, y el clima |
| `enfermedad=dm2` | Además, los datos de crónicas (DGE / INEGI) |
| `enfermedad=dm2&municipio=14067` | Crónicas de ese municipio más las estatales. **`municipio` solo afecta a las crónicas** |

**Respuesta `200`:**
```json
{
  "filtros": { "enfermedad": "dengue", "municipio": null, "anio": 2026 },
  "casos_por_mes": [ { "enfermedad": "dengue", "mes": 9, "casos": 14 } ],
  "clima_por_mes": [ { "mes": 9, "temperatura": 29.5, "humedad": 72.0, "precipitacion": 180.4 } ],
  "prediccion": { "anio": 2026, "mes": 12, "semanas": [1.2, 1.96, 0.8, 0.5], "total": 4.46, "...": "..." },
  "cronicas": null
}
```

| Bloque | Cuándo viene lleno |
|---|---|
| `casos_por_mes` | Siempre (lista vacía si no hay datos). Un mes que no aparece = sin dato, no 0 |
| `clima_por_mes` | Siempre (lista vacía si no hay datos) |
| `prediccion` | Solo si se manda `enfermedad` |
| `cronicas` | Solo si la enfermedad es de tipo `cronica`. No se filtra por año |

Cada registro de `cronicas` trae: `indicador` (`casos_nuevos`, `incidencia`, `mortalidad`, `prevalencia`), `ambito`, `municipio__clave_inegi`, `region`, `anio`, `sexo`, `grupo_edad`, `institucion`, `valor`, `unidad` (`casos`, `defunciones`, `tasa_100k`, `porcentaje`) y `fuente`.

**Errores:** `400` si una clave no existe o `anio` no es número.

### 8.3 `GET /estadisticas/encuesta/` 🔒

**Respuesta `200`:**
```json
{
  "total": 12,
  "por_municipio": [ { "municipio__clave_inegi": "14022", "municipio__nombre": "Cihuatlán", "respuestas": 7 } ]
}
```

---

## 9. Contenido y encuesta

### 9.1 `GET /contenido/?tipo=&enfermedad=` 🔓

Prevención fija, artículos y notas, del más nuevo al más viejo. Filtros opcionales: `tipo` (`prevencion`, `articulo`, `nota`) y `enfermedad` (clave).

- **Sin sesión** (portal): solo lo publicado.
- **Con sesión** (escritorio): también los borradores.

**Respuesta `200`:**
```json
[
  {
    "id": 5, "tipo": "prevencion", "enfermedad": "dm2", "titulo": "Cómo prevenir la diabetes",
    "cuerpo": "...", "url_fuente": "https://...", "imagen_url": "",
    "publicado": true, "autor": "Daniel", "fecha": "2026-11-13T08:00:00-06:00"
  }
]
```

### 9.2 `GET /contenido/{id}/` 🔓

Un contenido. Si es un borrador y se pide sin sesión: `404`.

### 9.3 `POST /contenido/` 👑

**Body:**
```json
{ "tipo": "articulo", "enfermedad": "dengue", "titulo": "Título", "cuerpo": "Texto", "url_fuente": "https://...", "publicado": false }
```

| Campo | Obligatorio | Regla |
|---|---|---|
| `tipo` | Sí | `prevencion`, `articulo` o `nota` |
| `titulo` | Sí | Máximo 200 caracteres |
| `cuerpo` | Sí | Texto libre |
| `enfermedad` | No | Clave, o `null` |
| `url_fuente`, `imagen_url` | No | URL válida |
| `publicado` | No | `false` por defecto (borrador) |

El `autor` se toma del token, no del body. **Respuesta `201`:** el contenido creado.

### 9.4 `PATCH /contenido/{id}/` 👑

Se manda **solo lo que cambia**. Ejemplo para publicar:
```json
{ "publicado": true }
```
**Respuesta `200`:** el contenido actualizado. (No existe `PUT`.)

### 9.5 `DELETE /contenido/{id}/` 👑

**Respuesta `204`**, sin cuerpo.

### 9.6 `POST /encuesta/` 🔓

Respuesta anónima del portal. No guarda nombre, correo ni ubicación exacta: solo el municipio.

**Body:**
```json
{ "municipio": "14022", "respuestas": { "tiene_diabetes": true, "edad": "25-44" }, "consentimiento": true }
```

| Campo | Regla |
|---|---|
| `municipio` | Clave existente |
| `respuestas` | Objeto con al menos una respuesta (las preguntas finales están pendientes) |
| `consentimiento` | Debe ser `true`; si no, se rechaza |

**Respuesta `201`:** los datos guardados.
**Límite:** 20 respuestas por hora por IP; después responde `429`.

---

## 10. Flujo completo

1. **Login:** el usuario de la organización inicia sesión con Firebase; la app consulta `GET /yo/` para saber su rol.
2. **Inicia la predicción:** carga el CSV/plantilla de la región (una fila por mes).
3. **Guardar datos:** la app (o el script del modelo) manda las filas a `POST /cargas/`. Quedan guardadas para las estadísticas.
4. **Modelo:** el modelo en Python lee ese mismo archivo y estima los casos de las 4 semanas del mes siguiente.
5. **Predicción:** manda el resultado a `POST /predicciones/`, con el token del usuario que la inició.
6. **Alerta automática:** el backend compara con el mismo mes del año anterior y, si sube, crea una alerta pendiente con su motivo.
7. **Revisión:** la organización ve la alerta en `GET /alertas/?estado=pendiente` y la confirma (con un mensaje para la población) o la descarta.
8. **Publicación:** la alerta confirmada aparece en el portal con `GET /alertas-publicas/`.
9. **Consulta:** la app muestra el mapa (`GET /mapa/`) y las gráficas (`GET /estadisticas/`), y administra artículos (`/contenido/`).
10. **Población:** el portal muestra prevención y artículos (`GET /contenido/`), las alertas vigentes, y recibe encuestas (`POST /encuesta/`), que la organización consulta en `GET /estadisticas/encuesta/`.

### Qué consume cada cliente

| Cliente | Endpoints |
|---|---|
| Modelo (Python) | `POST /cargas/`, `POST /predicciones/` |
| App de escritorio | `/yo/`, `/predicciones/` (GET), `/alertas/` (y confirmar/descartar), `/mapa/`, `/estadisticas/`, `/estadisticas/encuesta/`, `/contenido/` (todas), `/municipios/`, `/enfermedades/` |
| Portal web | `/alertas-publicas/`, `/contenido/` (solo lectura), `/municipios/`, `/enfermedades/`, `/encuesta/` |

---

## Anexo: pruebas

La colección de Postman `HackaJal_API.postman_collection.json` (en `docs/`) prueba los 19 endpoints: 21 pruebas del flujo completo y 17 de casos de error.
