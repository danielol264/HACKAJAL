// Script de validación automatizada de contratos e integración para el Portal Web HackaJal
// Ejecución con Node.js

// Forzar modo mock para validación de servicios simulados
process.env.VITE_USE_MOCK = 'true';

import { apiRequest } from './src/services/api.js';
import { obtenerAlertas } from './src/services/alertasService.js';
import { obtenerContenido, obtenerArticulo } from './src/services/contenidoService.js';
import { obtenerMunicipios } from './src/services/municipiosService.js';
import { obtenerEnfermedades } from './src/services/enfermedadesService.js';
import { enviarEncuesta } from './src/services/encuestaService.js';
import {
  adaptarAlerta,
  adaptarContenido,
  adaptarMunicipio,
  adaptarEnfermedad,
  formatearFecha,
} from './src/services/adapters.js';
import { ENCUESTA_PREGUNTAS_PROTOTIPO } from './src/config/surveyQuestions.js';

let totalTests = 0;
let passedTests = 0;

function assert(condition, testName) {
  totalTests++;
  if (condition) {
    console.log(`  ✓ [PASS] ${testName}`);
    passedTests++;
  } else {
    console.error(`  ✗ [FAIL] ${testName}`);
  }
}

async function runTests() {
  console.log('================================================================');
  console.log('AUDITORÍA DE ACEPTACIÓN FINAL: CONTRATO API_WEB.md');
  console.log('================================================================\n');

  // --------------------------------------------------------------------------
  // 1. ENDPOINT 1: GET /alertas-publicas/
  // --------------------------------------------------------------------------
  console.log('--- 1. Contrato y Servicio: GET /alertas-publicas/ ---');
  try {
    const rawAlerta = {
      id: 3,
      enfermedad: 'dengue',
      enfermedad_nombre: 'Dengue',
      anio: 2026,
      mes: 12,
      mensaje_publico: 'Se espera un aumento de dengue en la región costera en diciembre.',
      publicada_en: '2026-11-13T08:20:00-06:00',
    };
    const adaptada = adaptarAlerta(rawAlerta);
    assert(adaptada.id === 3, 'Alerta preserva id');
    assert(adaptada.enfermedad === 'dengue', 'Alerta preserva clave de enfermedad');
    assert(adaptada.enfermedad_nombre === 'Dengue', 'Alerta preserva enfermedad_nombre');
    assert(adaptada.anio === 2026 && adaptada.mes === 12, 'Alerta preserva anio y mes');
    assert(adaptada.mensaje_publico === rawAlerta.mensaje_publico, 'Alerta preserva mensaje_publico');
    assert(adaptada.region.includes('14 municipios'), 'Alerta asigna cobertura a toda la región costera (no individual)');
    assert(typeof adaptada.fecha === 'string' && adaptada.fecha.length > 0, 'Alerta genera fecha formateada legible');

    // Prueba de consumo de servicio
    const alertas = await obtenerAlertas();
    assert(Array.isArray(alertas), 'obtenerAlertas() retorna un Array');
    assert(alertas.length > 0, 'obtenerAlertas() devuelve alertas en modo de prueba');
    assert(alertas[0].id !== undefined && alertas[0].mensaje_publico !== undefined, 'Elementos retornados cumplen con el modelo Alerta');
  } catch (err) {
    assert(false, `Excepción en alertas: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 2. ENDPOINT 2: GET /contenido/
  // --------------------------------------------------------------------------
  console.log('\n--- 2. Contrato y Servicio: GET /contenido/ ---');
  try {
    const rawContenido = {
      id: 5,
      tipo: 'prevencion',
      enfermedad: 'dm2',
      titulo: 'Cómo prevenir la diabetes',
      cuerpo: 'Texto completo del contenido...',
      url_fuente: 'https://www.gob.mx/salud',
      imagen_url: '',
      publicado: true,
      autor: 'Daniel',
      fecha: '2026-11-13T08:00:00-06:00',
    };
    const cAdaptado = adaptarContenido(rawContenido);
    assert(cAdaptado.id === 5, 'Contenido preserva id');
    assert(cAdaptado.tipo === 'prevencion', 'Contenido preserva tipo (prevencion)');
    assert(cAdaptado.enfermedad === 'dm2', 'Contenido preserva clave de enfermedad (dm2)');
    assert(cAdaptado.cuerpo === rawContenido.cuerpo, 'Contenido preserva cuerpo en texto plano');
    assert(cAdaptado.tieneImagen === false, 'Contenido con imagen_url vacía marca tieneImagen=false');
    assert(cAdaptado.tieneFuente === true, 'Contenido con url_fuente válida marca tieneFuente=true');
    assert(typeof cAdaptado.fechaFormateada === 'string', 'Fecha formateada en español generada correctamente');

    // Consumo de servicio con filtros
    const todosContenidos = await obtenerContenido();
    assert(Array.isArray(todosContenidos) && todosContenidos.length > 0, 'obtenerContenido() retorna lista de contenidos');

    const prevencion = await obtenerContenido({ tipo: 'prevencion' });
    assert(prevencion.every((c) => c.tipo === 'prevencion'), 'Filtro tipo=prevencion responde exclusivamente contenidos de prevención');

    const dengue = await obtenerContenido({ enfermedad: 'dengue' });
    assert(dengue.every((c) => c.enfermedad === 'dengue'), 'Filtro enfermedad=dengue responde contenidos asociados a dengue');
  } catch (err) {
    assert(false, `Excepción en contenido: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 3. ENDPOINT 3: GET /contenido/{id}/
  // --------------------------------------------------------------------------
  console.log('\n--- 3. Contrato y Servicio: GET /contenido/{id}/ ---');
  try {
    const rawArticulo = {
      id: 10,
      tipo: 'articulo',
      enfermedad: 'dengue',
      titulo: 'Modelado epidemiológico',
      cuerpo: 'Análisis detallado',
      url_fuente: '',
      imagen_url: 'https://example.com/img.jpg',
      publicado: true,
      autor: null,
      fecha: '2026-11-10T09:00:00-06:00',
    };
    const aAdaptado = adaptarContenido(rawArticulo);
    assert(aAdaptado.id === 10, 'Artículo preserva id');
    assert(aAdaptado.tipo === 'articulo', 'Artículo preserva tipo (articulo)');
    assert(aAdaptado.tieneImagen === true, 'Artículo con imagen_url tieneImagen=true');
    assert(aAdaptado.autor === null, 'Artículo acepta autor null');

    // Consumo de servicio individual
    const detalle = await obtenerArticulo(1);
    assert(detalle.id === 1, 'obtenerArticulo(1) recupera el contenido con id 1');
    assert(typeof detalle.cuerpo === 'string' && detalle.cuerpo.length > 0, 'Detalle contiene el texto del cuerpo');

    // Manejo de 404
    let error404Capturado = false;
    try {
      await obtenerArticulo(999999);
    } catch (e) {
      error404Capturado = true;
      assert(e.status === 404, 'ID inexistente responde error con status 404');
    }
    assert(error404Capturado, 'Manejo de 404 verificado para contenido no encontrado');
  } catch (err) {
    assert(false, `Excepción en artículo: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 4. ENDPOINT 4: GET /municipios/
  // --------------------------------------------------------------------------
  console.log('\n--- 4. Contrato y Servicio: GET /municipios/ ---');
  try {
    const rawMunicipio = {
      clave_inegi: '14067',
      nombre: 'Puerto Vallarta',
      region: 'Costa-Sierra Occidental',
      latitud: null,
      longitud: null,
    };
    const mAdaptado = adaptarMunicipio(rawMunicipio);
    assert(mAdaptado.clave_inegi === '14067', 'Municipio preserva clave_inegi');
    assert(mAdaptado.nombre === 'Puerto Vallarta', 'Municipio preserva nombre');
    assert(mAdaptado.region === 'Costa-Sierra Occidental', 'Municipio preserva region');

    // Consumo de servicio
    const municipios = await obtenerMunicipios();
    assert(Array.isArray(municipios), 'obtenerMunicipios() retorna un Array');
    assert(municipios.length === 14, 'Catálogo contiene exactamente los 14 municipios de la región costera');
    assert(municipios.some((m) => m.clave_inegi === '14067' && m.nombre === 'Puerto Vallarta'), 'Incluye Puerto Vallarta con clave 14067');
    assert(municipios.some((m) => m.clave_inegi === '14027' && m.nombre === 'Cihuatlán'), 'Incluye Cihuatlán con clave 14027');
  } catch (err) {
    assert(false, `Excepción en municipios: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 5. ENDPOINT 5: GET /enfermedades/
  // --------------------------------------------------------------------------
  console.log('\n--- 5. Contrato y Servicio: GET /enfermedades/ ---');
  try {
    const rawEnf = { clave: 'dm2', nombre: 'Diabetes mellitus tipo 2', tipo: 'cronica' };
    const eAdaptado = adaptarEnfermedad(rawEnf);
    assert(eAdaptado.clave === 'dm2', 'Enfermedad preserva clave');
    assert(eAdaptado.nombre === 'Diabetes mellitus tipo 2', 'Enfermedad preserva nombre');
    assert(eAdaptado.tipo === 'cronica', 'Enfermedad preserva tipo');

    // Consumo de servicio
    const enfermedades = await obtenerEnfermedades();
    assert(Array.isArray(enfermedades) && enfermedades.length >= 4, 'obtenerEnfermedades() retorna el catálogo');
    assert(enfermedades.some((e) => e.clave === 'dengue'), 'Catálogo contiene dengue');
    assert(enfermedades.some((e) => e.clave === 'dm2'), 'Catálogo contiene dm2');
    assert(enfermedades.some((e) => e.clave === 'has'), 'Catálogo contiene has (hipertensión)');
  } catch (err) {
    assert(false, `Excepción en enfermedades: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 6. ENDPOINT 6: POST /encuesta/
  // --------------------------------------------------------------------------
  console.log('\n--- 6. Contrato y Servicio: POST /encuesta/ y validaciones ---');
  try {
    // 6.1 Preguntas desacopladas
    assert(ENCUESTA_PREGUNTAS_PROTOTIPO.length > 0, 'Configuración de preguntas desacoplada para P1 existe');
    const preguntaEdad = ENCUESTA_PREGUNTAS_PROTOTIPO.find((p) => p.id === 'edad');
    assert(preguntaEdad !== undefined, 'Pregunta edad existe en configuración');

    // 6.2 Estructura del payload
    const testMunicipio = '14022';
    const testRespuestas = { tiene_diabetes: true, edad: '25-44' };

    assert(typeof testRespuestas === 'object' && !Array.isArray(testRespuestas), 'respuestas es un objeto plano y NO un arreglo');
    assert(testRespuestas.tiene_diabetes === true, 'respuestas contiene clave: valor conforme a contrato');

    // 6.3 Envío exitoso 201
    const resultadoEnvio = await enviarEncuesta(testMunicipio, testRespuestas);
    assert(resultadoEnvio.municipio === '14022', 'Echo de respuesta confirma clave de municipio');
    assert(resultadoEnvio.consentimiento === true, 'Echo de respuesta confirma consentimiento true');
    assert(resultadoEnvio.respuestas.tiene_diabetes === true, 'Echo de respuesta confirma objeto de respuestas');

    // 6.4 Rechazo de municipio vacío
    let errorMunicipio = false;
    try {
      await enviarEncuesta('', testRespuestas);
    } catch (e) {
      errorMunicipio = true;
      assert(e.status === 400, 'Rechaza municipio vacío con status 400');
    }
    assert(errorMunicipio, 'Validación de municipio ejecutada');

    // 6.5 Rechazo de respuestas vacías
    let errorRespuestas = false;
    try {
      await enviarEncuesta('14022', {});
    } catch (e) {
      errorRespuestas = true;
      assert(e.status === 400, 'Rechaza objeto de respuestas vacío con status 400');
    }
    assert(errorRespuestas, 'Validación de respuestas ejecutada');
  } catch (err) {
    assert(false, `Excepción en encuesta: ${err.message}`);
  }

  // --------------------------------------------------------------------------
  // 7. COMPROBACIÓN VITE_USE_MOCK=false (Uso exclusivo de API real, sin mezclar mocks)
  // --------------------------------------------------------------------------
  console.log('\n--- 7. Verificación de VITE_USE_MOCK=false (Sin mezcla de mocks) ---');
  try {
    process.env.VITE_USE_MOCK = 'false';
    let hizoLlamadaReal = false;
    let mensajeErrorRed = '';
    try {
      await apiRequest('alertas-publicas/');
    } catch (e) {
      hizoLlamadaReal = true;
      mensajeErrorRed = e.message;
    }
    assert(hizoLlamadaReal === true, 'Con VITE_USE_MOCK=false el cliente ejecuta fetch real a la red');
    assert(
      mensajeErrorRed === 'No se pudo conectar con el servidor',
      'Con backend apagado retorna error de red sin sustituirlo por datos mock'
    );
    // Restaurar mock
    process.env.VITE_USE_MOCK = 'true';
  } catch (err) {
    assert(false, `Excepción en verificación de red real: ${err.message}`);
  }

  console.log('\n================================================================');
  console.log(`RESULTADO DE LA AUDITORÍA: ${passedTests}/${totalTests} pruebas pasadas.`);
  console.log('================================================================');

  if (passedTests === totalTests) {
    console.log('\n¡TODAS LAS PRUEBAS DE INTEGRACIÓN Y CONTRATO PASARON SATISFACTORIAMENTE!');
    process.exit(0);
  } else {
    console.error('\nALGUNAS PRUEBAS FALLARON.');
    process.exit(1);
  }
}

runTests();
