/**
 * Configuración del cuestionario de la encuesta ciudadana.
 * 
 * ATENCIÓN - NOTA DE INTEGRACIÓN:
 * Las preguntas definitivas NO están definidas aún por el equipo P1.
 * Este archivo define la estructura dinámica del cuestionario conforme a API_WEB.md.
 * 
 * El payload enviado a POST /encuesta/ es estrictamente:
 * {
 *   "municipio": "<clave_inegi>",
 *   "respuestas": {
 *     "<clave_pregunta>": <valor>
 *   },
 *   "consentimiento": true
 * }
 * 
 * Cuando el equipo P1 entregue las preguntas definitivas, solo se deben modificar
 * o agregar elementos en este arreglo, sin necesidad de reconstruir el formulario.
 * 
 * Esquema de cada pregunta:
 * - id: Clave enviada en el objeto "respuestas" (string, ej: "tiene_diabetes")
 * - label: Texto de la pregunta que lee el ciudadano
 * - type: "boolean" | "select" | "text" | "number"
 * - options: Arreglo de opciones para type="select" [{ value: "...", label: "..." }]
 * - required: Booleano indicando si es obligatoria
 * - placeholder: Texto de ayuda opcional
 */

export const ENCUESTA_PREGUNTAS_PROTOTIPO = [
  {
    id: "tiene_diabetes",
    label: "¿Usted o algún familiar directo en su hogar ha sido diagnosticado con diabetes?",
    type: "boolean",
    required: false,
    options: [
      { value: true, label: "Sí" },
      { value: false, label: "No" },
    ],
  },
  {
    id: "edad",
    label: "Rango de edad del participante",
    type: "select",
    required: true,
    options: [
      { value: "menor-18", label: "Menor de 18 años" },
      { value: "18-24", label: "18 a 24 años" },
      { value: "25-44", label: "25 a 44 años" },
      { value: "45-64", label: "45 a 64 años" },
      { value: "65-mas", label: "65 años o más" },
    ],
  },
  {
    id: "sintomas_recientes",
    label: "¿Ha presentado fiebre o dolor muscular en las últimas 2 semanas?",
    type: "select",
    required: false,
    options: [
      { value: "ninguno", label: "Ningún síntoma" },
      { value: "fiebre", label: "Fiebre" },
      { value: "dolor_muscular", label: "Dolor muscular / articular" },
      { value: "ambos", label: "Fiebre y dolor articular" },
    ],
  },
];
