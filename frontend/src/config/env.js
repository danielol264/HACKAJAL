// Configuración de entorno para el Portal Web HACKAJAL
/**
 * URL base de la API REST del backend Django.
 * Valor por defecto en desarrollo local: http://127.0.0.1:8000/api
 * Se normaliza sin diagonal final para evitar dobles diagonales en las peticiones.
 */
export function getApiUrl() {
  const rawApiUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL)
    || (typeof process !== 'undefined' && process.env?.VITE_API_URL)
    || 'http://127.0.0.1:8000/api';
  return rawApiUrl.replace(/\/+$/, '');
}

export const API_URL = getApiUrl();

/**
 * Determina si el modo mock de datos simulados está activo.
 * Se evalúa dinámicamente para permitir pruebas y conmutación ágil por variable de entorno.
 */
export function isMockMode() {
  const envVal = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_USE_MOCK !== undefined)
    ? import.meta.env.VITE_USE_MOCK
    : (typeof process !== 'undefined' && process.env?.VITE_USE_MOCK);
  return envVal === 'true' || envVal === true;
}

export const USE_MOCK = isMockMode();
