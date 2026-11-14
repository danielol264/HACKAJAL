# Documentación del modelo predictivo de dengue – Región Costa de Jalisco

Proyecto HackaJal, reto "Salud y Bienestar" (equipo Red Mind). Documento escrito el 13 de noviembre de 2026 y basado en el código y los resultados que están en este repositorio.

## 1. Qué es y para qué sirve

El modelo estima **cuántos casos de dengue habrá en cada municipio de la región Costa en cada una de las próximas 4 semanas**, y con eso asigna un **nivel de riesgo** (bajo, medio o alto) por municipio y semana.

Orienta decisiones (por ejemplo, dónde mandar brigadas o avisar a la población). **No diagnostica** y no sustituye el criterio de las autoridades de salud. La aplicación debe decirlo.

## 2. Ficha técnica

| Concepto | Valor |
|---|---|
| Enfermedad | Dengue |
| Región | Costa de Jalisco: 14 municipios (ver sección 4) |
| Qué predice | Casos nuevos por semana y por municipio |
| Hasta cuándo predice | 1, 2, 3 y 4 semanas después de la última semana completa de datos |
| Tipo de modelo | Gradient Boosting (clase `HistGradientBoostingRegressor` de scikit-learn) |
| Cantidad de modelos | 4: uno para cada cantidad de semanas adelante |
| Datos de entrenamiento | Casos semanales de los 125 municipios de Jalisco, de la semana del 29/12/2019 a la del 25/10/2026 (343 semanas, 42,875 filas) |
| Fuente de los datos | Datos abiertos de la Dirección General de Epidemiología (dengue 2020 a 2025, y 2026 con corte al 03/11/2026, descargado el 12/11/2026), archivo `datos/Dengue Clima Semanal.csv` |
| Variables que usa | 14, todas calculadas a partir de los casos pasados y de la semana del año (sección 6) |
| Clima | **No se usa** (sección 12) |
| Brigadas | **No se usan** (sección 12) |
| Archivo del modelo | `resultados/modelo_dengue_final.joblib` |
| Versiones con las que se creó | Python 3.13, scikit-learn 1.9.1, pandas 3.0.5, numpy 2.5.3, joblib 1.6.0 |

## 3. Los datos

El archivo `datos/Dengue Clima Semanal.csv` trae una fila por municipio y por semana. Columnas que usa el modelo:

| Columna | Qué significa |
|---|---|
| `clave_municipio` | Clave de 3 dígitos del municipio, escrita como texto ("067", no 67) |
| `municipio` | Nombre del municipio |
| `fecha_inicio_semana` | Domingo con el que empieza la semana |
| `semana_epi` | Número de semana epidemiológica |
| `anio` | Año de la semana |
| `casos` | Casos de dengue de ese municipio en esa semana |
| `posible_rezago` | "SI" en las últimas 3 semanas de cada año: esas semanas pudieron registrarse incompletas porque los casos se capturan con retraso |

Hechos importantes de los datos:
- Casos en todo Jalisco por año: 2020 = 16,061; 2021 = 1,428; 2022 = 673; 2023 = 2,679; **2024 = 70,624 (brote muy grande)**; 2025 = 10,454; **2026 = 2,230 (hasta el corte del 03/11/2026)**.
- **Las semanas con retraso de captura (`posible_rezago` = "SI") no se usan como respuesta correcta** al entrenar ni al evaluar, porque tienen menos casos de los que realmente hubo.
- El archivo también trae columnas de clima (`lluvia_mm`, `temp_max_c`, `temp_min_c`), pero son de estaciones del Norte de Jalisco y no representan a la Costa.
- Los datos terminan en la semana del 25/10/2026 (el archivo de 2026 tiene corte al 03/11/2026). Las últimas 3 semanas (11, 18 y 25 de octubre) están marcadas como posible retraso de captura. En años anteriores las últimas semanas sí salían más bajas de lo real; en 2026 no se nota esa caída (75, 81 y 81 casos en Jalisco contra unos 70 las semanas anteriores).
- Cada archivo anual termina antes de fin de año (por la fecha de corte), por eso la serie tiene huecos de algunas semanas entre un año y otro. Por ejemplo, faltan las semanas del 21 y 28 de diciembre de 2025.
- **Cómo se arma el archivo semanal.** `codigo/construir_datos_semanales.py` convierte la base abierta de un año en filas semanales por municipio: solo Jalisco, casos = registros probables (estatus 1) y confirmados (estatus 2) por semana de inicio de síntomas, confirmados = estatus 2, defunciones = casos con `DEFUNCION` = 1. Se comprobó que reproduce exactamente los datos de 2025 (6,375 filas, 0 diferencias).

