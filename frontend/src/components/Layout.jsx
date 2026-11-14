const nav = [
  ['inicio', 'Inicio'],
  ['alertas', 'Alertas'],
  ['prevencion', 'Información de salud'],
  ['encuesta', 'Encuesta'],
  ['situacion', 'Situación epidemiológica'],
  ['municipios', 'Municipios'],
  ['mapa', 'Mapa'],
  ['historial', 'Historial'],
  ['acerca', 'Acerca'],
];

export function Brand() {
  return (
    <div className="brand">
      <b>⌖</b>
      <span>
        <strong>Vigilancia y Salud</strong>
        <small>Costa Sur · Costa-Sierra Occidental</small>
      </span>
    </div>
  );
}

export function Navbar({ page, go, open, setOpen }) {
  return (
    <header>
      <div className="nav">
        <button className="brand-btn" onClick={() => go('inicio')} aria-label="Ir al inicio">
          <Brand />
        </button>
        <button
          className="menu"
          onClick={() => setOpen(!open)}
          aria-label="Abrir menú de navegación"
        >
          ☰
        </button>
        <nav className={open ? 'open' : ''}>
          {nav.map(([id, n]) => (
            <button
              className={page === id ? 'active' : ''}
              onClick={() => go(id)}
              key={id}
            >
              {n}
            </button>
          ))}
        </nav>
        <span className="portal">● Portal público</span>
      </div>
    </header>
  );
}

export function Footer({ go }) {
  return (
    <footer>
      <div className="footer-main">
        <div>
          <Brand />
          <p>
            Portal público oficial de información preventiva, alertas epidemiológicas y participación comunitaria para los 14 municipios de la región costera de Jalisco.
          </p>
        </div>
        <div className="footer-links">
          <div>
            <b>Servicios de Salud</b>
            <button onClick={() => go('alertas')}>Alertas oficiales</button>
            <button onClick={() => go('prevencion')}>Información preventiva</button>
            <button onClick={() => go('encuesta')}>Encuesta anónima</button>
          </div>
          <div>
            <b>Información Territorial</b>
            <button onClick={() => go('municipios')}>14 Municipios</button>
            <button onClick={() => go('mapa')}>Mapa regional</button>
            <button onClick={() => go('historial')}>Historial dengue</button>
          </div>
          <div>
            <b>Institucional</b>
            <button onClick={() => go('situacion')}>Situación epidemiológica</button>
            <button onClick={() => go('centros')}>Centros de salud</button>
            <button onClick={() => go('acerca')}>Acerca del proyecto</button>
          </div>
        </div>
      </div>
      <div className="footer-bottom">
        HackAJAL 2026 — Gobierno de Jalisco · Salud Pública
        <span>Vigilancia Epidemiológica Regional · API REST Conforme a API_WEB.md</span>
      </div>
    </footer>
  );
}
