// Servicio para los endpoints de contenido (Información de Salud)
// Cumple estrictamente con API_WEB.md:
// - GET /contenido/
// - GET /contenido/{id}/
import { apiRequest } from './api.js';
import { adaptarContenido } from './adapters.js';

/**
 * Consulta la lista de contenido publicado (prevención, artículos y notas).
 * Parámetros opcionales:
 * - tipo: 'prevencion' | 'articulo' | 'nota'
 * - enfermedad: clave de enfermedad (ej. 'dm2', 'dengue')
 * 
 * @param {Object} filtros - Filtros de consulta { tipo, enfermedad }
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Array<Object>>} Lista de contenidos adaptados
 */
export async function obtenerContenido(filtros = {}, options = {}) {
  const params = new URLSearchParams();
  if (filtros.tipo) params.append('tipo', filtros.tipo);
  if (filtros.enfermedad) params.append('enfermedad', filtros.enfermedad);

  const queryStr = params.toString();
  const ruta = queryStr ? `contenido/?${queryStr}` : 'contenido/';

  const data = await apiRequest(ruta, options);
  if (!Array.isArray(data)) return [];
  return data.map(adaptarContenido);
}

/**
 * Consulta un artículo o contenido específico por su identificador.
 * Endpoint oficial: GET /contenido/{id}/
 * 
 * @param {number|string} id - Identificador numérico del contenido
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Object>} Contenido adaptado
 */
export async function obtenerArticulo(id, options = {}) {
  if (!id) {
    const err = new Error('Identificador de contenido no proporcionado');
    err.status = 400;
    throw err;
  }
  const data = await apiRequest(`contenido/${id}/`, options);
  return adaptarContenido(data);
}

// Aliases para compatibilidad con código existente
export {
  obtenerContenido as listContenido,
  obtenerArticulo as getContenidoDetalle,
};
