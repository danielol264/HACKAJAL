# Especificación del backend para el PORTAL WEB (React) — HackaJal

> **Instrucciones para la IA que lea este documento**
> - Este es el contrato **exacto** del backend. No inventes endpoints, campos, parámetros ni formatos que no estén aquí.
> - El portal web **no tiene login**: ninguna petición lleva token ni encabezado `Authorization`.
> - El portal web **solo** puede usar los 6 endpoints de este documento. No uses otros (mapa, estadísticas, alertas internas, cargas, predicciones son de otra app y responden 401).
> - Los municipios y enfermedades se identifican **por clave** (texto), nunca por id numérico.
> - Si algo no está definido aquí, pregunta al equipo de backend en lugar de suponer.

---

## 1. Contexto del proyecto

Hackatón de Jalisco. Sistema de predicción epidemiológica para la **región costera de Jalisco** (14 municipios). Por ahora solo se predice **dengue**.

- Un modelo predice los casos de dengue de las próximas 4 semanas para toda la región.
- Si los casos estimados superan a los del mismo mes del año anterior, se genera una alerta.
- Una organización de salud revisa la alerta en una app de escritorio y, si la **confirma**, se publica en este portal.

**El portal web es para la población general y tiene 3 secciones:**
1. **Alertas**: avisos confirmados por las organizaciones.
2. **Información de salud**: prevención (diabetes, hipertensión, obesidad, dengue, etc.) y artículos o notas.
3. **Encuesta**: anónima; sus respuestas se usan para estadísticas.

---

## 2. Datos técnicos

| Concepto | Valor |
|---|---|
| URL base local | `http://127.0.0.1:8000/api` |
| URL base producción | Pendiente (usar variable de entorno, ej. `VITE_API_URL`) |
| Formato | JSON. En POST: `Content-Type: application/json` |
| Autenticación | **Ninguna** |
| Idioma de los mensajes de error | Español |
| Fechas | ISO 8601, ej. `"2026-11-13T08:20:00-06:00"` |
| CORS | El backend solo acepta el dominio del portal configurado en `CORS_ALLOWED_ORIGINS`. En desarrollo: `http://localhost:5173` (Vite). Si React corre en otro puerto, avisar al backend |

**Todas las URLs terminan en `/`.** Sin la diagonal final, Django responde error.

---

## 3. Endpoints

| # | Método | Ruta | Para qué |
|---|---|---|---|
| 1 | GET | `/alertas-publicas/` | Alertas vigentes |
| 2 | GET | `/contenido/` | Lista de prevención, artículos y notas |
| 3 | GET | `/contenido/{id}/` | Un artículo completo |
| 4 | GET | `/municipios/` | Selector de municipio (encuesta) |
| 5 | GET | `/enfermedades/` | Filtro por enfermedad (información de salud) |
| 6 | POST | `/encuesta/` | Enviar respuesta de la encuesta |

---

### 3.1 `GET /alertas-publicas/`

Alertas **confirmadas** y **vigentes** (del mes actual en adelante). Ordenadas por año y mes, de la más próxima a la más lejana. Si no hay ninguna, regresa `[]`.

**Parámetros:** ninguno.

