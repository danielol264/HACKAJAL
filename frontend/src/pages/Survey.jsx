import React, { useState } from 'react';
import { useMunicipios } from '../hooks/useMunicipios';
import { useEnviarEncuesta } from '../hooks/useEnviarEncuesta';
import { ENCUESTA_PREGUNTAS_PROTOTIPO } from '../config/surveyQuestions';
import {
  Title,
  Button,
  Select,
  Input,
  Checkbox,
  LoadingState,
  ErrorState,
  Alert,
  Spinner,
} from '../components/UI';

export default function Survey({ go }) {
  const { data: municipios, loading: loadingMun, error: errorMun, recargar: recargarMun } = useMunicipios();
  const { send, loading: sending, error: sendError, success, reset } = useEnviarEncuesta();

  const [municipio, setMunicipio] = useState('');
  const [respuestas, setRespuestas] = useState({});
  const [consentimiento, setConsentimiento] = useState(false);
  const [validationError, setValidationError] = useState('');

  const handleRespuestaChange = (id, valor) => {
    setRespuestas((prev) => ({
      ...prev,
      [id]: valor,
    }));
    setValidationError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    if (!municipio) {
      setValidationError('Por favor selecciona un municipio de la lista.');
      return;
    }

    if (!consentimiento) {
      setValidationError('Se requiere el consentimiento informado para enviar la respuesta.');
      return;
    }

    // Filtrar respuestas no vacías o definidas
    const respuestasLimpias = {};
    Object.entries(respuestas).forEach(([key, val]) => {
      if (val !== undefined && val !== null && String(val).trim() !== '') {
        respuestasLimpias[key] = val;
      }
    });

    if (Object.keys(respuestasLimpias).length === 0) {
      setValidationError('Por favor responde al menos una pregunta antes de enviar.');
      return;
    }

    try {
      await send(municipio, respuestasLimpias);
    } catch {
      // Error manejado internamente por el hook useEnviarEncuesta
    }
  };

  const handleNuevoEnvio = () => {
    reset();
    setMunicipio('');
    setRespuestas({});
    setConsentimiento(false);
    setValidationError('');
  };

  return (
    <section className="section">
      <Title
        eyebrow="PARTICIPACIÓN CIUDADANA"
        title="Encuesta anónima de salud"
        text="Tu participación contribuye a generar estadísticas comunitarias sobre salud y prevención en la región costera de Jalisco. La encuesta es completamente anónima."
      />

      {success ? (
        <div className="survey-form" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div style={{ fontSize: '48px', color: '#087b7e', marginBottom: '12px' }}>✓</div>
          <h2 style={{ color: '#087b7e', margin: '0 0 12px' }}>¡Gracias por responder!</h2>
          <p style={{ color: '#587078', fontSize: '14px', lineHeight: 1.6, maxWidth: '480px', margin: '0 auto 24px' }}>
            Tu reporte anónimo ha sido registrado con éxito. Los datos agregados permiten orientar las acciones comunitarias de salud pública.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <Button onClick={handleNuevoEnvio} className="secondary">
              Responder otra encuesta
            </Button>
            <Button onClick={() => go('inicio')} className="primary">
              Volver al inicio
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="survey-form">
          <div className="data" style={{ marginBottom: '22px' }}>
            <b>i</b>
            <p>
              <strong>Privacidad garantizada:</strong> No solicitamos nombre, correo electrónico, teléfono ni ubicación geográfica precisa (GPS). Solo se registra el municipio seleccionado y las respuestas sobre hábitos y salud.
            </p>
          </div>

          {/* Selector dinámico de Municipio (GET /municipios/) */}
          <div className="field">
            <label htmlFor="municipio-select">
              Municipio de residencia o consulta <span style={{ color: '#a42c2c' }}>*</span>
            </label>

            {loadingMun && <LoadingState message="Cargando catálogo de municipios de Jalisco..." />}

            {errorMun && !loadingMun && (
              <ErrorState
                title="No se pudo cargar el listado de municipios"
                error={errorMun}
                onRetry={recargarMun}
              />
            )}

            {!loadingMun && !errorMun && (
              <Select
                id="municipio-select"
                value={municipio}
                onChange={(e) => {
                  setMunicipio(e.target.value);
                  setValidationError('');
                }}
                required
              >
                <option value="">-- Selecciona tu municipio (14 municipios costeros) --</option>
                {municipios &&
                  municipios.map((m) => (
                    <option key={m.clave_inegi} value={m.clave_inegi}>
                      {m.nombre} ({m.region})
                    </option>
                  ))}
              </Select>
            )}
            <small style={{ display: 'block', marginTop: '6px', color: '#70838d', fontSize: '11px' }}>
              Los municipios corresponden a las regiones Costa Sur y Costa-Sierra Occidental.
            </small>
          </div>

          {/* Preguntas dinámicas configurables (desacopladas para el equipo P1) */}
          <div style={{ marginTop: '24px', borderTop: '1px solid #e1eceb', paddingTop: '20px' }}>
            <h3 style={{ fontSize: '15px', color: '#20313b', marginBottom: '16px' }}>
              Cuestionario de salud comunitaria
            </h3>

            {ENCUESTA_PREGUNTAS_PROTOTIPO.map((pregunta) => (
              <div className="field" key={pregunta.id}>
                <label htmlFor={`pregunta-${pregunta.id}`}>
                  {pregunta.label} {pregunta.required && <span style={{ color: '#a42c2c' }}>*</span>}
                </label>

                {pregunta.type === 'boolean' ? (
                  <Select
                    id={`pregunta-${pregunta.id}`}
                    value={respuestas[pregunta.id] === undefined ? '' : respuestas[pregunta.id]}
                    onChange={(e) => {
                      const val = e.target.value;
                      handleRespuestaChange(
                        pregunta.id,
                        val === '' ? undefined : val === 'true'
                      );
                    }}
                    required={pregunta.required}
                  >
                    <option value="">-- Selecciona una opción --</option>
                    <option value="true">Sí</option>
                    <option value="false">No</option>
                  </Select>
                ) : pregunta.type === 'select' ? (
                  <Select
                    id={`pregunta-${pregunta.id}`}
                    value={respuestas[pregunta.id] || ''}
                    onChange={(e) => handleRespuestaChange(pregunta.id, e.target.value)}
                    required={pregunta.required}
                  >
                    <option value="">-- Selecciona una opción --</option>
                    {pregunta.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input
                    id={`pregunta-${pregunta.id}`}
                    value={respuestas[pregunta.id] || ''}
                    onChange={(e) => handleRespuestaChange(pregunta.id, e.target.value)}
                    placeholder={pregunta.placeholder || ''}
                    required={pregunta.required}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Checkbox obligatorio de Consentimiento */}
          <div className="consent-field">
            <Checkbox
              id="consentimiento-check"
              checked={consentimiento}
              onChange={(e) => {
                setConsentimiento(e.target.checked);
                setValidationError('');
              }}
              required
            />
            <label htmlFor="consentimiento-check" className="consent-label">
              <strong>Acepto participar de forma voluntaria y anónima.</strong> Entiendo que mis respuestas no contienen datos personales y se utilizarán únicamente con fines de análisis epidemiológico y salud pública.
            </label>
          </div>

          {/* Mensajes de validación local y errores del servidor */}
          {validationError && <Alert type="error">{validationError}</Alert>}

          {sendError && (
            <Alert type="error">
              {sendError.message || 'Error al enviar la encuesta. Por favor intenta más tarde.'}
            </Alert>
          )}

          {/* Botón de envío con estado de carga */}
          <div style={{ marginTop: '24px' }}>
            <Button
              type="submit"
              disabled={sending || !municipio || !consentimiento}
              className="primary"
              style={{ width: '100%', padding: '14px', fontSize: '14px' }}
            >
              {sending ? <Spinner size="sm" label="Enviando respuestas..." /> : 'Enviar respuestas'}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
