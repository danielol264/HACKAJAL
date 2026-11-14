import React, { useState, useEffect, useRef, useMemo } from 'react';
import './InteractiveCoverageMap.css';
import {
  obtenerCoberturaTerritorial,
  obtenerResumenCobertura,
  buscarMunicipioEnCobertura,
} from '../../services/coverageMapService';
import MunicipalityTooltip from './MunicipalityTooltip';
import MunicipalityDetails from './MunicipalityDetails';

/**
 * Componente principal de Mapa Interactivo de Cobertura Territorial de HACKAJAL.
 * Cumple con estándares de UX/UI institucional, accesibilidad WCAG y diseño responsivo.
 *
 * Props:
 * - variant: 'full' (sección protagonista completa) o 'compact' / 'hero' (versión sintetizada para el hero)
 * - onSelect: callback opcional al seleccionar municipio
 * - go: función de navegación de la aplicación (go('ruta'))
 */
export default function InteractiveCoverageMap({
  variant = 'full',
  onSelect,
  go,
  initialSelectedId = null,
}) {
  const [municipalities, setMunicipalities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMun, setSelectedMun] = useState(null);
  const [hoveredMun, setHoveredMun] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [regionFilter, setRegionFilter] = useState('todas'); // 'todas' | 'Costa Sur' | 'Costa-Sierra Occidental'
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const containerRef = useRef(null);
  const mapSvgRef = useRef(null);

  const resumen = useMemo(() => obtenerResumenCobertura(), []);
  const { dimensionesMapa } = resumen;

  // Carga de datos integrada con servicios oficiales
  useEffect(() => {
    let cancelado = false;
    async function cargar() {
      setLoading(true);
      try {
        const data = await obtenerCoberturaTerritorial();
        if (!cancelado) {
          setMunicipalities(data);
          if (initialSelectedId) {
            const found = buscarMunicipioEnCobertura(initialSelectedId, data);
            if (found) setSelectedMun(found);
          }
        }
      } catch (err) {
        console.error('Error al cargar datos del mapa:', err);
      } finally {
        if (!cancelado) setLoading(false);
      }
    }
    cargar();
    return () => {
      cancelado = true;
    };
  }, [initialSelectedId]);

  // Selección de municipio
  const handleSelectMunicipality = (m) => {
    setSelectedMun((prev) => (prev?.cve === m?.cve ? null : m));
    if (onSelect) onSelect(m);

    // Si se selecciona un municipio y el zoom está en nivel base, acercar suavemente
    if (m && variant === 'full') {
      const targetZoom = 1.35;
      const centerX = dimensionesMapa.width / 2;
      const centerY = dimensionesMapa.height / 2;
      const panX = (centerX - m.cx) * (targetZoom - 1);
      const panY = (centerY - m.cy) * (targetZoom - 1);
      setZoom(targetZoom);
      setPan({ x: panX, y: panY });
    }
  };

  // Manejadores de interacción de puntero
  const handleMouseEnter = (e, m) => {
    setHoveredMun(m);
    updateTooltipCoordinates(e);
    setTooltipVisible(true);
  };

  const handleMouseMove = (e) => {
    updateTooltipCoordinates(e);
  };

  const handleMouseLeave = () => {
    setHoveredMun(null);
    setTooltipVisible(false);
  };

  const updateTooltipCoordinates = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setTooltipPos({ x, y });
  };

  // Accesibilidad mediante teclado
  const handleKeyDown = (e, m) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSelectMunicipality(m);
    } else if (e.key === 'Escape') {
      setSelectedMun(null);
    }
  };

  // Controles de zoom
  const handleZoomIn = () => {
    setZoom((z) => Math.min(z + 0.3, 2.4));
  };

  const handleZoomOut = () => {
    setZoom((z) => {
      const next = Math.max(z - 0.3, 1);
      if (next === 1) setPan({ x: 0, y: 0 });
      return next;
    });
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedMun(null);
    setSearchQuery('');
    setRegionFilter('todas');
  };

  // Filtrado y búsqueda
  const filteredMunicipalities = useMemo(() => {
    return municipalities.filter((m) => {
      const matchRegion = regionFilter === 'todas' || m.region === regionFilter;
      const matchQuery =
        !searchQuery ||
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.claveInegi.includes(searchQuery);
      return matchRegion && matchQuery;
    });
  }, [municipalities, regionFilter, searchQuery]);

  // Selección directa desde el buscador
  const handleSearchSelect = (m) => {
    handleSelectMunicipality(m);
    setSearchQuery('');
  };

  // Render simplificado para variante "hero"
  if (variant === 'hero' || variant === 'compact') {
    return (
      <div className="coverage-map-hero-preview" ref={containerRef}>
        <div className="hero-preview-badge">
          <span className="pulse-dot" />
          <span>Vigilancia territorial activa · 14 municipios</span>
        </div>

        <div className="hero-svg-wrapper">
          <svg
            viewBox={dimensionesMapa.viewBox}
            className="hero-map-svg"
            role="img"
            aria-label="Mapa esquemático de cobertura territorial en la costa de Jalisco"
          >
            <defs>
              <filter id="hero-soft-glow" x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#087b7e" floodOpacity="0.15" />
              </filter>
            </defs>
            <g>
              {municipalities.map((m) => {
                const isSelected = selectedMun?.cve === m.cve;
                const isCosta = m.region === 'Costa Sur';
                return (
                  <path
                    key={m.cve}
                    d={m.path}
                    className={`hero-path ${isCosta ? 'coast' : 'sierra'} ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectMunicipality(m)}
                    title={`${m.name} (${m.region})`}
                  />
                );
              })}
              {municipalities.map((m) => (
                <circle
                  key={`dot-${m.cve}`}
                  cx={m.cx}
                  cy={m.cy}
                  r="2.5"
                  className="hero-dot"
                />
              ))}
            </g>
          </svg>
        </div>

        <div className="hero-preview-footer">
          <div className="hero-preview-counts">
            <strong>14 municipios monitoreados</strong>
            <span>Costa Sur y Costa-Sierra Occidental</span>
          </div>
          <a
            href="#mapa-cobertura"
            className="hero-explore-btn"
            onClick={(e) => {
              const el = document.getElementById('mapa-cobertura');
              if (el) {
                e.preventDefault();
                el.scrollIntoView({ behavior: 'smooth' });
              }
            }}
          >
            Explorar mapa completo ↓
          </a>
        </div>
      </div>
    );
  }

  // Render completo de alta fidelidad para la sección protagonista
  return (
    <section className="interactive-coverage-section" id="mapa-cobertura">
      {/* Encabezado institucional de la sección */}
      <header className="coverage-section-header">
        <div className="header-titles">
          <span className="section-eyebrow">COBERTURA OFICIAL Y SEGUIMIENTO REGIONAL</span>
          <h2 className="section-heading">Vigilancia territorial</h2>
          <p className="section-description">
            Explora la cobertura epidemiológica y consulta información de los municipios bajo vigilancia.
          </p>
        </div>

        <div className="coverage-kpi-bar">
          <div className="kpi-item">
            <span className="kpi-number">14</span>
            <span className="kpi-label">Municipios bajo vigilancia</span>
          </div>
          <div className="kpi-item">
            <span className="kpi-number">2</span>
            <span className="kpi-label">Regiones sanitarias</span>
          </div>
          <div className="kpi-item">
            <span className="kpi-number">100%</span>
            <span className="kpi-label">Límites verificados INEGI</span>
          </div>
        </div>
      </header>

      {/* Barra de herramientas y filtros */}
      <div className="coverage-toolbar">
        {/* Filtro por región */}
        <div className="region-filter-tabs" role="tablist" aria-label="Filtrar por región">
          <button
            type="button"
            role="tab"
            aria-selected={regionFilter === 'todas'}
            className={`filter-tab ${regionFilter === 'todas' ? 'active' : ''}`}
            onClick={() => setRegionFilter('todas')}
          >
            Todos los municipios ({resumen.totalMunicipios})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={regionFilter === 'Costa Sur'}
            className={`filter-tab coast ${regionFilter === 'Costa Sur' ? 'active' : ''}`}
            onClick={() => setRegionFilter('Costa Sur')}
          >
            <span className="tab-indicator coast" /> Costa Sur (6)
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={regionFilter === 'Costa-Sierra Occidental'}
            className={`filter-tab sierra ${regionFilter === 'Costa-Sierra Occidental' ? 'active' : ''}`}
            onClick={() => setRegionFilter('Costa-Sierra Occidental')}
          >
            <span className="tab-indicator sierra" /> Costa-Sierra Occidental (8)
          </button>
        </div>

        {/* Buscador predictivo de municipios */}
        <div className="municipality-search-wrapper">
          <label htmlFor="coverage-search" className="visually-hidden">
            Buscar municipio en el mapa
          </label>
          <div className="search-input-box">
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              id="coverage-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar municipio (ej. Puerto Vallarta, Cihuatlán...)"
              className="search-field"
            />
            {searchQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Limpiar búsqueda"
              >
                ✕
              </button>
            )}
          </div>

          {/* Desplegable de coincidencias cuando el usuario busca */}
          {searchQuery.trim().length > 0 && (
            <div className="search-dropdown-results" role="listbox">
              {filteredMunicipalities.length > 0 ? (
                filteredMunicipalities.map((m) => (
                  <button
                    key={m.cve}
                    type="button"
                    role="option"
                    className="dropdown-item"
                    onClick={() => handleSearchSelect(m)}
                  >
                    <strong>{m.name}</strong>
                    <span>{m.region} · INEGI {m.claveInegi}</span>
                  </button>
                ))
              ) : (
                <div className="dropdown-empty">
                  No se encontraron municipios coincidentes.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Área principal: Grid con Mapa Protagonista y Panel Contextual */}
      <div className="coverage-main-grid" ref={containerRef}>
        {/* Contenedor del Mapa Geográfico */}
        <div className="map-canvas-container" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
          {loading && (
            <div className="map-loading-overlay">
              <div className="map-spinner" />
              <span>Cargando delimitación territorial oficial...</span>
            </div>
          )}

          {/* Controles de visualización (Zoom / Reset) */}
          <div className="map-controls-floating" aria-label="Controles de navegación en el mapa">
            <button
              type="button"
              className="control-btn"
              onClick={handleZoomIn}
              aria-label="Acercar mapa"
              title="Acercar (+)"
            >
              +
            </button>
            <button
              type="button"
              className="control-btn"
              onClick={handleZoomOut}
              aria-label="Alejar mapa"
              title="Alejar (−)"
            >
              −
            </button>
            <button
              type="button"
              className="control-btn reset"
              onClick={handleResetView}
              aria-label="Restablecer vista inicial"
              title="Restablecer vista"
            >
              ⟲
            </button>
          </div>

          {/* Etiqueta de escala y fuente */}
          <div className="map-watermark">
            <span>Fuente: INEGI Marco Geoestadístico · Jalisco</span>
          </div>

          {/* Lienzo SVG Interactivo */}
          <svg
            ref={mapSvgRef}
            viewBox={dimensionesMapa.viewBox}
            className="interactive-svg-canvas"
            role="region"
            aria-label="Mapa interactivo de cobertura territorial de Jalisco"
          >
            <defs>
              <filter id="mun-shadow-hover" x="-15%" y="-15%" width="130%" height="130%">
                <feDropShadow dx="0" dy="3" stdDeviation="5" floodColor="#087b7e" floodOpacity="0.35" />
              </filter>
              <filter id="mun-shadow-selected" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="4" stdDeviation="7" floodColor="#087b7e" floodOpacity="0.45" />
              </filter>
            </defs>

            {/* Grupo transformable para zoom y pan */}
            <g
              id="map-viewport-group"
              style={{
                transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                transformOrigin: 'center center',
                transition: 'transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)',
              }}
            >
              {/* Capa de Geometrías Municipales */}
              {municipalities.map((m) => {
                const isSelected = selectedMun?.cve === m.cve;
                const isHovered = hoveredMun?.cve === m.cve;
                const isCosta = m.region === 'Costa Sur';
                const isDimmed = regionFilter !== 'todas' && m.region !== regionFilter;

                return (
                  <path
                    key={m.cve}
                    id={`mun-path-${m.cve}`}
                    d={m.path}
                    tabIndex={0}
                    role="button"
                    aria-label={`${m.name}, región ${m.region}. Clave INEGI: ${m.claveInegi}`}
                    aria-pressed={isSelected}
                    className={[
                      'municipality-polygon',
                      isCosta ? 'region-costa' : 'region-sierra',
                      isSelected ? 'is-selected' : '',
                      isHovered ? 'is-hovered' : '',
                      isDimmed ? 'is-dimmed' : '',
                      m.tieneAlertas ? 'has-alert' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onMouseEnter={(e) => handleMouseEnter(e, m)}
                    onClick={() => handleSelectMunicipality(m)}
                    onKeyDown={(e) => handleKeyDown(e, m)}
                  />
                );
              })}

              {/* Capa de Marcadores y Etiquetas en los Centroides Oficiales */}
              {municipalities.map((m) => {
                const isSelected = selectedMun?.cve === m.cve;
                const isHovered = hoveredMun?.cve === m.cve;
                const isDimmed = regionFilter !== 'todas' && m.region !== regionFilter;

                return (
                  <g
                    key={`centroid-${m.cve}`}
                    className={`municipality-marker-group ${isSelected ? 'marker-selected' : ''} ${isHovered ? 'marker-hovered' : ''} ${isDimmed ? 'marker-dimmed' : ''}`}
                    pointerEvents="none"
                  >
                    {/* Anillo de pulso si está seleccionado o tiene alerta */}
                    {(isSelected || m.tieneAlertas) && (
                      <circle
                        cx={m.cx}
                        cy={m.cy}
                        r="10"
                        className={`marker-pulse-ring ${m.tieneAlertas ? 'alert-pulse' : ''}`}
                      />
                    )}

                    {/* Punto central del municipio */}
                    <circle
                      cx={m.cx}
                      cy={m.cy}
                      r={isSelected ? '5' : isHovered ? '4.5' : '3.2'}
                      className="marker-core-dot"
                    />

                    {/* Etiqueta textual visible con sombra de alto contraste */}
                    <text
                      x={m.cx}
                      y={m.cy - (isSelected ? 9 : 7)}
                      className="municipality-label-text"
                    >
                      {m.name}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Tooltip interactivo flotante */}
          <MunicipalityTooltip
            municipality={hoveredMun}
            position={tooltipPos}
            visible={tooltipVisible && !selectedMun}
          />

          {/* Leyenda visual integrada en el mapa */}
          <div className="coverage-map-legend" aria-label="Leyenda de regiones">
            <div className="legend-item">
              <span className="legend-color-box coast" />
              <span className="legend-text">Costa Sur (6 municipios)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-box sierra" />
              <span className="legend-text">Costa-Sierra Occidental (8 municipios)</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot-alert" />
              <span className="legend-text">Avisos oficiales vigentes</span>
            </div>
          </div>
        </div>

        {/* Panel lateral contextual: información territorial y epidemiológica */}
        <MunicipalityDetails
          municipality={selectedMun}
          onClose={() => setSelectedMun(null)}
          onSelectMunicipality={handleSelectMunicipality}
          allMunicipalities={municipalities}
          go={go}
        />
      </div>
    </section>
  );
}
