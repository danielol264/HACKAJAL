// Servicio para el endpoint GET /municipios/
// Cumple estrictamente con API_WEB.md
import { apiRequest } from './api.js';
import { adaptarMunicipio } from './adapters.js';

/**
 * Consulta la lista oficial de los 14 municipios de la región costera.
 * Endpoint oficial: GET /municipios/
 * 
 * En el selector se muestra `nombre` y se envía `clave_inegi`.
 * 
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Array<Object>>} Lista de municipios adaptados
 */
export async function obtenerMunicipios(options = {}) {
  const data = await apiRequest('municipios/', options);
  if (!Array.isArray(data)) return [];
  return data.map(adaptarMunicipio);
}

// Alias para compatibilidad con código existente
export { obtenerMunicipios as getMunicipios };
