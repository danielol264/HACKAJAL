import { useState } from 'react';
import { Title, Stat, Card, Chart } from '../components/UI';
import { municipalities, history, otherDiseases } from '../data/demoData';
import InteractiveCoverageMap from '../components/maps/InteractiveCoverageMap';

// Re-exports de páginas conectadas a la API oficial
export { default as Alerts } from './Alerts';
export { default as Prevention } from './HealthInfo';
export { default as ContentDetail } from './ContentDetail';
export { default as Home } from './Home';

const partial = '2026 es un periodo parcial con corte al 27 de octubre de 2026.';
const statData = [
  ['✓', 'Confirmados', '2,203', 'Registros históricos 2020–2026'],
  ['?', 'Probables', '9,029', 'Pendientes de confirmación'],
  ['—', 'Descartados', '4,235', 'No son casos confirmados'],
  ['⌖', 'Municipios', '14', 'Costa Sur y Costa-Sierra Occidental'],
];

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
      <small>Vista territorial esquemática de los 14 municipios monitoreados.</small>
    </div>
  );
}

export function Epidemiology() {
  return (
    <section className="section">
      <Title
        eyebrow="SITUACIÓN EPIDEMIOLÓGICA"
        title="Dengue: información histórica disponible."
        text="La plataforma no presenta predicciones ni niveles de riesgo actuales mientras el modelo esté en preparación."
      />
      <div className="stats four">
        {statData.slice(0, 3).map((x) => (
          <Stat key={x[1]} icon={x[0]} label={x[1]} value={x[2]} text={x[3]} />
        ))}
      </div>
      <section className="prediction-state">
        <span>PRÓXIMAMENTE</span>
        <h2>Predicción de dengue por región</h2>
        <p>El modelo predictivo regional de casos a 4 semanas es evaluado periódicamente por organizaciones de salud. Cuando se confirme un aviso oficial, se publica en el apartado de Alertas.</p>
        <div>
          <b>Región Costera</b>
          <b>Horizonte 1–4 semanas</b>
          <b>Validación en curso</b>
        </div>
        <small>Las alertas oficiales se emiten únicamente tras la confirmación de las autoridades de salud.</small>
      </section>
      <section className="other-diseases">
        <h2>Otras enfermedades: información de referencia</h2>
        <div className="grid three">
          {otherDiseases.map((d) => (
            <Card key={d[0]} icon="i" title={d[0]} text={<><b>{d[1]}</b><br />{d[2]}</>} />
          ))}
        </div>
      </section>
    </section>
  );
}

export function Municipality() {
  const [query, setQuery] = useState('');
  const list = municipalities.filter((m) => m.name.toLowerCase().includes(query.toLowerCase()));
  return (
    <section className="section">
      <Title
        eyebrow="MUNICIPIOS MONITOREADOS"
        title="Información por territorio."
        text="Consulta los 14 municipios de las regiones Costa Sur y Costa-Sierra Occidental."
      />
      <div className="selector">
        <label htmlFor="municipality">Buscar municipio</label>
        <input
          id="municipality"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Escribe el nombre del municipio (ej. Puerto Vallarta, Cihuatlán...)"
        />
      </div>
      <div className="municipality-list">
        {list.map((m) => (
          <article key={m.name}>
            <div>
              <h2>{m.name}</h2>
              <span>{m.region}</span>
            </div>
            <p><b>Población Censo 2020:</b> Información de referencia</p>
            <p><b>Confirmados históricos:</b> {m.confirmed || 'Información no disponible'}</p>
            <button className="secondary" onClick={() => setQuery(m.name)}>Ver ficha</button>
            {query === m.name && (
              <div className="municipality-detail">
                <b>Información histórica acumulada</b>
                <p>{m.confirmed || m.rate || 'No hay información municipal desglosada disponible para este indicador.'}</p>
                <p>No se muestra un nivel de riesgo actual porque las alertas epidemiológicas oficiales se evalúan a nivel regional.</p>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

export function RiskMap({ go, id }) {
  return (
    <InteractiveCoverageMap
      variant="full"
      go={go}
      initialSelectedId={id}
    />
  );
}

export function History() {
  return (
    <section className="section">
      <Title
        eyebrow="HISTORIAL DEL DENGUE"
        title="Registros por año y estatus."
        text="Los registros confirmados, probables y descartados se muestran por separado."
      />
      <article className="history-chart">
        <div>
          <h2>Registros anuales, 2020–2026</h2>
          <p>Confirmados, probables y descartados.</p>
        </div>
        <HistoryBars />
        <div className="history-legend">
          <span className="confirmed">Confirmados</span>
          <span className="probable">Probables</span>
          <span className="discarded">Descartados</span>
        </div>
      </article>
      <div className="data">
        <b>i</b>
        <p>
          <strong>Corte parcial 2026.</strong><br />
          {partial} No debe compararse directamente con años completos.
        </p>
      </div>
      <div className="grid charts">
        <Chart title="Distribución de casos por enfermedad" sub="Dengue y padecimientos crónicos prioritarios" bar />
        <article className="why">
          <h2>Cómo interpretar los datos</h2>
          <p>Un caso probable no equivale a un caso confirmado. Los descartados se muestran para mantener la transparencia del conjunto analizado.</p>
        </article>
      </div>
    </section>
  );
}

export function HealthCenters() {
  return (
    <section className="section">
      <Title
        eyebrow="CENTROS DE SALUD"
        title="Directorio en preparación."
        text="Los establecimientos y datos de contacto se mostrarán únicamente cuando sean verificados por una fuente institucional."
      />
      <div className="empty">Información institucional en proceso de validación. En caso de emergencia médica, acude al centro de salud u hospital más cercano.</div>
    </section>
  );
}

export function About() {
  return (
    <section className="section">
      <Title
        eyebrow="ACERCA DEL PROYECTO"
        title="Portal Público de Vigilancia y Salud — HackaJal"
        text="Sistema de información preventiva y vigilancia epidemiológica para la población de la región costera de Jalisco."
      />
      <div className="summary" style={{ marginBottom: '24px' }}>
        <h2>Vigilancia comunitaria y salud preventiva</h2>
        <p>
          Este portal web comunica alertas epidemiológicas oficiales, artículos y recomendaciones preventivas para el cuidado de la salud en 14 municipios de Jalisco (regiones Costa Sur y Costa-Sierra Occidental).
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px', marginTop: '16px' }}>
          <div>
            <b>Región de cobertura:</b> Costa Sur y Costa-Sierra Occidental (14 municipios monitoreados).
          </div>
          <div>
            <b>Enfermedad prioritaria:</b> Dengue (modelo predictivo y alertas confirmadas).
          </div>
          <div>
            <b>Información preventiva:</b> Medidas de prevención para Dengue, Diabetes tipo 2, Hipertensión arterial y Obesidad.
          </div>
          <div>
            <b>Participación comunitaria:</b> Encuesta de salud anónima y voluntaria para monitoreo social.
          </div>
        </div>
      </div>
      <div className="data">
        <b>i</b>
        <p>
          <strong>Privacidad y ética:</strong> La plataforma opera sin inicio de sesión y no solicita datos personales como nombres, teléfonos o correos. El portal cumple con las especificaciones técnicas del contrato API_WEB.md.
        </p>
      </div>
    </section>
  );
}
