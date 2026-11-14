import React from 'react';

/**
 * Tooltip informativo emergente para hover/foco sobre municipios.
 * Cumple con los requerimientos de accesibilidad y no inventa datos epidemiológicos.
 */
export default function MunicipalityTooltip({ municipality, position, visible }) {
  if (!visible || !municipality) return null;

  const isCostaSur = municipality.region === 'Costa Sur';
  const epi = municipality.epidemiologia || {};

  return (
    <div
      className="municipality-tooltip"
      role="tooltip"
      aria-hidden={!visible}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      <div className="tooltip-header">
        <div className="tooltip-title-wrap">
          <strong className="tooltip-title">{municipality.name}</strong>
          <span className="tooltip-cve">INEGI: {municipality.claveInegi}</span>
        </div>
        <span className={`tooltip-badge ${isCostaSur ? 'coast' : 'sierra'}`}>
          {municipality.region}
        </span>
      </div>

      <div className="tooltip-body">
        {epi.disponible ? (
          <div className="tooltip-stats">
            <div className="tooltip-stat">
              <span>Registrados:</span>
              <strong>{epi.casosRegistrados ?? '—'}</strong>
            </div>
            <div className="tooltip-stat">
              <span>Activos:</span>
              <strong>{epi.casosActivos ?? '—'}</strong>
            </div>
            <div className="tooltip-stat full">
              <span>Estado:</span>
              <span className="tooltip-status-tag">{epi.mensajeEstado}</span>
            </div>
            {epi.ultimaActualizacion && (
              <small className="tooltip-date">Actualizado: {epi.ultimaActualizacion}</small>
            )}
          </div>
        ) : (
          <div className="tooltip-pending">
            <div className="tooltip-status-row">
              <span className="tooltip-dot" aria-hidden="true" />
              <span>Vigilancia territorial activa</span>
            </div>
            <p className="tooltip-pending-text">
              Datos epidemiológicos: <em>Pendientes de integración oficial</em>
            </p>
            {municipality.notaHistorica && (
              <div className="tooltip-historical-note">
                <small>Ref. histórica: {municipality.notaHistorica}</small>
              </div>
            )}
          </div>
        )}

        {municipality.tieneAlertas && (
          <div className="tooltip-alert-flag">
            <span aria-hidden="true">⚑</span>
            <span>Aviso epidemiológico vigente en la región</span>
          </div>
        )}
      </div>

      <div className="tooltip-hint">
        <small>Haz clic para consultar la ficha completa</small>
      </div>
    </div>
  );
}