**Respuesta `200`:**
```json
[
  {
    "id": 3,
    "enfermedad": "dengue",
    "enfermedad_nombre": "Dengue",
    "anio": 2026,
    "mes": 12,
    "mensaje_publico": "Se espera un aumento de dengue en la región costera en diciembre. Elimina recipientes con agua y usa repelente.",
    "publicada_en": "2026-11-13T08:20:00-06:00"
  }
]
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | entero | Identificador de la alerta |
| `enfermedad` | texto | Clave (`"dengue"`) |
| `enfermedad_nombre` | texto | Nombre para mostrar |
| `anio`, `mes` | entero | Mes al que aplica la alerta (`mes` de 1 a 12) |
| `mensaje_publico` | texto | **El texto que se muestra a la población** |
| `publicada_en` | fecha | Cuándo se publicó |

La alerta es de **toda la región costera**, no de un municipio en particular.

---

### 3.2 `GET /contenido/`

Lista de contenido **publicado**, del más nuevo al más viejo. Si no hay, regresa `[]`.

**Parámetros opcionales (query):**

| Parámetro | Valores | Ejemplo |
|---|---|---|
| `tipo` | `prevencion`, `articulo`, `nota` | `/contenido/?tipo=prevencion` |
| `enfermedad` | clave de enfermedad | `/contenido/?tipo=prevencion&enfermedad=dm2` |

**Respuesta `200`:**
```json
[
  {
    "id": 5,
    "tipo": "prevencion",
    "enfermedad": "dm2",
    "titulo": "Cómo prevenir la diabetes",
    "cuerpo": "Texto completo del contenido...",
    "url_fuente": "https://www.gob.mx/salud",
    "imagen_url": "",
    "publicado": true,
    "autor": "Daniel",
    "fecha": "2026-11-13T08:00:00-06:00"
  }
]
```

| Campo | Tipo | Notas |
|---|---|---|
| `id` | entero | Para abrir el detalle |
| `tipo` | texto | `prevencion` = información fija de salud · `articulo` = artículo científico · `nota` = nota corta |
| `enfermedad` | texto o `null` | Clave de la enfermedad, o `null` si es general |
| `titulo` | texto | |
| `cuerpo` | texto | Texto plano (no HTML). Respetar saltos de línea |
| `url_fuente` | texto | Puede venir vacío `""` |
| `imagen_url` | texto | Puede venir vacío `""`; si viene vacío, no mostrar imagen |
| `publicado` | booleano | En el portal siempre es `true` |
| `autor` | texto o `null` | Puede ser `null` |
| `fecha` | fecha | |

---

### 3.3 `GET /contenido/{id}/`

Un contenido completo. Mismo formato que un elemento de la lista anterior.

**Errores:** `404` si no existe o no está publicado → mostrar "Contenido no disponible".

---

### 3.4 `GET /municipios/`

**Respuesta `200`:**
```json
[
  { "clave_inegi": "14020", "nombre": "Cabo Corrientes", "region": "Costa-Sierra Occidental", "latitud": null, "longitud": null },
  { "clave_inegi": "14067", "nombre": "Puerto Vallarta", "region": "Costa-Sierra Occidental", "latitud": null, "longitud": null }
]
```

En el selector se **muestra** `nombre` y se **envía** `clave_inegi`. Vienen ordenados por nombre. Son 14:

| Región | Municipios |
|---|---|
| Costa Sur | Casimiro Castillo, Cihuatlán, Cuautitlán de García Barragán, La Huerta, Tomatlán, Villa Purificación |
| Costa-Sierra Occidental | Atenguillo, Cabo Corrientes, Guachinango, Mascota, Mixtlán, Puerto Vallarta, San Sebastián del Oeste, Talpa de Allende |

---

### 3.5 `GET /enfermedades/`

**Respuesta `200`:**
```json
[
  { "clave": "dengue", "nombre": "Dengue", "tipo": "transmisible" },
  { "clave": "dm2", "nombre": "Diabetes mellitus tipo 2", "tipo": "cronica" },
  { "clave": "has", "nombre": "Hipertensión arterial", "tipo": "cronica" },
  { "clave": "obesidad", "nombre": "Obesidad", "tipo": "cronica" }
]
```
Claves actuales: `dengue`, `zika`, `chikungunya`, `dm1`, `dm2`, `has`, `obesidad`. Se muestra `nombre` y se filtra con `clave`.

---

### 3.6 `POST /encuesta/`

Respuesta **anónima**. No se piden ni se envían nombre, correo, teléfono ni ubicación GPS.

**Body:**
```json
{
  "municipio": "14022",
  "respuestas": { "tiene_diabetes": true, "edad": "25-44" },
  "consentimiento": true
}
```

| Campo | Tipo | Regla |
|---|---|---|
| `municipio` | texto | `clave_inegi` de uno de los 14 municipios |
| `respuestas` | objeto | Al menos una respuesta. **Las preguntas finales aún no están definidas** (las define P1); por ahora se mandan como pares `clave: valor` |
| `consentimiento` | booleano | Debe ser `true`. Mostrar un checkbox obligatorio de aceptación antes de enviar |

**Respuesta `201`:** regresa lo enviado. Mostrar "¡Gracias por responder!".

**Errores:**

| Código | Ejemplo de respuesta | Qué mostrar |
|---|---|---|
| `400` | `{"consentimiento": ["Se requiere el consentimiento para guardar la respuesta."]}` | El mensaje del campo |
| `400` | `{"municipio": ["Objeto con clave_inegi=99999 no existe."]}` | "Selecciona un municipio válido" |
| `400` | `{"respuestas": ["Debe ser un objeto con al menos una respuesta."]}` | "Responde al menos una pregunta" |
| `429` | `{"detail": "..."}` | "Demasiados envíos, intenta más tarde" (límite: 20 por hora por IP) |

---

## 4. Formato general de errores

- Error por campo: `{"campo": ["mensaje"]}`.
- Error general: `{"detail": "mensaje"}`.
- `500` o sin conexión: mostrar "No se pudo conectar con el servidor".

---

## 5. Código base sugerido (React)

```js
// src/api.js
const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`${API}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  const datos = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw { status: r.status, datos };
  return datos;
}

export const obtenerAlertas = () => pedir("/alertas-publicas/");
export const obtenerContenido = (filtros = {}) =>
  pedir(`/contenido/?${new URLSearchParams(filtros)}`);           // { tipo, enfermedad }
export const obtenerArticulo = (id) => pedir(`/contenido/${id}/`);
export const obtenerMunicipios = () => pedir("/municipios/");
export const obtenerEnfermedades = () => pedir("/enfermedades/");
export const enviarEncuesta = (municipio, respuestas) =>
  pedir("/encuesta/", {
    method: "POST",
    body: JSON.stringify({ municipio, respuestas, consentimiento: true }),
  });
```

Archivo `.env` del proyecto de React:
```
VITE_API_URL=http://127.0.0.1:8000/api
```

---

## 6. Resumen de pantallas

| Pantalla | Endpoints |
|---|---|
| Inicio / Alertas | `GET /alertas-publicas/` |
| Información de salud (prevención) | `GET /contenido/?tipo=prevencion`, filtro con `GET /enfermedades/` |
| Artículos y notas | `GET /contenido/?tipo=articulo` y `?tipo=nota` |
| Detalle | `GET /contenido/{id}/` |
| Encuesta | `GET /municipios/` + `POST /encuesta/` |