## 4. La región Costa

La región se formó con la Costa-Sierra Occidental (8 municipios) y la Costa Sur (6), como la definieron el Product Owner y el CTO. Está escrita en `codigo/nucleo.py` (`REGION_COSTA`).

| Clave | Municipio | Clave | Municipio |
|---|---|---|---|
| 012 | Atenguillo | 021 | Casimiro Castillo |
| 020 | Cabo Corrientes | 022 | Cihuatlán |
| 038 | Guachinango | 027 | Cuautitlán de García Barragán |
| 058 | Mascota | 043 | La Huerta |
| 062 | Mixtlán | 100 | Tomatlán |
| 067 | Puerto Vallarta | **068** | Villa Purificación |
| 080 | San Sebastián del Oeste | | |
| 084 | Talpa de Allende | | |

**Errata a corregir en el sistema:** en la tabla que usó el equipo, Villa Purificación aparece con la clave 107. En los datos de la Dirección General de Epidemiología la 107 es Tuxcueca (que no es de la Costa) y la clave de Villa Purificación es **068**. Si la base de datos o la API usan 107, se estaría incluyendo a un municipio que no es de la Costa.

Aunque el modelo se entrena con los 125 municipios (aprende de más datos), **solo se evalúa y se entrega la Costa**.

## 5. Cómo funciona, paso a paso

1. **Se toma la semana de origen.** Para las evaluaciones y por omisión en `predecir.py` es la última semana completa (sin posible retraso de captura): hoy el 04/10/2026. Para alimentar la API (`cliente_api.py`, opción `--origen ultima`, la que se usa por omisión) es la **última semana con datos**, el 25/10/2026, aunque esté marcada como posible retraso; así la predicción cubre del 01/11/2026 al 22/11/2026 en lugar de semanas que ya pasaron. Si esa última semana estuviera incompleta, el modelo podría quedarse corto.
2. **Para cada municipio se calculan las 14 variables** con lo que había pasado hasta esa semana (sección 6).
3. **Cada uno de los 4 modelos contesta una pregunta**: "¿cuánto cambiarán los casos de este municipio dentro de 1, 2, 3 o 4 semanas, comparado con los casos de la semana de origen?".
4. **Se convierte esa respuesta en casos esperados.** El modelo no predice los casos directamente, predice el *cambio* respecto a la semana de origen en escala logarítmica, y después se regresa a casos con `casos_esperados = exp(cambio + log(1 + casos de origen)) - 1`, sin permitir valores negativos. Se eligió así porque:
   - un modelo que predice casos directamente se queda corto cuando viene un brote más grande que los que vio al aprender (en las pruebas con el brote de 2024 subestimaba mucho los casos, y predecir el cambio lo corrigió);
   - un modelo con distribución de Poisson se "explotaba" con el brote de 2024.
5. **Se comparan los casos esperados con los umbrales del municipio** y se asigna el nivel de riesgo (sección 9).

Para que el modelo no confunda escalas, los casos pasados entran como `log(1 + casos)`.

## 6. Las 14 variables

| Variable | Qué es |
|---|---|
| `casos_lag0` | Casos del municipio en la semana de origen |
| `casos_lag1`, `casos_lag2`, `casos_lag3` | Casos del municipio 1, 2 y 3 semanas antes |
| `casos_media4`, `casos_media8`, `casos_media12` | Promedio de casos de las últimas 4, 8 y 12 semanas |
| `casos_52sem` | Suma de casos de las 52 semanas anteriores (mínimo 8 semanas de historia) |
| `estado_lag0` | Casos de todo Jalisco en la semana de origen |
| `estado_media4` | Promedio de casos de todo Jalisco en las últimas 4 semanas |
| `costa_lag0` | Casos de toda la Costa en la semana de origen |
| `es_costa` | 1 si el municipio es de la Costa, 0 si no |
| `sem_sin`, `sem_cos` | La semana del año convertida en un círculo (seno y coseno), para que el modelo sepa en qué época del año está y entienda que la semana 52 queda junto a la 1 |

Todas las variables usan solo información **anterior o igual a la semana de origen**. El modelo nunca ve el futuro.

