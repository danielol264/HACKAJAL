// Servicio para el endpoint POST /encuesta/
// Cumple estrictamente con API_WEB.md
import { apiRequest } from './api.js';

/**
 * Envía las respuestas anónimas de la encuesta ciudadana.
 * Endpoint oficial: POST /encuesta/
 * 
 * Reglas del contrato:
 * - Anonimato absoluto (no envía nombre, correo, teléfono ni GPS).
 * - `municipio`: string con la clave_inegi de uno de los 14 municipios.
 * - `respuestas`: objeto { [clave_pregunta]: valor }.
 * - `consentimiento`: booleano obligatorio true.
 * 
 * @param {string} municipio - clave_inegi seleccionada (ej. "14022")
 * @param {Object} respuestas - Objeto clave/valor con al menos una respuesta
 * @param {Object} options - Opciones adicionales de fetch (signal, etc.)
 * @returns {Promise<Object>} Echo de lo enviado con código 201
 */
export async function enviarEncuesta(municipio, respuestas, options = {}) {
  if (!municipio) {
    const err = new Error('Selecciona un municipio válido.');
    err.status = 400;
    throw err;
  }

  if (!respuestas || typeof respuestas !== 'object' || Object.keys(respuestas).length === 0) {
    const err = new Error('Responde al menos una pregunta.');
    err.status = 400;
    throw err;
  }

  const payload = {
    municipio: String(municipio),
    respuestas,
    consentimiento: true,
  };

  return await apiRequest('encuesta/', {
    method: 'POST',
    body: payload,
    ...options,
  });
}

// Alias de retrocompatibilidad
export { enviarEncuesta as sendEncuesta };
