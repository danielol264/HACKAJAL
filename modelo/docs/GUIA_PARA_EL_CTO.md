# Guía para el CTO – cómo usar el modelo de la Costa en la API y en Firebase

Todo lo de esta guía está en `Hackaton Jalisco\Sprint 2` (código en `codigo`, resultados en `resultados`).

## 1. La región Costa (14 municipios)
Costa-Sierra Occidental (8) + Costa Sur (6), tal como la definió el equipo.

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

**Ojo con una errata:** en la tabla que usó el equipo, Villa Purificación aparece con la clave **107**. En los datos de la Dirección General de Epidemiología la **107 es Tuxcueca** y la de Villa Purificación es **068**. Si el backend o la base usan 107, se estaría incluyendo a Tuxcueca (que no es de la Costa) y faltaría Villa Purificación.
Las claves son texto de 3 dígitos ("067", no 67).

## 2. Formato de las predicciones (mismo contrato del mock del sprint 1)
Archivo `resultados/predicciones_costa.json` (también `.csv`). Cada elemento de `predicciones`:
```
{ "clave_municipio": "067", "municipio": "Puerto Vallarta", "fecha_inicio_semana": "2026-11-01",
  "semana_epi": 45, "enfermedad": "dengue", "casos_esperados": 11.9, "nivel_riesgo": "bajo",
  "tipo_registro": "PREDICCION_MODELO" }
```
- 14 municipios x 4 semanas = 56 filas. `nivel_riesgo` es "bajo", "medio" o "alto". `casos_esperados` tiene 1 decimal.
- `predicciones_estado.csv` trae los 125 municipios (500 filas) por si se necesita.
- Los umbrales de cada municipio están en `resultados/umbrales_alerta.csv` (`umbral_medio`, `umbral_alto`).
- El modelo orienta, no diagnostica: la app debe decirlo.

## 3. Cómo guardarlas en Firebase (Cloud Firestore)
Está listo `codigo/subir_predicciones_firebase.py`:
```
pip install firebase-admin
python codigo\subir_predicciones_firebase.py resultados --simular
python codigo\subir_predicciones_firebase.py resultados --credenciales C:\ruta\llave.json
```
- Crea la colección `predicciones` (id: `067_2026-11-01_dengue`, así no se duplica al volver a correrlo) y la colección `umbrales_alerta` (id: la clave del municipio).
- **No se ha probado contra un Firebase real**: no tenemos las llaves. El modo `--simular` sí se probó y muestra lo que escribiría.
- Las llaves de Firebase nunca se suben a GitHub ni a Drive.
- Si prefieren otra estructura de colecciones, es cambiar ese archivo; dime cuál.

## 4. Cómo probar la API (según el contrato)
Con `pruebas/probar_contrato_api.py` se hacen 41 pruebas de los endpoints de `docs/API_ESCRITORIO.md`: casos correctos, permisos (401 y 403), municipio o enfermedad inexistente y datos vacíos o inválidos. Ejemplo:
```
set USUARIO_EMAIL=admin@correo.com
set USUARIO_PASSWORD=...
set CONSULTA_EMAIL=consulta@correo.com
set CONSULTA_PASSWORD=...
set FIREBASE_API_KEY=...
python pruebas\probar_contrato_api.py --url http://127.0.0.1:8000/api
```
- **Por omisión solo lee.** Con `--escribir` también prueba `/cargas/` y `/predicciones/`, que **reemplazan la predicción vigente y crean una alerta pendiente**: úsalo solo con una base de pruebas.
- Regla general: **nunca un error 500 ni una página de error técnico.** Cada falla se convierte en una tarjeta Bug (el programa imprime el texto sugerido).
- Contra la API simulada del repositorio dio 34 correctas y 7 fallas (ver `resultados/reporte_contrato_api_simulada.csv`); contra el backend real todavía no se ha corrido.

## 5. Cómo se actualizan las predicciones
Con datos nuevos de dengue (la tabla semanal por municipio, mismo formato de `Dengue Clima Semanal.csv`):
```
python codigo\predecir.py "Dengue Clima Semanal.csv" resultados\modelo_dengue_final.joblib resultados
```
Genera de nuevo `predicciones_costa.csv/json`, `predicciones_estado.csv` y `umbrales_alerta.csv`.
Hoy los datos llegan a la semana del 25/10/2026 (corte del 03/11/2026) y las predicciones son del 01/11/2026 al 22/11/2026.