## 7. Entrenamiento

Parámetros (iguales para los 4 modelos):

| Parámetro | Valor | Para qué sirve |
|---|---|---|
| `loss` | squared_error | Se equivoca menos en promedio cuando la diferencia es grande |
| `max_iter` | 200 | Cantidad de árboles |
| `learning_rate` | 0.05 | Qué tanto corrige cada árbol |
| `max_depth` | 4 | Árboles pequeños para no memorizar |
| `min_samples_leaf` | 40 | Cada regla debe apoyarse en al menos 40 ejemplos |
| `l2_regularization` | 1.0 | Evita que el modelo se pase de confiado |
| `random_state` | 0 | Para que el resultado se pueda repetir |

El modelo final se entrenó con **todo el historial** disponible (2020 a 2026) de los 125 municipios, y se guardó en `resultados/modelo_dengue_final.joblib`. Dentro del archivo van los 4 modelos, la lista de variables, los parámetros, la lista de municipios de la Costa y las fechas de la última semana con datos y de la última sin retraso.

## 8. Cómo se evaluó y qué resultados dio

**Principio:** el modelo se prueba como se usaría en la vida real: aprende solo con el pasado y se le examina con un año que no vio. Nunca se mezclan fechas.

| Examen | Aprende con datos hasta | Se prueba con |
|---|---|---|
| 1 | 2022 | 2023 |
| 2 | 2023 | 2024 (año del brote) |
| 3 | 2024 | 2025 |
| 4 | 2025 | 2026 (año en curso, hasta el 04/10/2026) |

Las semanas con retraso de captura no se cuentan. Las medidas se calculan **solo en los 14 municipios de la Costa**.

**Se compara contra una referencia muy simple**, que no es un modelo: "copiar casos de esa semana", es decir, decir que dentro de 1, 2, 3 o 4 semanas habrá los mismos casos que en la semana de origen. Si el modelo no le gana a eso, no sirve.

**Dos medidas de error** (entre más chicas, mejor):
- *Error promedio en casos*: cuántos casos se equivoca el modelo, en promedio, por municipio y por semana.
- *Error comparado con los casos reales*: la suma de todos los errores entre la suma de los casos reales. Un 0.50 significa que el error total es la mitad de los casos que realmente hubo.

**Error comparado con los casos reales** (Costa; modelo elegido contra copiar casos de esa semana):

| Examen | Casos reales en la Costa | Modelo, 1 / 2 / 3 / 4 semanas | Copiar casos de esa semana, 1 / 2 / 3 / 4 semanas | Resultado |
|---|---|---|---|---|
| 2023 | 372 | 0.72 / 0.72 / 0.81 / 0.80 | 0.80 / 0.74 / 0.77 / 0.78 | Empate |
| 2024 (brote) | 5,688 | 0.31 / 0.40 / 0.45 / 0.49 | 0.27 / 0.34 / 0.40 / 0.47 | Gana copiar |
| 2025 | 1,712 | 0.66 / 0.71 / 0.80 / 0.92 | 0.70 / 0.80 / 1.07 / 1.35 | Gana el modelo, sobre todo a 3 y 4 semanas |
| 2026 (hasta el 04/10) | 296 | 0.58 / 0.68 / 0.67 / 0.70 | 0.61 / 0.67 / 0.68 / 0.68 | Empate |

**Error promedio en casos:**

| Examen | Modelo, 1 / 2 / 3 / 4 semanas | Copiar casos de esa semana, 1 / 2 / 3 / 4 semanas |
|---|---|---|
| 2023 | 0.40 / 0.40 / 0.45 / 0.44 | 0.44 / 0.41 / 0.43 / 0.43 |
| 2024 (brote) | 2.80 / 3.62 / 4.07 / 4.46 | 2.40 / 3.09 / 3.63 / 4.26 |
| 2025 | 1.68 / 1.80 / 2.03 / 2.34 | 1.79 / 2.04 / 2.74 / 3.44 |
| 2026 (hasta el 04/10) | 0.31 / 0.36 / 0.35 / 0.37 | 0.32 / 0.36 / 0.36 / 0.36 |

