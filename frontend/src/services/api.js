// Único punto de conexión con el backend (Django REST Framework).
// El portal web es público: ninguna petición lleva token.
const API = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '');

async function pedir(ruta, opciones = {}) {
  let respuesta;
  try {
    // Content-Type solo cuando hay cuerpo: así los GET no disparan la petición previa de CORS
    const headers = opciones.body ? { 'Content-Type': 'application/json' } : {};
    respuesta = await fetch(`${API}${ruta}`, { ...opciones, headers });
  } catch {
    throw { status: 0, datos: null, mensaje: 'No se pudo conectar con el servidor.' };
  }
  const datos = respuesta.status === 204 ? null : await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw { status: respuesta.status, datos, mensaje: mensajeDeError(respuesta.status, datos) };
  return datos;
}

// Convierte la respuesta de error del backend en un texto para mostrar.
export function mensajeDeError(status, datos) {
  if (status === 429) return 'Demasiados envíos desde tu conexión. Intenta más tarde.';
  if (status === 404) return 'Contenido no disponible.';
  if (datos?.detail) return datos.detail;
  if (datos && typeof datos === 'object') {
    const primero = Object.values(datos).flat()[0];
    if (typeof primero === 'string') return primero;
  }
  return 'Ocurrió un error. Intenta de nuevo.';
}

export const api = {
  alertas: () => pedir('/alertas-publicas/'),
  contenido: (filtros = {}) => {
    const limpios = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v));
    const query = new URLSearchParams(limpios).toString();
    return pedir(`/contenido/${query ? `?${query}` : ''}`);
  },
  articulo: (id) => pedir(`/contenido/${id}/`),
  municipios: () => pedir('/municipios/'),
  enfermedades: () => pedir('/enfermedades/'),
  enviarEncuesta: (municipio, respuestas) =>
    pedir('/encuesta/', {
      method: 'POST',
      body: JSON.stringify({ municipio, respuestas, consentimiento: true }),
    }),
};
