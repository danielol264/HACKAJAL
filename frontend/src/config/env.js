// Configuración de entorno para el Portal Web HACKAJAL
/**
 * URL base de la API REST del backend Django.
 * Valor por defecto en desarrollo local: http://127.0.0.1:8000/api
 * Se normaliza sin diagonal final para evitar dobles diagonales en las peticiones.
 */
const rawApiUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL)
  || (typeof process !== 'undefined' && process.env?.VITE_API_URL)
  || 'http://127.0.0.1:8000/api';

export const API_URL = rawApiUrl.replace(/\/+$/, '');

/**
 * Modo de datos simulados para desarrollo y pruebas cuando Django no está corriendo.
 * Activado si VITE_USE_MOCK === 'true'.
 */
const envUseMock = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_USE_MOCK !== undefined)
  ? import.meta.env.VITE_USE_MOCK
  : (typeof process !== 'undefined' && process.env?.VITE_USE_MOCK);

export const USE_MOCK = envUseMock === 'true' || envUseMock === true;
