export const Demo = () => (
  <div className="demo">
    <b>i</b>
    <span>
      <strong>Vista demostrativa.</strong> Las cifras e indicadores son ilustrativos y no representan datos epidemiológicos reales.
    </span>
  </div>
);

export function BackButton({ onClick }) {
  return (
    <button className="back-button" onClick={onClick} aria-label="Regresar al apartado anterior">
      <span aria-hidden="true">←</span> Regresar
    </button>
  );
}

export function Title({ eyebrow, title, text }) {
  return (
    <div className="title">
      {eyebrow && <span>{eyebrow}</span>}
      {title && <h1>{title}</h1>}
      {text && <p>{text}</p>}
    </div>
  );
}

export function Stat({ icon, label, value, text }) {
  return (
    <article className="stat">
      <i>{icon}</i>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{text}</small>
      </div>
    </article>
  );
}

export function Card({ icon, title, text, action, onClick }) {
  return (
    <article className="card">
      <i>{icon}</i>
      <h3>{title}</h3>
      <p>{text}</p>
      {action && <button onClick={onClick}>{action} →</button>}
    </article>
  );
}

export function RiskBadge({ level = 'low', label }) {
  const normLevel = (level || 'low').toLowerCase();
  const clase = normLevel === 'high' || normLevel === 'alto'
    ? 'high'
    : normLevel === 'moderate' || normLevel === 'medio'
    ? 'moderate'
    : normLevel === 'critical' || normLevel === 'critico'
    ? 'critical'
    : 'low';

  const textoDefault = clase === 'high'
    ? 'Importancia alta'
    : clase === 'moderate'
    ? 'Importancia moderada'
    : clase === 'critical'
    ? 'Aviso crítico'
    : 'Aviso epidemiológico';

  return (
    <span className={`risk-badge ${clase}`}>
      ● {label || textoDefault}
    </span>
  );
}

export function AlertCard({ alert }) {
  if (!alert) return null;

  // Soporta tanto la estructura oficial del backend API_WEB.md como la adaptada
  const enfermedadNombre = alert.enfermedad_nombre || alert.enfermedad || 'Dengue';
  const mensaje = alert.mensaje_publico || alert.mensaje || alert.text || '';
  const titulo = alert.titulo || `Alerta: ${enfermedadNombre}`;
  const region = alert.region || 'Región Costera de Jalisco (14 municipios)';
  const fecha = alert.fecha || (alert.publicada_en ? new Date(alert.publicada_en).toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' }) : '');
  const periodo = alert.periodo || (alert.mes && alert.anio ? `Periodo: ${alert.mes}/${alert.anio}` : '');

  return (
    <article className="alert-card">
      <div>
        <RiskBadge level={alert.level || 'moderate'} label={periodo || 'Alerta vigente'} />
        <h2>{titulo}</h2>
        <p style={{ whiteSpace: 'pre-line' }}>{mensaje}</p>
      </div>
      <aside>
        <b>{region}</b>
        {fecha && <small>Publicada: {fecha}</small>}
      </aside>
    </article>
  );
}

export function Chart({ title, sub, bar = false }) {
  return (
    <article className="chart">
      <div>
        <h3>{title}</h3>
        <small>{sub || 'Visualización demostrativa'}</small>
      </div>
      {bar ? (
        <div className="bars">
          {[45, 68, 37, 54].map((v, i) => (
            <span key={i}>
              <i style={{ height: v + '%' }} />
              <b>{['Dengue', 'Diabetes', 'Hipertensión', 'Obesidad'][i]}</b>
            </span>
          ))}
        </div>
      ) : (
        <div className="line">
          <svg viewBox="0 0 600 180" preserveAspectRatio="none">
            <defs>
              <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                <stop stopColor="#0a7a7d" stopOpacity=".25" />
                <stop offset="1" stopColor="#0a7a7d" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0 143 C45 136 70 108 110 122 S170 83 208 99 S260 126 300 77 S355 68 395 86 S445 50 480 63 S545 25 600 40V180H0Z"
              fill="url(#g)"
            />
            <path
              d="M0 143 C45 136 70 108 110 122 S170 83 208 99 S260 126 300 77 S355 68 395 86 S445 50 480 63 S545 25 600 40"
              fill="none"
              stroke="#0a7a7d"
              strokeWidth="4"
            />
          </svg>
          <div>
            Ene <span>Mar</span><span>May</span><span>Jul</span><span>Sep</span><span>Nov</span>
          </div>
        </div>
      )}
    </article>
  );
}

// Primitivas de interfaz de usuario
export const Button = ({ type = 'button', disabled = false, onClick, className = 'button', children }) => (
  <button type={type} disabled={disabled} onClick={onClick} className={className}>
    {children}
  </button>
);

export const Input = ({ id, value, onChange, placeholder = '', required = false, className = 'input' }) => (
  <input
    id={id}
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    required={required}
    className={className}
  />
);

export const Select = ({ id, value, onChange, required = false, className = 'select', children }) => (
  <select id={id} value={value} onChange={onChange} required={required} className={className}>
    {children}
  </select>
);

export const Checkbox = ({ id, checked, onChange, required = false, className = 'checkbox' }) => (
  <input
    type="checkbox"
    id={id}
    checked={checked}
    onChange={onChange}
    required={required}
    className={className}
  />
);

export const Spinner = ({ size = 'md', label = 'Cargando...' }) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: '#087b7e', fontSize: '13px' }}>
    <span
      className={`spinner spinner-${size}`}
      style={{
        display: 'inline-block',
        width: size === 'sm' ? '16px' : '24px',
        height: size === 'sm' ? '16px' : '24px',
        border: '2px solid #b5dcd8',
        borderTopColor: '#087b7e',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }}
      aria-hidden="true"
    />
    <span>{label}</span>
  </div>
);

