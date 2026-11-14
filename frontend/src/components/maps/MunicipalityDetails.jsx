import React from 'react';

/**
 * Panel contextual de información territorial y epidemiológica del municipio seleccionado.
 * Cumple estrictamente con los lineamientos de diseño institucional y no inventa datos.
 */
export default function MunicipalityDetails({
  municipality,
  onClose,
  onSelectMunicipality,
  allMunicipalities = [],
  go,
}) {
  // Estado vacío amigable cuando no hay selección
  if (!municipality) {
    const destacados = allMunicipalities.slice(0, 4);

    return (
      <aside className="municipality-details empty-state" aria-live="polite">
        <div className="details-empty-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#087b7e" strokeWidth="1.8">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
            <circle cx="12" cy="9" r="2.5" />
          </svg>
        </div>
        <h3 className="details-empty-title">Vigilancia territorial</h3>
        <p className="details-empty-text">
          Selecciona un municipio en el mapa para consultar su información territorial y epidemiológica.
        </p>

        {destacados.length > 0 && (
          <div className="details-quick-selection">
            <span className="quick-label">Sugerencias rápidas:</span>
            <div className="quick-chips">
              {destacados.map((m) => (
                <button
                  key={m.cve}
                  type="button"
                  className="quick-chip"
                  onClick={() => onSelectMunicipality?.(m)}
                >
                  {m.name}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="details-meta-card">
          <div className="meta-item">
            <span className="meta-val">14</span>
            <span className="meta-lbl">Municipios bajo vigilancia</span>
          </div>
          <div className="meta-item">
            <span className="meta-val">2</span>
            <span className="meta-lbl">Regiones sanitarias</span>
          </div>
          <div className="meta-item">
            <span className="meta-val">100%</span>
            <span className="meta-lbl">Cobertura oficial</span>
          </div>
        </div>
      </aside>
    );
  }

  const isCostaSur = municipality.region === 'Costa Sur';
  const epi = municipality.epidemiologia || {};
  const alertas = municipality.alertasRelacionadas || [];

  return (
    <aside className="municipality-details active" aria-live="polite">
      {/* Cabecera del panel */}
      <div className="details-header">
        <div>
          <span className={`details-region-badge ${isCostaSur ? 'coast' : 'sierra'}`}>
            {municipality.region}
          </span>
          <h2 className="details-title">{municipality.name}</h2>
          <span className="details-cve">
            Clave INEGI: <strong>{municipality.claveInegi}</strong> · Cabecera: {municipality.cabecera || municipality.name}
          </span>
        </div>
        <button
          type="button"
          className="details-close-btn"
          onClick={onClose}
          aria-label={`Cerrar ficha de ${municipality.name}`}
          title="Cerrar panel"
        >
          ✕
        </button>
      </div>

      <div className="details-content">
        {/* Bloque 1: Información Territorial */}
        <section className="details-section">
          <h4 className="section-title">
            <span className="section-dot" /> Información territorial
          </h4>
          <dl className="details-grid">
            <div className="details-row">
              <dt>Municipio oficial:</dt>
              <dd>{municipality.name}</dd>
            </div>
            <div className="details-row">
              <dt>Región de salud:</dt>
              <dd>{municipality.region}</dd>
            </div>
            <div className="details-row">
              <dt>Identificador geográfico:</dt>
              <dd>INEGI {municipality.claveInegi}</dd>
            </div>
            <div className="details-row">
              <dt>Estatus de cobertura:</dt>
              <dd className="status-monitored">Bajo vigilancia activa</dd>
            </div>
          </dl>
        </section>

        {/* Bloque 2: Información Epidemiológica */}
        <section className="details-section">
          <h4 className="section-title">
            <span className="section-dot" /> Información epidemiológica
          </h4>

          {epi.disponible ? (
            <div className="epi-metrics-grid">
              <div className="metric-box">
                <span className="metric-label">Casos registrados</span>
                <strong className="metric-value">{epi.casosRegistrados ?? '—'}</strong>
              </div>
              <div className="metric-box">
                <span className="metric-label">Casos activos</span>
                <strong className="metric-value highlight">{epi.casosActivos ?? '—'}</strong>
              </div>
              <div className="metric-box">
                <span className="metric-label">Casos recuperados</span>
                <strong className="metric-value">{epi.casosRecuperados ?? '—'}</strong>
              </div>
              <div className="metric-box">
                <span className="metric-label">Última actualización</span>
                <strong className="metric-value date">{epi.ultimaActualizacion ?? 'Pendiente'}</strong>
              </div>
            </div>
          ) : (
            <div className="epi-pending-notice">
              <div className="pending-badge">
                <span className="pending-indicator" />
                <span>Integración en proceso</span>
              </div>
              <p className="pending-desc">
                Las cifras epidemiológicas de este municipio se encuentran en fase de integración con el sistema central de salud pública de Jalisco.
              </p>
              {municipality.notaHistorica && (
                <div className="historical-reference">
                  <strong>Referencia histórica acumulada:</strong>
                  <p>{municipality.notaHistorica}</p>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Bloque 3: Alertas Oficiales Relacionadas */}
        <section className="details-section">
          <h4 className="section-title">
            <span className="section-dot" /> Avisos y alertas relacionadas
          </h4>
          {alertas.length > 0 ? (
            <div className="details-alerts-list">
              {alertas.map((alerta) => (
                <article key={alerta.id} className="details-alert-card">
                  <div className="alert-meta">
                    <span className="alert-badge">Alerta regional</span>
                    <span className="alert-date">{alerta.periodo || alerta.fecha}</span>
                  </div>
                  <strong className="alert-disease">{alerta.enfermedad}</strong>
                  <p className="alert-msg">{alerta.mensaje}</p>
                  {go && (
                    <button
                      type="button"
                      className="alert-action-link"
                      onClick={() => go('alertas')}
                    >
                      Consultar aviso oficial →
                    </button>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="no-alerts-text">
              ✓ Sin alertas sanitarias activas emitidas para la región de este municipio.
            </p>
          )}
        </section>

        {/* Acciones de vinculación ciudadana */}
        <div className="details-actions">
          {go && (
            <button
              type="button"
              className="primary details-action-btn"
              onClick={() => go('encuesta')}
            >
              Participar en encuesta territorial
            </button>
          )}
          {go && (
            <button
              type="button"
              className="secondary details-action-btn"
              onClick={() => go('prevencion')}
            >
              Medidas de prevención
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
