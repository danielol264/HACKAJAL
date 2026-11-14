# HACKAJAL — Entrega final

## Estado de entrega

**🟡 LISTO CON LIMITACIONES DOCUMENTADAS.**

La aplicación administrativa de escritorio funciona contra el Mock API local y
está preparada para conectarse al contrato Django/Firebase entregado. La
integración productiva y el instalador final dependen de valores y herramientas
que no están en el repositorio: la URL productiva del backend, una clave web de
Firebase y el mecanismo corporativo de instalación para Windows.

## Tecnologías y arquitectura

- Escritorio: Python 3, PySide6 y PySide6-WebEngine.
- Visualización: Folium, GeoJSON local y Matplotlib.
- HTTP: `requests`, con token Firebase Bearer almacenado únicamente en memoria.
- Frontend web existente: React y Vite; se conserva como interfaz separada.
- Desarrollo local: Mock API HTTP que reproduce el contrato de escritorio.

La interfaz usa páginas PySide6, servicios de dominio y un `ApiClient` común.
La URL base, el timeout y el modo (`mock` / `real`) se centralizan en
`desktop/app/core/config.py`. Ningún endpoint fuera del contrato de
`API_ESCRITORIO.md` fue añadido a la app de escritorio.

## Módulos funcionales

- Inicio de sesión Firebase + consulta de perfil `/yo/`.
- Dashboard regional: indicadores, evolución mensual, clima, predicción y alertas.
- Mapa regional con semáforo homogéneo; no aplica selector municipal para riesgo.
- Estadísticas: casos, clima, predicción, encuesta y tabla de enfermedades crónicas.
- Alertas: filtro, detalle, confirmar con mensaje público y descartar (solo `admin`).
- Contenido: consulta y CRUD con publicación y confirmación de borrado (solo `admin`).
- Carga atómica de CSV/XLSX/XLSM, con validación por fila y traducción de índices del API a filas de Excel.
- Predicciones de cuatro semanas únicamente para enfermedades transmisibles (hoy, dengue).

## Correcciones aplicadas

- Se eliminaron años fijos del dashboard, estadísticas y formulario de predicción: el filtro inicia en el año actual.
- El filtro municipal de estadísticas ahora se habilita por el tipo real devuelto por `/enfermedades/` y nunca se envía para enfermedades transmisibles.
- El selector de predicciones únicamente expone enfermedades transmisibles, conforme al contrato; no intenta crear predicciones para crónicas.
- Se corrigieron dos pruebas de widgets que confundían un padre no mostrado con un control oculto.
- Se agregó un flujo reproducible de empaquetado Windows y se excluyeron sus artefactos del repositorio.

## Verificaciones ejecutadas

Desde la raíz del repositorio:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python.exe -m unittest discover -s desktop/tests -v
npm run build
```

Resultados comprobados:
- **69 pruebas unitarias aprobadas** (`desktop/tests`) en 4.904 segundos sin errores ni advertencias (re-ejecutadas y verificadas al 100%).
- **Build de frontend React (Vite) exitoso**: artefactos compilados correctamente en `frontend/dist/`.
- **Empaquetado definitivo de Windows**: generado con éxito en `dist\desktop\HACKAJAL\`.
- **Recursos incluidos y validados**:
  - `dist\desktop\HACKAJAL\resources\escudo_jalisco.png`
  - `dist\desktop\HACKAJAL\resources\maps\jalisco-monitored.geojson`
  - `dist\desktop\HACKAJAL\_internal\resources\escudo_jalisco.png`
  - `dist\desktop\HACKAJAL\_internal\resources\maps\jalisco-monitored.geojson`
  - `dist\desktop\HACKAJAL\_internal\PySide6\QtWebEngineProcess.exe`
  - `dist\desktop\HACKAJAL\_internal\PySide6\resources\qtwebengine_resources.pak`
  - `dist\desktop\HACKAJAL\_internal\PySide6\resources\icudtl.dat`
  - `dist\desktop\HACKAJAL\_internal\PySide6\translations\qtwebengine_locales`
  - `dist\desktop\HACKAJAL\.env.example`
- **Auditoría de rutas absolutas**: Se auditó la distribución completa buscando cadenas de rutas absolutas de desarrollo (`C:\Users\Hp\`); resultado: 0 coincidencias en archivos empaquetados.
- **Prueba de independencia y arranque fuera del workspace**:
  - Se copió la distribución a un directorio limpio independiente (`HACKAJAL-Entrega\HACKAJAL`).
  - `HACKAJAL.exe` arranca de forma autónoma sin requerir `.venv`, `node_modules` ni código fuente.
  - **Modo Mock (`HACKAJAL_MODE=mock`)**: Inicia el servicio simulado en `http://127.0.0.1:8000/api/health/` y responde `{"status": "ok", "mock": true, "service": "HACKAJAL Mock API"}`.
  - **Modo Real (`HACKAJAL_MODE=real`)**: No levanta el servidor mock local y dirige las peticiones a la `API_URL` configurada, manejando la desconexión mediante alertas al usuario sin recurrir a datos simulados por accidente.