export const Alert = ({ type = 'info', children }) => {
  const bg = type === 'error' ? '#fdeaea' : type === 'success' ? '#e5f6ea' : '#f1faf8';
  const col = type === 'error' ? '#a42c2c' : type === 'success' ? '#21683c' : '#20313b';
  const border = type === 'error' ? '#f5c2c2' : type === 'success' ? '#c2e7cc' : '#cfe5e2';

  return (
    <div
      role="alert"
      style={{
        padding: '12px 16px',
        borderRadius: '8px',
        background: bg,
        color: col,
        border: `1px solid ${border}`,
        fontSize: '13px',
        margin: '12px 0',
      }}
    >
      {children}
    </div>
  );
};

// Estados estándar para UX (Bloque 6: Loading, Success, Empty, Error, Retry)
export function LoadingState({ message = 'Cargando información...' }) {
  return (
    <div style={{ padding: '36px 20px', textAlign: 'center' }}>
      <Spinner label={message} />
    </div>
  );
}

export function EmptyState({ title = 'No hay información disponible', message = 'No se encontraron registros para mostrar en este momento.' }) {
  return (
    <div className="empty" style={{ textAlign: 'center', padding: '32px 20px' }}>
      <h3 style={{ margin: '0 0 8px', fontSize: '16px', color: '#354954' }}>{title}</h3>
      <p style={{ margin: 0, color: '#68808b', fontSize: '13px' }}>{message}</p>
    </div>
  );
}

export function ErrorState({ title = 'Error al consultar el servidor', error, onRetry }) {
  const msg = typeof error === 'string' ? error : error?.message || 'No se pudo conectar con el servidor';
  return (
    <div
      style={{
        padding: '24px',
        borderRadius: '10px',
        background: '#fdeaea',
        border: '1px solid #f5c2c2',
        color: '#a42c2c',
        margin: '16px 0',
      }}
    >
      <h3 style={{ margin: '0 0 6px', fontSize: '15px' }}>{title}</h3>
      <p style={{ margin: '0 0 14px', fontSize: '13px' }}>{msg}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="secondary"
          style={{ borderColor: '#a42c2c', color: '#a42c2c', background: '#fff' }}
        >
          ↻ Reintentar conexión
        </button>
      )}
    </div>
  );
}
