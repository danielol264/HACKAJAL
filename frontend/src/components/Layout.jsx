const nav = [['inicio', 'Inicio'], ['alertas', 'Alertas'], ['prevencion', 'Prevención'], ['articulos', 'Artículos'], ['encuesta', 'Encuesta']];

export function Brand() {
  return <div className="brand"><span><strong>Vigilancia del dengue</strong><small>Costa de Jalisco</small></span></div>;
}

export function Navbar({ page, go, open, setOpen }) {
  return (
    <header>
      <div className="nav">
        <button className="brand-btn" onClick={() => go('inicio')}><Brand /></button>
        <button className="menu" onClick={() => setOpen(!open)} aria-label="Abrir menú">☰</button>
        <nav className={open ? 'open' : ''}>
          {nav.map(([id, n]) => <button className={page === id ? 'active' : ''} onClick={() => go(id)} key={id}>{n}</button>)}
        </nav>
      </div>
    </header>
  );
}

export function Footer({ go }) {
  return (
    <footer>
      <div className="footer-main">
        <div><Brand /><p>Información preventiva y alertas sobre dengue para los 14 municipios de la región costera de Jalisco.</p></div>
        <div className="footer-links">
          <div><b>Información</b><button onClick={() => go('alertas')}>Alertas</button><button onClick={() => go('prevencion')}>Prevención</button><button onClick={() => go('articulos')}>Artículos</button></div>
          <div><b>Participa</b><button onClick={() => go('encuesta')}>Encuesta</button><button onClick={() => go('acerca')}>Acerca del sistema</button></div>
        </div>
      </div>
      <div className="footer-bottom">HackAJAL 2026 <span>Región costera de Jalisco</span></div>
    </footer>
  );
}
