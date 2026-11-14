// Datos simulados estructurados estrictamente según API_WEB.md
// Utilizados en desarrollo cuando VITE_USE_MOCK=true o en pruebas sin backend activo.

export const MOCK_MUNICIPIOS = [
  { clave_inegi: "14012", nombre: "Atenguillo", region: "Costa-Sierra Occidental", latitud: 20.35, longitud: -104.52 },
  { clave_inegi: "14020", nombre: "Cabo Corrientes", region: "Costa-Sierra Occidental", latitud: 20.53, longitud: -105.38 },
  { clave_inegi: "14022", nombre: "Casimiro Castillo", region: "Costa Sur", latitud: 19.60, longitud: -104.43 },
  { clave_inegi: "14027", nombre: "Cihuatlán", region: "Costa Sur", latitud: 19.23, longitud: -104.57 },
  { clave_inegi: "14029", nombre: "Cuautitlán de García Barragán", region: "Costa Sur", latitud: 19.45, longitud: -104.37 },
  { clave_inegi: "14038", nombre: "Guachinango", region: "Costa-Sierra Occidental", latitud: 20.58, longitud: -104.38 },
  { clave_inegi: "14043", nombre: "La Huerta", region: "Costa Sur", latitud: 19.48, longitud: -104.65 },
  { clave_inegi: "14058", nombre: "Mascota", region: "Costa-Sierra Occidental", latitud: 20.53, longitud: -104.78 },
  { clave_inegi: "14061", nombre: "Mixtlán", region: "Costa-Sierra Occidental", latitud: 20.60, longitud: -104.42 },
  { clave_inegi: "14067", nombre: "Puerto Vallarta", region: "Costa-Sierra Occidental", latitud: 20.62, longitud: -105.23 },
  { clave_inegi: "14080", nombre: "San Sebastián del Oeste", region: "Costa-Sierra Occidental", latitud: 20.76, longitud: -104.85 },
  { clave_inegi: "14084", nombre: "Talpa de Allende", region: "Costa-Sierra Occidental", latitud: 20.38, longitud: -104.82 },
  { clave_inegi: "14100", nombre: "Tomatlán", region: "Costa Sur", latitud: 19.93, longitud: -105.25 },
  { clave_inegi: "14115", nombre: "Villa Purificación", region: "Costa Sur", latitud: 19.72, longitud: -104.60 },
];

export const MOCK_ENFERMEDADES = [
  { clave: "dengue", nombre: "Dengue", tipo: "transmisible" },
  { clave: "zika", nombre: "Zika", tipo: "transmisible" },
  { clave: "chikungunya", nombre: "Chikungunya", tipo: "transmisible" },
  { clave: "dm1", nombre: "Diabetes mellitus tipo 1", tipo: "cronica" },
  { clave: "dm2", nombre: "Diabetes mellitus tipo 2", tipo: "cronica" },
  { clave: "has", nombre: "Hipertensión arterial", tipo: "cronica" },
  { clave: "obesidad", nombre: "Obesidad", tipo: "cronica" },
];

export const MOCK_ALERTAS = [
  {
    id: 3,
    enfermedad: "dengue",
    enfermedad_nombre: "Dengue",
    anio: 2026,
    mes: 12,
    mensaje_publico: "Se espera un aumento de casos de dengue en la región costera en diciembre. Elimina recipientes con agua acumulada, limpia azoteas y utiliza repelente.",
    publicada_en: "2026-11-13T08:20:00-06:00",
  },
];

export const MOCK_CONTENIDO = [
  {
    id: 1,
    tipo: "prevencion",
    enfermedad: "dengue",
    titulo: "Acciones esenciales para evitar criaderos del mosquito del dengue",
    cuerpo: "El mosquito Aedes aegypti se reproduce en agua limpia estancada. La estrategia más efectiva es la descacharrización:\n\n1. Lava con cepillo y jabón recipientes, tinacos y cubetas.\n2. Tapa todo depósito de agua para uso doméstico.\n3. Voltea botellas, cazuelas y botes que no uses.\n4. Tira llantas viejas, latas y objetos que acumulen lluvia.\n\nDedica 10 minutos cada semana para revisar tu patio y azotea.",
    url_fuente: "https://www.gob.mx/salud",
    imagen_url: "",
    publicado: true,
    autor: "Secretaría de Salud Jalisco",
    fecha: "2026-11-10T09:00:00-06:00",
  },
  {
    id: 2,
    tipo: "prevencion",
    enfermedad: "dm2",
    titulo: "Cómo prevenir la Diabetes Mellitus Tipo 2",
    cuerpo: "La diabetes tipo 2 puede prevenirse o retrasarse significativamente manteniendo hábitos de vida saludables:\n\n- Mantener un peso corporal adecuado.\n- Realizar al menos 30 minutos de actividad física diaria moderada.\n- Consumir una dieta balanceada rica en fibra, verduras y baja en azúcares refinados y bebidas azucaradas.\n- Realizar chequeos periódicos de glucosa en sangre, especialmente después de los 35 años o con antecedentes familiares.",
    url_fuente: "https://www.gob.mx/salud",
    imagen_url: "",
    publicado: true,
    autor: "Área de Enfermedades Crónicas",
    fecha: "2026-11-12T10:30:00-06:00",
  },
  {
    id: 3,
    tipo: "prevencion",
    enfermedad: "has",
    titulo: "Control y prevención de la Hipertensión Arterial",
    cuerpo: "La hipertensión arterial se conoce como 'el asesino silencioso' porque suele no presentar síntomas evidentes hasta etapas avanzadas.\n\nRecomendaciones preventivas:\n- Reducir el consumo de sal a menos de 5 gramos diarios.\n- Evitar el consumo de tabaco y limitar el alcohol.\n- Manejar el estrés mediante descanso adecuado y ejercicio.\n- Medirse la presión arterial con regularidad.",
    url_fuente: "https://www.gob.mx/salud",
    imagen_url: "",
    publicado: true,
    autor: "Consejo Estatal de Salud",
    fecha: "2026-11-11T11:00:00-06:00",
  },
  {
    id: 4,
    tipo: "articulo",
    enfermedad: "dengue",
    titulo: "Vigilancia sindrómica y modelado predictivo en zonas costeras",
    cuerpo: "El comportamiento epidemiológico del dengue en la costa de Jalisco presenta una fuerte estacionalidad vinculada al régimen de lluvias y temperatura media superficial. Los modelos de series temporales y aprendizaje automático permiten anticipar brotes con horizontes de hasta 4 semanas, brindando a las brigadas de vectores tiempo oportuno para intervenciones focalizadas de nebulización y control larvario.",
    url_fuente: "https://saludpublica.mx",
    imagen_url: "",
    publicado: true,
    autor: "Equipo de Investigación HackaJal",
    fecha: "2026-11-08T14:15:00-06:00",
  },
  {
    id: 5,
    tipo: "nota",
    enfermedad: null,
    titulo: "Jornada comunitaria de descacharrización en Costa Sur",
    cuerpo: "Las jurisdicciones sanitarias de la Costa Sur y Costa-Sierra Occidental convocan a las familias a participar en la recolección de recipientes y objetos en desuso. Los camiones recolectores pasarán los fines de semana por las cabeceras municipales.",
    url_fuente: "",
    imagen_url: "",
    publicado: true,
    autor: "Coordinación Regional",
    fecha: "2026-11-13T07:45:00-06:00",
  },
];