**Lectura honesta:**
- El modelo le gana claramente a la referencia solo en 2025, y mientras más lejos predice, más ventaja tiene. En 2026 (el examen más reciente, con el modelo entrenado hasta 2025) empata: gana por poco a 1 semana y queda igual o apenas peor a 2, 3 y 4 semanas.
- En 2023 empata y en el brote de 2024 pierde en todas las semanas.
- En la Costa los casos son pocos (372 en todo 2023), por eso los errores comparados con los casos reales son altos aunque el error en casos sea pequeño.
- El total de casos sale sesgado: se pasa en 2025 y se queda corto en 2023, 2024 y 2026 (en 2026 predice entre 243 y 275 casos contra 296 reales).
- Se comparó también el mismo modelo entrenado **solo con los 14 municipios de la Costa**. Quedó casi igual (a veces un poco mejor y a veces un poco peor), así que se eligió el entrenado con todo Jalisco porque aprende de más datos.

Todos los resultados completos están en `resultados/metricas_comparacion.csv`.

## 9. Reglas de alerta

Cada municipio tiene sus propios umbrales, calculados con su historia de casos por semana (sin semanas con retraso):

- **Medio**: casos esperados (redondeados) mayores o iguales al más grande entre 1 y el percentil 75 de sus casos semanales.
- **Alto**: casos esperados (redondeados) mayores o iguales al más grande entre 3, el percentil 90 de sus casos semanales y el umbral medio más 1.
- **Bajo**: todo lo demás.

Ejemplos de la Costa (casos esperados por semana, medio / alto): Puerto Vallarta 15 / 30; La Huerta 3 / 7; Cihuatlán 2 / 5; Cuautitlán de García Barragán 2 / 4; el resto 1 / 3. La tabla completa está en `resultados/umbrales_alerta.csv`.

El Product Owner aprobó esta regla de palabra, antes de que la región cambiara del Norte a la Costa. Conviene que la confirme de nuevo con los umbrales de la Costa.

## 10. Qué entrega el modelo

Un registro por municipio y por semana (14 municipios × 4 semanas = 56 filas), con el mismo formato del ejemplo del Sprint 1:

```json
{ "clave_municipio": "067", "municipio": "Puerto Vallarta", "fecha_inicio_semana": "2026-11-01",
  "semana_epi": 45, "enfermedad": "dengue", "casos_esperados": 11.9, "nivel_riesgo": "bajo",
  "tipo_registro": "PREDICCION_MODELO" }
```

Archivos: `resultados/predicciones_costa.csv` y `.json`. Con las predicciones actuales (del 01/11/2026 al 22/11/2026, hechas desde la semana del 25/10/2026) los 14 municipios salen en nivel bajo; el valor más alto es Puerto Vallarta con 11.9 casos esperados en la semana del 01/11 (su umbral de nivel medio es 15). Para toda la Costa suman 13.3, 12.1, 8.7 y 7.3 casos por semana. También hay `resultados/predicciones_estado.csv` con los 125 municipios.

## 11. Integración con la API

El archivo `codigo/cliente_api.py` conecta el modelo con la API del CTO. Usa las cuatro funciones que entregó el CTO y agrega la parte del modelo.

Flujo:

1. **Iniciar sesión** (Firebase): `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=API_KEY`. Devuelve un token que dura 1 hora.
2. **Cargar la plantilla mensual**: `POST /api/cargas/`. Guarda los datos para las estadísticas. Si una fila falla, no se guarda nada y la API dice qué fila corregir.
3. **Predecir** con el modelo.
4. **Enviar la predicción**: `POST /api/predicciones/` con `enfermedad`, `anio`, `mes` y `semanas` (4 números). La API responde con `total` y `alerta` (o `null`).

**Cómo se convierte la predicción del modelo a lo que pide la API.** La API recibe un solo dato por semana, para toda la región. El modelo predice por municipio, así que se **suman los casos esperados de los 14 municipios** semana por semana. El mes (`anio` y `mes`) es el mes en el que caen la mayoría de las 4 semanas predichas. Ejemplo con las predicciones actuales: `{"enfermedad": "dengue", "anio": 2026, "mes": 11, "semanas": [13.3, 12.1, 8.7, 7.3]}`.

Variables de entorno: `API_URL` (por omisión `http://127.0.0.1:8000/api`), `FIREBASE_API_KEY`, `USUARIO_EMAIL`, `USUARIO_PASSWORD`. **Nunca se escriben en el código ni se suben al repositorio.**

Cómo usarlo:
```
python codigo/cliente_api.py --simular        # no usa red, muestra lo que se enviaría
python codigo/cliente_api.py                   # flujo completo contra la API
```

