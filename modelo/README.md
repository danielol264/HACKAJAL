# Modelo predictivo de dengue – Región Costa de Jalisco

Predice los casos de dengue de cada municipio de la Costa (14 municipios) para las próximas 4 semanas y asigna un nivel de riesgo (bajo, medio o alto). Orienta, no diagnostica.

- **Documentación completa:** [`docs/DOCUMENTACION_MODELO.md`](docs/DOCUMENTACION_MODELO.md)
- **Guía para conectar con la API y Firebase:** [`docs/GUIA_PARA_EL_CTO.md`](docs/GUIA_PARA_EL_CTO.md)

## Inicio rápido
```
pip install -r ../requirements.txt      # un solo entorno para todo el proyecto (requirements.txt de la raíz)
python codigo/generar_plantilla_mensual.py   # llena datos/plantilla_carga_mensual.xlsx con los datos semanales
python codigo/cliente_api.py --simular     # muestra la predicción que se enviaría, sin usar red
```
Para usar la API de verdad, `cliente_api.py` lee `API_URL` y `FIREBASE_API_KEY` del `.env` de la raíz del proyecto; agrega ahí `USUARIO_EMAIL` y `USUARIO_PASSWORD` (o defínelas como variables de entorno) y corre `python codigo/cliente_api.py`. Desde la app de escritorio no hace falta: *Predicciones → Ejecutar modelo* usa `codigo/predecir_json.py`.

## Contenido
`codigo/` (modelo y cliente de la API) · `pruebas/` (21 pruebas del modelo, 41 pruebas de la API según el contrato, API simulada) · `resultados/` (modelo guardado, métricas, predicciones, umbrales) · `datos/` (datos semanales de dengue y plantilla mensual) · `docs/`
