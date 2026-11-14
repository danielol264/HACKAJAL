// Cliente HTTP centralizado para el Portal Web HACKAJAL
// Cumple estrictamente con el contrato oficial API_WEB.md
import { API_URL, USE_MOCK, isMockMode, getApiUrl } from '../config/env.js';
import {
  MOCK_ALERTAS,
  MOCK_CONTENIDO,
  MOCK_MUNICIPIOS,
  MOCK_ENFERMEDADES,
} from '../data/mockApiData.js';

export { API_URL };

/**
 * Normaliza la ruta asegurando que termine con diagonal final '/'
 * conforme a los requerimientos de Django REST Framework.
 */
function normalizarRuta(ruta) {
  const sinDiagonalInicial = ruta.replace(/^\/+/, '');
  const [camino, query] = sinDiagonalInicial.split('?');
  const caminoConSlash = camino.endsWith('/') ? camino : `${camino}/`;
  return query !== undefined ? `${caminoConSlash}?${query}` : caminoConSlash;
}

/**
 * Simulador local para pruebas cuando VITE_USE_MOCK=true
 */
async function responderMock(rutaNormalizada, { method = 'GET', body = null } = {}) {
  // Simular latencia de red
  await new Promise((r) => setTimeout(r, 150));

  const [pathOnly, queryStr] = rutaNormalizada.split('?');
  const params = new URLSearchParams(queryStr || '');

  // 1. GET /alertas-publicas/
  if (pathOnly === 'alertas-publicas/') {
    return [...MOCK_ALERTAS];
  }

  // 2. GET /contenido/
  if (pathOnly === 'contenido/' && method === 'GET') {
    const tipo = params.get('tipo');
    const enfermedad = params.get('enfermedad');
    let filtrado = [...MOCK_CONTENIDO];
    if (tipo) filtrado = filtrado.filter((c) => c.tipo === tipo);
    if (enfermedad) filtrado = filtrado.filter((c) => c.enfermedad === enfermedad);
    return filtrado;
  }

  // 3. GET /contenido/{id}/
  const matchDetalle = pathOnly.match(/^contenido\/(\d+)\/$/);
  if (matchDetalle && method === 'GET') {
    const cid = parseInt(matchDetalle[1], 10);
    const item = MOCK_CONTENIDO.find((c) => c.id === cid);
    if (!item || !item.publicado) {
      const err = new Error('Contenido no disponible');
      err.status = 404;
      err.datos = { detail: 'Contenido no encontrado o no disponible.' };
      throw err;
    }
    return { ...item };
  }

  // 4. GET /municipios/
  if (pathOnly === 'municipios/') {
    return [...MOCK_MUNICIPIOS];
  }

  // 5. GET /enfermedades/
  if (pathOnly === 'enfermedades/') {
    return [...MOCK_ENFERMEDADES];
  }

  // 6. POST /encuesta/
  if (pathOnly === 'encuesta/' && method === 'POST') {
    if (!body || !body.consentimiento) {
      const err = new Error('Se requiere el consentimiento para guardar la respuesta.');
      err.status = 400;
      err.datos = { consentimiento: ['Se requiere el consentimiento para guardar la respuesta.'] };
      throw err;
    }
    if (!body.municipio) {
      const err = new Error('Selecciona un municipio válido.');
      err.status = 400;
      err.datos = { municipio: ['Selecciona un municipio válido.'] };
      throw err;
    }
    if (!body.respuestas || typeof body.respuestas !== 'object' || Object.keys(body.respuestas).length === 0) {
      const err = new Error('Responde al menos una pregunta.');
      err.status = 400;
      err.datos = { respuestas: ['Debe ser un objeto con al menos una respuesta.'] };
      throw err;
    }
    // Echo de la respuesta según contrato 201
    return { ...body };
  }

  const err = new Error('Recurso no encontrado');
  err.status = 404;
  throw err;
}

/**
 * Cliente HTTP centralizado para todas las peticiones a la API.
 * 
 * Reglas de API_WEB.md:
 * - Sin autenticación (no Authorization headers ni tokens).
 * - JSON en peticiones POST.
 * - Manejo robusto de errores de red, 404, 429 y validaciones 400 de Django.
 * 
 * @param {string} ruta - Ruta relativa al backend (ej. 'alertas-publicas/')
 * @param {Object} opciones - Configuración de fetch (method, body, signal, etc.)
 * @returns {Promise<any>} Datos JSON parseados o null si la respuesta es vacía / 204.
 */
export async function apiRequest(ruta, { method = 'GET', body = null, headers = {}, signal = null } = {}) {
  const rutaNormalizada = normalizarRuta(ruta);

  // Si está explícitamente configurado el modo mock para desarrollo local offline
  if (isMockMode()) {
    return await responderMock(rutaNormalizada, { method, body });
  }

  const baseUrl = getApiUrl();
  const url = `${baseUrl}/${rutaNormalizada}`;

  const init = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    signal,
  };

  if (body !== null && method !== 'GET' && method !== 'HEAD') {
    init.body = typeof body === 'string' ? body : JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, init);
  } catch (netError) {
    // Si fue cancelado voluntariamente por un AbortController
    if (netError.name === 'AbortError') {
      throw netError;
    }
    // Error de red, conexión rechazada o servidor apagado
    const connError = new Error('No se pudo conectar con el servidor');
    connError.status = 0;
    connError.isNetworkError = true;
    connError.originalError = netError;
    throw connError;
  }

  // Manejo de respuesta vacía (204 No Content)
  if (response.status === 204) {
    return null;
  }

  // Parseo seguro de respuesta JSON
  let datos = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      datos = await response.json();
    } catch {
      datos = null;
    }
  }

  // Si la petición fue exitosa (200-299)
  if (response.ok) {
    return datos;
  }

  // Gestión de códigos de error según API_WEB.md
  let mensajeError = 'Ocurrió un error en la solicitud.';

  if (response.status === 404) {
    mensajeError = 'Contenido no disponible';
  } else if (response.status === 429) {
    mensajeError = 'Demasiados envíos, intenta más tarde';
  } else if (response.status >= 500) {
    mensajeError = 'No se pudo conectar con el servidor';
  } else if (datos) {
    // Manejo de errores 400 por campo o detail de Django REST Framework
    if (typeof datos.detail === 'string') {
      mensajeError = datos.detail;
    } else if (typeof datos === 'object') {
      const keys = Object.keys(datos);
      if (keys.length > 0) {
        const primerCampo = keys[0];
        const val = datos[primerCampo];
        if (Array.isArray(val) && val.length > 0) {
          mensajeError = `${primerCampo}: ${val[0]}`;
        } else if (typeof val === 'string') {
          mensajeError = `${primerCampo}: ${val}`;
        }
      }
    }
  }

  const err = new Error(mensajeError);
  err.status = response.status;
  err.datos = datos;
  throw err;
}
