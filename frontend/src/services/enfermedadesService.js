// Servicio para el endpoint GET /enfermedades/
// Cumple estrictamente con API_WEB.md
import { apiRequest } from './api.js';
import { adaptarEnfermedad } from './adapters.js';

/**
 * Consulta el catálogo de enfermedades para filtros de contenido.
 * Endpoint oficial: GET /enfermedades/
 * 
 * Se muestra `nombre` y se filtra con `clave`.
 * 
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Array<Object>>} Lista de enfermedades adaptadas
 */
export async function obtenerEnfermedades(options = {}) {
  const data = await apiRequest('enfermedades/', options);
  if (!Array.isArray(data)) return [];
  return data.map(adaptarEnfermedad);
}

// Alias para compatibilidad con código existente
export { obtenerEnfermedades as getEnfermedades };
