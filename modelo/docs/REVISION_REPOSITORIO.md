# Revisión del repositorio HACKAJAL (13 de noviembre de 2026)

Revisado: la rama `main` clonada (commit `d33c203`) y las ramas `origin/main` y `origin/doray`. Se leyeron `README.md`, los cuatro documentos de `docs/`, la aplicación de escritorio y su API simulada, y se corrió esa API simulada contra el cliente del modelo (`codigo/cliente_api.py`).

## 1. Qué hay en el repositorio
| Carpeta | Contenido |
|---|---|
| `desktop/` | Aplicación de escritorio (Python, PySide6) con 69 pruebas y una **API simulada** (`desktop/mock_api`) que imita el contrato |
| `frontend/` | Portal web (React y Vite) con sus propios datos de demostración |
| `docs/` | `API_ESCRITORIO.md` (contrato exacto), `INTEGRACION_BACKEND.md`, `REQUISITOS_BACKEND.md`, `ENTREGA_FINAL.md` |
| `backend/`, `confg/`, `modelo/`, `frontend/uixusuario/`, `frontend/uixpoblacioncivil/` | **Solo un archivo de relleno (`p1.txt`)**: están vacías |

**El backend de Django todavía no está en el repositorio**, así que no se pudo probar contra él. La carpeta `modelo/` está esperando el contenido de este modelo.

## 2. Cómo encaja el modelo
Según `API_ESCRITORIO.md`: el usuario sube la plantilla mensual (`POST /cargas/`), un modelo en Python predice las 4 semanas del mes siguiente (`POST /predicciones/`), y el backend compara el total con el mismo mes del año anterior; si sube (o no hay dato), crea una alerta pendiente que la organización confirma o descarta. Todo es de **toda la región costera**, no por municipio. `ENTREGA_FINAL.md` dice que no se entregó ningún modelo ni interfaz ejecutable: eso es lo que cubre `codigo/cliente_api.py`.

## 3. Lo que funcionó
Con la API simulada del repositorio, el flujo completo funciona: iniciar sesión → cargar plantilla → enviar las 4 semanas → la API responde `total` y `alerta` pendiente. El usuario de consulta recibe 403 y la contraseña incorrecta recibe 400, como dice el contrato.

## 4. Problemas encontrados
1. **Siete claves de municipio del catálogo simulado no coinciden con las oficiales.** Las claves oficiales salen de los datos de la Dirección General de Epidemiología (se comprobó por nombre). Si el catálogo real se llena con las claves simuladas, los municipios quedarían mal identificados (por ejemplo, 14056 es Santa María del Oro, no La Huerta).

| Municipio | Clave en el catálogo simulado | Clave oficial |
|---|---|---|
| Guachinango | 14037 | **14038** |
| Mixtlán | 14061 | **14062** |
| San Sebastián del Oeste | 14079 | **14080** |
| Talpa de Allende | 14106 | **14084** |
| La Huerta | 14056 | **14043** |
| Tomatlán | 14101 | **14100** |
| Villa Purificación | 14113 | **14068** |

Las otras siete (Atenguillo 14012, Cabo Corrientes 14020, Casimiro Castillo 14021, Cihuatlán 14022, Cuautitlán de García Barragán 14027, Mascota 14058 y Puerto Vallarta 14067) coinciden. La tabla de regiones del equipo traía además 107 para Villa Purificación.

2. **La función `leer_plantilla` del CTO manda decimales donde la API pide enteros.** Si hay una celda vacía en `casos_dengue`, pandas convierte la columna a decimales y envía `9.0`. La API simulada lo rechaza ("Debe ser un entero mayor o igual a 0"). Se corrigió en `cliente_api.py` (función `_registros`). Conviene que el backend real acepte ambos.
3. **Riesgo de alerta de un mes pasado.** Si los datos se quedan sin actualizar, la predicción sería de un mes que ya pasó y la API crearía una alerta pendiente de ese mes. El cliente se detiene en ese caso (`--forzar` solo para pruebas). Con los datos de 2026 cargados (corte del 03/11/2026) la predicción es de noviembre de 2026 y pasa.
4. **La API simulada siempre crea alerta**, porque compara contra un valor fijo (2 casos del año anterior). No sirve para probar la regla real de alerta; eso hay que probarlo con el backend de Django.
5. **Los documentos traen credenciales de demostración distintas.** `README.md` y `ENTREGA_FINAL.md` mencionan `admin@hackajal.gob.mx` y `Admin2026!`; la API simulada acepta `admin@hackajal.salud.gob.mx` con `AdminPassword123!` (y `admin@correo.com` con `admin123`). Conviene unificarlas.
6. **El modelo no usa clima**, pero el contrato describe las semanas como casos estimados "con clima". Confirmar con el CTO.

## 5. Lo que falta para cerrar la integración
- Que el CTO suba el backend de Django al repositorio (o dé la URL), la clave web de Firebase y un usuario `admin` de prueba.
- Probar `cliente_api.py` contra ese backend (y correr `pruebas/probar_api.py` si hay rutas por municipio).
- Datos semanales de dengue de 2026 para que la predicción sea del mes siguiente real.
- Decidir si el modelo se ejecuta a mano, programado, o dentro del servidor.
