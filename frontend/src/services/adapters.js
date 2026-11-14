// Adaptadores de modelos para normalización de datos (Bloque 5)
// Asegura consistencia entre el contrato oficial API_WEB.md y la interfaz de usuario

/**
 * Formatea una fecha ISO 8601 a un formato legible en español.
 */
export function formatearFecha(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return new Intl.DateTimeFormat('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(d);
  } catch {
    return isoString;
  }
}

/**
 * Normaliza y enriquece una alerta epidemiológica conforme a API_WEB.md
 * Entrada del backend:
 * {
 *   "id": 3,
 *   "enfermedad": "dengue",
 *   "enfermedad_nombre": "Dengue",
 *   "anio": 2026,
 *   "mes": 12,
 *   "mensaje_publico": "...",
 *   "publicada_en": "2026-11-13T08:20:00-06:00"
 * }
 */
export function adaptarAlerta(alerta) {
  if (!alerta) return null;
  const meses = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];
  const nombreMes = alerta.mes && meses[alerta.mes] ? meses[alerta.mes] : alerta.mes;

  return {
    id: alerta.id,
    enfermedad: alerta.enfermedad,
    enfermedad_nombre: alerta.enfermedad_nombre || 'Dengue',
    anio: alerta.anio,
    mes: alerta.mes,
    mensaje_publico: alerta.mensaje_publico || alerta.mensaje || '',
    publicada_en: alerta.publicada_en,
    // Atributos de compatibilidad y presentación
    titulo: `Alerta: ${alerta.enfermedad_nombre || 'Dengue'}`,
    texto: alerta.mensaje_publico || alerta.mensaje || '',
    periodo: alerta.mes && alerta.anio ? `${nombreMes} ${alerta.anio}` : '',
    fecha: formatearFecha(alerta.publicada_en),
    region: 'Región Costera de Jalisco (14 municipios)',
    nivel: 'alerta',
  };
}

/**
 * Normaliza un contenido o artículo conforme a API_WEB.md
 * Entrada del backend:
 * {
 *   "id": 5,
 *   "tipo": "prevencion" | "articulo" | "nota",
 *   "enfermedad": "dm2" | null,
 *   "titulo": "...",
 *   "cuerpo": "...",
 *   "url_fuente": "...",
 *   "imagen_url": "...",
 *   "publicado": true,
 *   "autor": "...",
 *   "fecha": "2026-11-13T08:00:00-06:00"
 * }
 */
export function adaptarContenido(item) {
  if (!item) return null;
  const tiposEtiquetas = {
    prevencion: 'Medida Preventiva',
    articulo: 'Artículo Científico',
    nota: 'Nota Informativa',
  };

  return {
    id: item.id,
    tipo: item.tipo || 'nota',
    tipoEtiqueta: tiposEtiquetas[item.tipo] || 'Información de Salud',
    enfermedad: item.enfermedad || null,
    titulo: item.titulo || 'Sin título',
    cuerpo: item.cuerpo || '',
    url_fuente: (item.url_fuente || '').trim(),
    imagen_url: (item.imagen_url || '').trim(),
    publicado: Boolean(item.publicado),
    autor: item.autor || null,
    fecha: item.fecha,
    fechaFormateada: formatearFecha(item.fecha),
    tieneImagen: Boolean(item.imagen_url && item.imagen_url.trim().length > 0),
    tieneFuente: Boolean(item.url_fuente && item.url_fuente.trim().length > 0),
  };
}

/**
 * Normaliza un municipio conforme a API_WEB.md
 * Entrada: { clave_inegi, nombre, region, latitud, longitud }
 */
export function adaptarMunicipio(m) {
  if (!m) return null;
  return {
    clave_inegi: String(m.clave_inegi),
    nombre: m.nombre,
    region: m.region,
    latitud: m.latitud,
    longitud: m.longitud,
  };
}

/**
 * Normaliza una enfermedad conforme a API_WEB.md
 * Entrada: { clave, nombre, tipo }
 */
export function adaptarEnfermedad(e) {
  if (!e) return null;
  return {
    clave: e.clave,
    nombre: e.nombre,
    tipo: e.tipo || 'general',
  };
}