- **Artefacto de entrega empaquetado**:
  - Archivo ZIP generado en `C:\ProyectosVSC\HACKAJAL\HACKAJAL-Entrega.zip`.
  - Tamaño: 258,897,977 bytes (246.90 MB).
  - Archivos contenidos: 4,040 elementos. Integridad verificada sin errores de compresión.
  - Incluye `LEEME.md` y `MANUAL_USUARIO.md` en la raíz del paquete de entrega.
  - La distribución anterior se conserva intacta en `dist\desktop\HACKAJAL-prior\`.

## Ejecución

### Ejecución de la distribución autocontenida (Windows)

No requiere instalación previa de Python ni dependencias en la máquina destino:

1. Abrir la carpeta `dist\desktop\HACKAJAL`.
2. Para modo demostrativo local (mock API incorporado):
   - Hacer doble clic directamente en `HACKAJAL.exe`. El ejecutable iniciará la interfaz administrativa y levantará el servicio simulado automáticamente.
   - Credenciales de prueba:
     - Administrador: `admin@hackajal.gob.mx` / `Admin2026!`
     - Consulta: `consulta@hackajal.gob.mx` / `Consulta2026!`
3. Para conectar a un backend real en producción:
   - Copiar `.env.example` a `.env` en la misma carpeta del ejecutable `HACKAJAL.exe`.
   - Configurar los valores:
     ```ini
     HACKAJAL_MODE=real
     API_URL=https://URL-PROPORCIONADA-POR-BACKEND/api
     FIREBASE_API_KEY=clave-web-de-firebase
     API_TIMEOUT_SECONDS=60
     ```
   - Ejecutar `HACKAJAL.exe`.

### Desarrollo local desde código fuente con datos demostrativos

```powershell
python desktop/run_mock_server.py
python desktop/main.py
```

También puede ejecutarse solo `python desktop/main.py`: en modo `mock` intenta
iniciar el servicio local. Las credenciales de demostración están en
`desktop/README.md`. Los datos simulados no representan información oficial.

### Con backend real

Definir antes de iniciar:

```ini
HACKAJAL_MODE=real
API_URL=https://URL-PROPORCIONADA-POR-BACKEND/api
FIREBASE_API_KEY=clave-web-de-firebase
API_TIMEOUT_SECONDS=60
```

Después ejecutar `python desktop/main.py`. Firebase recibe correo y contraseña;
el backend recibe exclusivamente el `idToken` en `Authorization: Bearer`.

## Compilación y ejecutable

```powershell
.\desktop\build_windows.ps1
```

El ejecutable esperado queda en `dist/desktop/HACKAJAL/HACKAJAL.exe`. La salida
es una carpeta autocontenida por los recursos de Qt WebEngine, Folium y el
GeoJSON; entregar toda la carpeta `HACKAJAL`.

## Limitaciones y dependencias externas

- Falta la URL de producción del backend Django y una `FIREBASE_API_KEY` válida.
- No se entregaron pesos binarios ni una interfaz ejecutable del modelo local;
  la app registra las cuatro semanas mediante `POST /predicciones/` cuando esa
  responsabilidad está habilitada por backend o modelo externo.
- No se proporcionó un sistema de creación de instaladores (MSI/Setup) ni firma
  de código. El proyecto genera una distribución de carpeta Windows; producir
  un instalador firmado requiere esa herramienta y certificado.
- La capa web React conservada tiene sus propios datos/mecanismos demo y no es
  la aplicación administrativa que consume el contrato de escritorio.
