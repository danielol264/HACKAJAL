export function BackButton({ onClick }) {
  return <button className="back-button" onClick={onClick} aria-label="Regresar a la página anterior"><span aria-hidden="true">←</span> Regresar</button>;
}

export function Title({ title, text }) {
  return <div className="title"><h1>{title}</h1>{text && <p>{text}</p>}</div>;
}

export function Card({ title, text, action, onClick }) {
  return (
    <article className="card">
      <h3>{title}</h3>
      <p>{text}</p>
      {action && <button onClick={onClick}>{action} →</button>}
    </article>
  );
}

export function AlertCard({ alert }) {
  return (
    <article className="alert-card">
      <div>
        <RiskBadge level={alert.level} label="Alerta confirmada" />
        <h2>{alert.title}</h2>
        <p>{alert.text}</p>
      </div>
      <aside><b>{alert.municipality}</b><small>{alert.date}</small></aside>
    </article>
  );
}

export function RiskBadge({ level, label }) {
  return <span className={`risk-badge ${level}`}>{label}</span>;
}