Protecciones agregadas al cliente:
- **No envía una predicción de un mes que ya pasó** (la API crearía una alerta de un mes pasado). Con los datos actuales el mes predicho es noviembre de 2026, así que pasa; si los datos se quedan sin actualizar, el cliente se detiene y avisa. `--forzar` lo salta solo para pruebas.
- Si la carga falla, muestra la **fila de Excel** que hay que corregir (índice de la API + 2) y **no envía la predicción**.
- Los valores enteros (`anio`, `mes`, `casos_dengue`) se envían como enteros aunque haya celdas vacías en la plantilla. (Con la función original, una celda vacía en `casos_dengue` volvía los demás valores decimales como 9.0 y la API simulada del repositorio los rechazaba.)

Lo que se probó (13 de noviembre de 2026):
- Contra la **API simulada del repositorio** (`desktop/mock_api`, la misma que usa la aplicación de escritorio): inicio de sesión, carga de plantilla (con datos completos, con celdas vacías, con errores y como .csv), envío de la predicción, contraseña incorrecta y usuario de consulta (recibe 403, como debe).
- Contra una API simulada propia (`pruebas/api_simulada.py`): los mismos casos y además API apagada.
- **No se ha probado contra el backend real de Django**: en el repositorio la carpeta `backend/` solo tiene un archivo de relleno.

### La plantilla mensual (`datos/plantilla_carga_mensual.xlsx`)
Hoja `Datos`, una fila por mes para **toda la región** (no por municipio), con las columnas `anio`, `mes`, `casos_dengue`, `temperatura_c`, `humedad_pct` y `precipitacion_mm`. Se sube a `/api/cargas/` para las estadísticas.

**Importante: el modelo no lee esta plantilla.** El modelo trabaja con datos semanales por municipio y la plantilla es mensual y de toda la región; con esa plantilla no se pueden calcular las variables del modelo. Por eso el modelo predice con el archivo semanal `Dengue Clima Semanal.csv`. Ver sección 13.

## 12. Limitaciones

- **Sin clima.** El modelo no usa clima porque la única serie que hay es de estaciones del Norte. El código para usarlo existe (`variables_clima` en `nucleo.py`); falta tener datos de estaciones de la Costa.
- **Sin brigadas.** No hay historial real de brigadas (solo 10 registros simulados).
- **Datos con retraso.** Terminan el 25/10/2026 (corte del 03/11/2026). El modelo solo predice 4 semanas desde la última semana con datos, así que no puede predecir diciembre de 2026 hasta que haya datos de noviembre. Hay que actualizar el archivo cada mes (sección 16).
- **Pocos casos en la Costa.** Con pocos casos por semana, el error comparado con los casos reales es alto y las predicciones son poco precisas.
- **Brotes grandes.** En el brote de 2024 el modelo no le ganó a copiar la semana anterior.
- **El modelo orienta, no diagnostica.** Debe mostrarse como estimación.
- **Versión de scikit-learn.** El archivo `.joblib` se creó con scikit-learn 1.9.1. Si en otra computadora marca advertencia o error de versión, se vuelve a crear con `entrenar_modelo.py` (tarda unos minutos).

## 13. Decisiones abiertas

1. **Datos mensuales contra semanales.** La API y la plantilla son mensuales; el modelo es semanal. Hoy el modelo lee el archivo semanal y la plantilla solo alimenta las estadísticas. Si el CTO quiere que el modelo use lo que se cargue en la plantilla, hay que cambiar el modelo (un modelo mensual por región) o conseguir los casos semanales por municipio.
2. **Qué significa "con clima" en `semanas`.** La especificación de la API (`docs/API_ESCRITORIO.md`) dice que `semanas` son 4 números de casos estimados "con clima" de toda la región. Este modelo no usa clima. Hay que confirmar con el CTO que los 4 valores semanales de casos esperados son lo correcto.
3. **Qué mes enviar.** Se envía el mes en el que caen la mayoría de las 4 semanas. Confirmar si la API espera otra cosa (por ejemplo, el mes siguiente al último dato).
4. **Actualizar los datos.** Cada mes hay que bajar la base de dengue más reciente de la Dirección General de Epidemiología, reconstruir el archivo semanal y reentrenar (sección 16).
5. **Clima y brigadas** de la Costa (Sprint 2, tarjeta pendiente de decisión del Product Owner).
6. **Corregir las claves de municipios del catálogo.** Siete de las 14 claves del catálogo simulado del repositorio no coinciden con las oficiales de los datos (ver `docs/REVISION_REPOSITORIO.md`), y la tabla del equipo tenía la 107 para Villa Purificación cuando la correcta es 068.
7. **Confirmar los umbrales** de alerta de la Costa con el Product Owner.

