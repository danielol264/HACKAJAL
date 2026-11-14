/**
 * Servicio de Cobertura Territorial y Vigilancia Epidemiológica HACKAJAL
 * Conecta las geometrías oficiales (INEGI) con los servicios de municipios y alertas.
 * Diseñado conforme a API_WEB.md y preparado para Django REST Framework.
 */

import {
  JALISCO_COVERAGE_MUNICIPALITIES,
  MAP_DIMENSIONS,
  REGIONS_META,
} from '../data/jaliscoCoverageGeo.js';
import { obtenerMunicipios } from './municipiosService.js';
import { obtenerAlertas } from './alertasService.js';

/**
 * Normaliza cadenas para comparaciones robustas (sin acentos, minúsculas).
 */
function normalizarTexto(str) {
  if (!str) return '';
  return str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

/**
 * Obtiene la cobertura completa de los 14 municipios monitoreados,
 * enriquecida con datos del catálogo de API_WEB y alertas vigentes.
 *
 * @param {Object} options - Opciones de fetch (signal, etc.)
 * @returns {Promise<Array<Object>>} Lista de 14 municipios con geometría y estado
 */
export async function obtenerCoberturaTerritorial(options = {}) {
  // 1. Obtener datos de soporte en paralelo sin romper si falla alguno
  let apiMunicipios = [];
  let apiAlertas = [];

  try {
    const [munResult, alertResult] = await Promise.allSettled([
      obtenerMunicipios(options),
      obtenerAlertas(options),
    ]);

    if (munResult.status === 'fulfilled' && Array.isArray(munResult.value)) {
      apiMunicipios = munResult.value;
    }
    if (alertResult.status === 'fulfilled' && Array.isArray(alertResult.value)) {
      apiAlertas = alertResult.value;
    }
  } catch {
    // Si no hay red o backend apagado, continuamos con datos geográficos verificados
  }

  // 2. Mapear alertas activas (aplican a toda la región costera según API_WEB.md)
  const alertasVigentes = apiAlertas.map((a) => ({
    id: a.id,
    enfermedad: a.enfermedad_nombre || a.enfermedad || 'Dengue',
    mensaje: a.mensaje_publico || a.texto || '',
    periodo: a.periodo || '',
    fecha: a.fecha || '',
  }));

  // 3. Fusionar datos geográficos oficiales con catálogo y estado epidemiológico
  return JALISCO_COVERAGE_MUNICIPALITIES.map((geoMun) => {
    // Buscar coincidencia en API_WEB por clave_inegi o nombre normalizado
    const matchApi = apiMunicipios.find(
      (m) =>
        m.clave_inegi === geoMun.claveInegi ||
        m.clave_inegi === `14${geoMun.cve}` ||
        normalizarTexto(m.nombre) === normalizarTexto(geoMun.name)
    );

    const claveOficial = matchApi?.clave_inegi || geoMun.claveInegi;
    const regionOficial = geoMun.region;

    // Estructura epidemiológica desacoplada y preparada para Django REST
    // No inventa cifras: si el backend aún no provee desglose municipal en tiempo real,
    // declara el estado pendiente de integración oficial.
    const datosEpidemiologicos = {
      disponible: false, // Cambiará a true cuando el endpoint municipal de Django REST responda
      mensajeEstado: 'Datos epidemiológicos pendientes de integración oficial',
      casosRegistrados: null,
      casosActivos: null,
      casosRecuperados: null,
      ultimaActualizacion: null,
      // Se preserva la nota histórica acumulada de referencia si existe
      notaHistorica: geoMun.notaHistorica || null,
    };

    return {
      ...geoMun,
      claveInegi: claveOficial,
      latitud: matchApi?.latitud || null,
      longitud: matchApi?.longitud || null,
      regionMeta: REGIONS_META[regionOficial] || REGIONS_META['Costa Sur'],
      alertasRelacionadas: alertasVigentes,
      tieneAlertas: alertasVigentes.length > 0,
      epidemiologia: datosEpidemiologicos,
    };
  });
}

/**
 * Obtiene el resumen consolidado de la cobertura territorial de HACKAJAL.
 */
export function obtenerResumenCobertura() {
  return {
    totalMunicipios: 14,
    totalRegiones: 2,
    regiones: [
      {
        nombre: 'Costa Sur',
        total: 6,
        color: REGIONS_META['Costa Sur'].color,
        municipios: JALISCO_COVERAGE_MUNICIPALITIES.filter((m) => m.region === 'Costa Sur').map((m) => m.name),
      },
      {
        nombre: 'Costa-Sierra Occidental',
        total: 8,
        color: REGIONS_META['Costa-Sierra Occidental'].color,
        municipios: JALISCO_COVERAGE_MUNICIPALITIES.filter((m) => m.region === 'Costa-Sierra Occidental').map((m) => m.name),
      },
    ],
    fuenteGeografica: MAP_DIMENSIONS.source,
    dimensionesMapa: MAP_DIMENSIONS,
    ultimaActualizacion: 'Ciclo 2026',
  };
}

/**
 * Busca un municipio por su clave INEGI o nombre.
 */
export function buscarMunicipioEnCobertura(termino, listaMunicipios) {
  if (!termino || !listaMunicipios) return null;
  const tNorm = normalizarTexto(termino);
  return (
    listaMunicipios.find(
      (m) =>
        m.claveInegi === termino ||
        m.cve === termino ||
        normalizarTexto(m.name) === tNorm ||
        normalizarTexto(m.cabecera) === tNorm
    ) || null
  );
}
