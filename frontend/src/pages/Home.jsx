import { useState } from 'react';
import { Title, Stat, Card, AlertCard, LoadingState, ErrorState } from '../components/UI';
import { municipalities, history } from '../data/demoData';
import { useAlertas } from '../hooks/useAlertas';

// Subcomponentes de visualización contextual histórica
function HistoryBars() {
  const max = 5390;
  return (
    <div className="history-bars" aria-label="Gráfica anual de casos históricos">
      {history.map((d) => (
        <div className="year-group" key={d.year}>
          <div className="bar-stack">
            <i className="discarded" style={{ height: `${(d.discarded / max) * 145}px` }} title={`Descartados: ${d.discarded}`} />
            <i className="probable" style={{ height: `${(d.probable / max) * 145}px` }} title={`Probables: ${d.probable}`} />
            <i className="confirmed" style={{ height: `${(d.confirmed / max) * 145}px` }} title={`Confirmados: ${d.confirmed}`} />
          </div>
          <b>{d.year}</b>
        </div>
      ))}
    </div>
  );
}

function NeutralMap({ selected, onSelect }) {
  return (
    <div className="neutral-map">
      <div className="region-label coast">Costa Sur</div>
      <div className="region-label sierra">Costa-Sierra<br />Occidental</div>
      <div className="neutral-map-grid">
        {municipalities.map((m) => (
          <button
            key={m.name}
            className={`${m.region === 'Costa Sur' ? 'coast' : 'sierra'} ${selected?.name === m.name ? 'selected' : ''}`}
            onClick={() => onSelect?.(m)}
          >
            {m.name}
          </button>
        ))}
      </div>
      <small>Vista territorial esquemática de los 14 municipios de la región costera de Jalisco.</small>
    </div>
  );
}

export default function Home({ go }) {
  const [chosen, setChosen] = useState(municipalities[0]);
  const { data: alerts, loading: loadingAlerts, error: errorAlerts, recargar: recargarAlertas } = useAlertas();

  const statData = [
    ['✓', 'Confirmados', '2,203', 'Registros históricos 2020–2026'],
    ['?', 'Probables', '9,029', 'Pendientes de confirmación'],
    ['—', 'Descartados', '4,235', 'No son casos confirmados'],
    ['⌖', 'Municipios', '14', 'Costa Sur y Costa-Sierra Occidental'],
  ];

  return (
    <>
      {/* Hero principal */}
      <section className="hero dengue-hero">
        <div>
          <span>JALISCO · COSTA SUR Y COSTA-SIERRA OCCIDENTAL</span>
          <h1>Vigilancia epidemiológica del dengue</h1>
          <p>Portal público de información y alertas preventivas para proteger la salud de nuestras comunidades.</p>
          <div className="hero-meta">
            <b>14 municipios monitoreados</b>
            <b>Histórico disponible: 2020–2026</b>
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button className="primary" onClick={() => go('municipios')}>Consultar municipios</button>
            <button className="secondary" onClick={() => go('encuesta')}>Participar en la encuesta</button>
          </div>
        </div>
        <aside className="surveillance-visual">
          <div className="radar"><i /><i /><i /><b>⌖</b></div>
          <p>Seguimiento territorial<br /><strong>Costa de Jalisco</strong></p>
        </aside>
      </section>

      {/* Sección 4.1: Alertas Públicas Vigentes (GET /alertas-publicas/) */}
      <section className="section" style={{ paddingTop: '32px', paddingBottom: '32px' }}>
        <Title
          eyebrow="AVISOS VIGENTES"
          title="Alertas epidemiológicas activas"
          text="Avisos oficiales confirmados para la población general de la región costera."
        />

        {loadingAlerts && <LoadingState message="Consultando avisos epidemiológicos..." />}

        {errorAlerts && !loadingAlerts && (
          <ErrorState
            title="Aviso de conexión"
            error={errorAlerts}
            onRetry={recargarAlertas}
          />
        )}

        {!loadingAlerts && !errorAlerts && (!alerts || alerts.length === 0) && (
          <div className="data">
            <b>✓</b>
            <p>
              <strong>Sin alertas vigentes:</strong> En este momento no hay avisos de alerta emitidos para la región costera. Consulta las recomendaciones preventivas para mantener tu entorno libre de criaderos.
            </p>
          </div>
        )}

        {!loadingAlerts && !errorAlerts && alerts && alerts.length > 0 && (
          <div className="alert-list" style={{ marginBottom: '16px' }}>
            {alerts.map((alerta) => (
              <AlertCard key={alerta.id} alert={alerta} />
            ))}
          </div>
        )}
      </section>

      {/* Datos históricos de contexto */}
      <section className="section compact">
        <div className="stats four">
          {statData.map((x) => (
            <Stat key={x[1]} icon={x[0]} label={x[1]} value={x[2]} text={x[3]} />
          ))}
        </div>
        <p className="micro-note">Registros históricos acumulados del conjunto analizado, 2020–2026. Corte de 2026 parcial.</p>
      </section>

      <section className="section">
        <Title
          eyebrow="RESULTADOS HISTÓRICOS DESTACADOS"
          title="Datos para comprender el comportamiento acumulado."
          text="Estos resultados representan registros históricos acumulados y no indican un nivel de riesgo actual."
        />
        <div className="featured-results">
          <article><span>PUERTO VALLARTA</span><strong>1,100</strong><p>confirmados históricos</p></article>
          <article><span>SAN SEBASTIÁN DEL OESTE</span><strong>904.4</strong><p>confirmados acumulados por cada 100,000 habitantes</p></article>
          <article><span>LA HUERTA</span><strong>855.6</strong><p>confirmados acumulados por cada 100,000 habitantes</p></article>
          <article><span>CUAUTITLÁN DE GARCÍA BARRAGÁN</span><strong>800.2</strong><p>confirmados acumulados por cada 100,000 habitantes</p></article>
        </div>
      </section>

      <section className="section coverage">
        <div>
          <Title
            eyebrow="COBERTURA TERRITORIAL"
            title="Consulta los 14 municipios incluidos."
            text="Selecciona un municipio para conocer la delimitación territorial."
          />
          <button className="secondary" onClick={() => go('mapa')}>Abrir mapa territorial</button>
        </div>
        <NeutralMap selected={chosen} onSelect={setChosen} />
      </section>

      <section className="section quick-actions">
        <Card
          icon="⚑"
          title="Alertas epidemiológicas"
          text="Consulta avisos validados e información preventiva oficial."
          action="Ver todas las alertas"
          onClick={() => go('alertas')}
        />
        <Card
          icon="◌"
          title="Información de salud y prevención"
          text="Prevención de dengue, diabetes, hipertensión y notas de salud."
          action="Ver contenidos de salud"
          onClick={() => go('prevencion')}
        />
      </section>
    </>
  );
}