## 14. Pruebas

- `pruebas/pruebas_modelo.py`: **21 pruebas del modelo, las 21 correctas** (10 casos correctos, 5 con municipio inexistente, 6 con datos vacíos). Resultado en `resultados/reporte_pruebas.csv`.
- `pruebas/probar_contrato_api.py`: **41 pruebas de la API según el contrato real** (`docs/API_ESCRITORIO.md`): 10 casos correctos, 5 de permisos (sin token, token falso, rol consulta), 9 con municipio, enfermedad o alerta inexistente y 17 con datos vacíos o inválidos. Por omisión solo lee; con `--escribir` también prueba las cargas y predicciones (usar solo con la API simulada o una base de pruebas). Contra la **API simulada del repositorio** dio 34 correctas y 7 fallas (resultado en `resultados/reporte_contrato_api_simulada.csv`): el catálogo de municipios tiene 7 claves distintas a las oficiales, acepta municipios inexistentes en `/estadisticas/`, acepta enfermedad inexistente y mes 13 en `/predicciones/`, rechaza casos enviados como `5.0` y se queda colgada con un JSON mal formado. **Falta correrlo contra el backend real.**
- `pruebas/probar_api.py`: pruebas para una ruta por municipio (`/api/.../{municipio}/`). El contrato actual no tiene esa ruta; se conserva por si el backend la agrega.
- Errores encontrados y corregidos durante las pruebas: casos en blanco (NaN) rompían la predicción; si faltaba la columna `casos` salía un error técnico en lugar de un mensaje claro.

## 15. Estructura de esta carpeta

```
modelo/
  README.md
  requirements.txt
  codigo/
    nucleo.py                         # región Costa, carga de datos, variables y medidas de error
    entrenar_modelo.py                # entrena, compara y guarda el modelo final
    predecir.py                       # predicciones por municipio y reglas de alerta
    cliente_api.py                    # integración con la API del CTO
    construir_datos_semanales.py      # convierte la base abierta de un año en filas semanales por municipio
    subir_predicciones_firebase.py    # carga de predicciones y umbrales a Firestore
  pruebas/
    pruebas_modelo.py                 # 21 pruebas del modelo
    probar_contrato_api.py            # 41 pruebas de la API según el contrato (correctos, inexistentes, vacíos)
    probar_api.py                     # pruebas para una ruta por municipio (el contrato actual no la tiene)
    api_simulada.py                   # API de mentira para probar el cliente
  resultados/                         # modelo, métricas, predicciones, umbrales, reporte de pruebas
  datos/                              # datos semanales y plantilla mensual
  docs/                               # esta documentación y la guía para el CTO
```

## 16. Cómo reproducir todo y cómo actualizar los datos

Actualizar con una base nueva de dengue (por ejemplo, la del 12/12/2026), desde la carpeta `modelo`:
```
python codigo/construir_datos_semanales.py "ruta/base_dengue_nueva.csv" "datos/Dengue Clima Semanal.csv" "datos/Dengue Clima Semanal NUEVO.csv"
```
Revisa el resumen que imprime (semanas, casos) y, si está bien, reemplaza `datos/Dengue Clima Semanal.csv` por el nuevo. Para comprobar el método con un año ya cargado, agrega `--validar` en lugar de la ruta de salida. Después:
```
pip install -r requirements.txt
python codigo/entrenar_modelo.py "datos/Dengue Clima Semanal.csv" resultados     # entrena y guarda el modelo y las métricas
python codigo/predecir.py "datos/Dengue Clima Semanal.csv" resultados/modelo_dengue_final.joblib resultados --origen-ultima
python pruebas/pruebas_modelo.py "datos/Dengue Clima Semanal.csv" resultados/modelo_dengue_final.joblib resultados/reporte_pruebas.csv
python codigo/cliente_api.py --simular
```
Sin `--origen-ultima`, `predecir.py` parte de la última semana completa (más segura, pero con semanas más viejas). Cada comando se corre desde la carpeta `modelo`.
