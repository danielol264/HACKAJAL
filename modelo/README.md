# Modelo predictivo de dengue – Región Costa de Jalisco

Predice los casos de dengue de cada municipio de la Costa (14 municipios) para las próximas 4 semanas y asigna un nivel de riesgo (bajo, medio o alto). Orienta, no diagnostica.

- **Documentación completa:** [`docs/DOCUMENTACION_MODELO.md`](docs/DOCUMENTACION_MODELO.md)
- **Guía para conectar con la API y Firebase:** [`docs/GUIA_PARA_EL_CTO.md`](docs/GUIA_PARA_EL_CTO.md)

## Inicio rápido
```
pip install -r requirements.txt
python codigo/cliente_api.py --simular     # muestra la predicción que se enviaría, sin usar red
```
Para usar la API de verdad, define `API_URL`, `FIREBASE_API_KEY`, `USUARIO_EMAIL` y `USUARIO_PASSWORD` como variables de entorno (nunca en el código) y corre `python codigo/cliente_api.py`.

## Contenido
`codigo/` (modelo y cliente de la API) · `pruebas/` (21 pruebas del modelo, 41 pruebas de la API según el contrato, API simulada) · `resultados/` (modelo guardado, métricas, predicciones, umbrales) · `datos/` (datos semanales de dengue y plantilla mensual) · `docs/`
