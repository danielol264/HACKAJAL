// Servicio para el endpoint GET /alertas-publicas/
// Cumple estrictamente con API_WEB.md
import { apiRequest } from './api.js';
import { adaptarAlerta } from './adapters.js';

/**
 * Consulta las alertas epidemiológicas confirmadas y vigentes.
 * Endpoint oficial: GET /alertas-publicas/
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Array<Object>>} Lista de alertas normalizadas
 */
export async function obtenerAlertas(options = {}) {
  const data = await apiRequest('alertas-publicas/', options);
  if (!Array.isArray(data)) return [];
  return data.map(adaptarAlerta);
}

// Alias de retrocompatibilidad
export { obtenerAlertas as getAlertas };
