import { useEffect, useState } from 'react';
import { Title, Card, AlertCard } from '../components/UI';
import { api } from '../services/api';

const MESES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

// Preguntas de la encuesta. shortcut: preguntas provisionales; reemplazar por las que defina P1.
const PREGUNTAS = [
  { id: 'fiebre_ultimas_2_semanas', texto: '¿Tú o alguien de tu hogar ha tenido fiebre en las últimas 2 semanas?' },
  { id: 'agua_acumulada_en_casa', texto: '¿Hay recipientes con agua acumulada en tu casa o patio?' },
  { id: 'usa_repelente', texto: '¿Usas repelente o mosquiteros?' },
  { id: 'tiene_diabetes', texto: '¿Alguien en tu hogar tiene diabetes?' },
  { id: 'tiene_hipertension', texto: '¿Alguien en tu hogar tiene hipertensión?' },
];

const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' }) : '');

// Carga datos de la API con estados de carga y error.
function useApi(pedir, deps = []) {
  const [estado, setEstado] = useState({ datos: null, error: null, cargando: true });
  useEffect(() => {
    let vigente = true;
    setEstado({ datos: null, error: null, cargando: true });
    pedir()
      .then((datos) => vigente && setEstado({ datos, error: null, cargando: false }))
      .catch((e) => vigente && setEstado({ datos: null, error: e.mensaje, cargando: false }));
    return () => { vigente = false; };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return estado;
}

function Estado({ cargando, error, vacio, textoVacio }) {
  if (cargando) return <div className="empty">Cargando…</div>;
  if (error) return <div className="empty error-box">{error}</div>;
  if (vacio) return <div className="empty">{textoVacio}</div>;
  return null;
}

const tituloAlerta = (a) => `${a.enfermedad_nombre} · ${MESES[a.mes]} ${a.anio}`;

// ---------- Inicio ----------

export function Home({ go }) {
  const alertas = useApi(api.alertas);
  const municipios = useApi(api.municipios);
  const ultima = alertas.datos?.[0];
  return (
    <>
      <section className="hero dengue-hero">
        <div>
          <h1>Dengue en la Costa de Jalisco</h1>
          <p>Avisos y recomendaciones para los 14 municipios de Costa Sur y Costa-Sierra Occidental.</p>
          <button className="primary" onClick={() => go('alertas')}>Ver alertas</button>
          <button className="secondary" onClick={() => go('prevencion')}>Cómo prevenir</button>
        </div>
        <aside className={`estado-region ${ultima ? 'con-alerta' : ''}`}>
          <small>Situación actual</small>
          {alertas.cargando
            ? <strong>Consultando…</strong>
            : ultima
              ? <><strong>Alerta de dengue</strong><span>{MESES[ultima.mes]} {ultima.anio}</span><button onClick={() => go('alertas')}>Leer aviso →</button></>
              : <><strong>Sin alertas vigentes</strong><span>Sigue las medidas de prevención.</span></>}
        </aside>
      </section>

      {ultima && (
        <section className="section compact">
          <AlertCard alert={{ level: 'high', title: tituloAlerta(ultima), text: ultima.mensaje_publico, municipality: 'Región costera', date: `Publicada el ${fecha(ultima.publicada_en)}` }} />
        </section>
      )}

      <section className="section quick-actions four-actions">
        <Card title="Alertas" text="Avisos que revisó y confirmó personal de salud." action="Ver alertas" onClick={() => go('alertas')} />
        <Card title="Prevención" text="Qué hacer en casa para evitar el mosquito." action="Ver recomendaciones" onClick={() => go('prevencion')} />
        <Card title="Artículos" text="Información sobre dengue, diabetes y otros padecimientos." action="Leer artículos" onClick={() => go('articulos')} />
        <Card title="Encuesta" text="Cuéntanos cómo está tu comunidad. Es anónima." action="Responder" onClick={() => go('encuesta')} />
      </section>

      <section className="section coverage">
        <div><Title title="Municipios de la región" text="Las alertas aplican a los 14 municipios." /></div>
        <div className="neutral-map">
          <div className="region-label coast">Costa Sur</div><div className="region-label sierra">Costa-Sierra<br />Occidental</div>
          <Estado {...municipios} vacio={!municipios.datos?.length} textoVacio="Sin municipios registrados." />
          {municipios.datos?.length > 0 && (
            <div className="neutral-map-grid">
              {municipios.datos.map((m) => <button key={m.clave_inegi} className={m.region === 'Costa Sur' ? 'coast' : 'sierra'} type="button">{m.nombre}</button>)}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

// ---------- Alertas ----------

export function Alerts() {
  const { datos, error, cargando } = useApi(api.alertas);
  return (
    <section className="section">
      <Title title="Alertas vigentes" text="Solo se publican las alertas que revisó personal de salud." />
      <Estado cargando={cargando} error={error} vacio={!datos?.length} textoVacio="No hay alertas vigentes para la región costera." />
      {datos?.length > 0 && (
        <div className="alert-list">
          {datos.map((a) => (
            <AlertCard key={a.id} alert={{ level: 'high', title: tituloAlerta(a), text: a.mensaje_publico, municipality: 'Región costera', date: `Publicada el ${fecha(a.publicada_en)}` }} />
          ))}
        </div>
      )}
    </section>
  );
}

// ---------- Prevención (información fija + contenido de la API) ----------

const PREVENCION_DENGUE = [
  ['Elimina criaderos', 'Lava, tapa, voltea y tira recipientes con agua.'],
  ['Evita picaduras', 'Usa repelente y ropa que cubra brazos y piernas.'],
  ['Identifica síntomas', 'Fiebre, dolor de cabeza o malestar: busca orientación profesional.'],
  ['Acude a un centro de salud', 'No te automediques si presentas señales de alarma.'],
  ['Señales de alarma', 'Busca atención urgente ante dolor abdominal intenso, vómito persistente o sangrado.'],
];

export function Prevention({ go }) {
  const [enfermedad, setEnfermedad] = useState('');
  const enfermedades = useApi(api.enfermedades);
  const contenido = useApi(() => api.contenido({ tipo: 'prevencion', enfermedad }), [enfermedad]);
  return (
    <>
      <section className="pre-hero">
        <div><h1>Prevención del dengue</h1><p>Revisa tu casa cada semana y elimina los lugares donde el mosquito pueda reproducirse.</p></div>
      </section>
      <section className="section">
        <div className="grid three">
          {PREVENCION_DENGUE.map((x) => <article className="pre-card" key={x[0]}><h2>{x[0]}</h2><p>{x[1]}</p></article>)}
        </div>
      </section>
      <section className="section">
        <Title title="Por padecimiento" text="Dengue, diabetes, hipertensión, obesidad y más." />
        <div className="selector">
          <label htmlFor="enfermedad">Filtrar por padecimiento</label>
          <select id="enfermedad" value={enfermedad} onChange={(e) => setEnfermedad(e.target.value)}>
            <option value="">Todos</option>
            {enfermedades.datos?.map((e) => <option key={e.clave} value={e.clave}>{e.nombre}</option>)}
          </select>
        </div>
        <ListaContenido {...contenido} go={go} textoVacio="Aún no hay información publicada para este padecimiento." />
      </section>
    </>
  );
}

// ---------- Artículos y notas ----------

export function Articles({ go }) {
  const [id, setId] = useState(null);
  const articulos = useApi(() => api.contenido({ tipo: 'articulo' }));
  const notas = useApi(() => api.contenido({ tipo: 'nota' }));
  if (id) return <Articulo id={id} volver={() => setId(null)} />;
  return (
    <section className="section">
      <Title title="Artículos y avisos" text="Información publicada por la Secretaría de Salud y organizaciones de salud." />
      <h2 className="subtitulo">Artículos</h2>
      <ListaContenido {...articulos} abrir={setId} go={go} textoVacio="Aún no hay artículos publicados." />
      <h2 className="subtitulo">Avisos</h2>
      <ListaContenido {...notas} abrir={setId} go={go} textoVacio="Aún no hay avisos publicados." />
    </section>
  );
}

function ListaContenido({ datos, error, cargando, abrir, textoVacio }) {
  const [abierto, setAbierto] = useState(null);
  return (
    <>
      <Estado cargando={cargando} error={error} vacio={!datos?.length} textoVacio={textoVacio} />
      {datos?.length > 0 && (
        <div className="grid three">
          {datos.map((c) => (
            <article className="card" key={c.id}>
              <h3>{c.titulo}</h3>
              <p className={abrir || abierto === c.id ? '' : 'resumen'}>{abrir ? c.cuerpo.slice(0, 160) + (c.cuerpo.length > 160 ? '…' : '') : c.cuerpo}</p>
              {abrir
                ? <button onClick={() => abrir(c.id)}>Leer completo →</button>
                : <button onClick={() => setAbierto(abierto === c.id ? null : c.id)}>{abierto === c.id ? 'Ver menos' : 'Ver más'} →</button>}
            </article>
          ))}
        </div>
      )}
    </>
  );
}

function Articulo({ id, volver }) {
  const { datos, error, cargando } = useApi(() => api.articulo(id), [id]);
  return (
    <section className="section">
      <button className="secondary" onClick={volver}>← Volver a la lista</button>
      <Estado cargando={cargando} error={error} />
      {datos && (
        <article className="article-detail">
          <span>{datos.tipo === 'nota' ? 'Aviso' : 'Artículo'} · {fecha(datos.fecha)}</span>
          <h1>{datos.titulo}</h1>
          {datos.imagen_url && <img src={datos.imagen_url} alt="" />}
          <p className="article-body">{datos.cuerpo}</p>
          {datos.url_fuente && <p><a href={datos.url_fuente} target="_blank" rel="noreferrer">Ver fuente original</a></p>}
          {datos.autor && <small>Publicado por {datos.autor}</small>}
        </article>
      )}
    </section>
  );
}

// ---------- Encuesta ----------

export function Survey() {
  const municipios = useApi(api.municipios);
  const [municipio, setMunicipio] = useState('');
  const [respuestas, setRespuestas] = useState({});
  const [consentimiento, setConsentimiento] = useState(false);
  const [envio, setEnvio] = useState({ enviando: false, ok: false, error: null });

  const completa = municipio && consentimiento && Object.keys(respuestas).length > 0;

  const enviar = async (e) => {
    e.preventDefault();
    setEnvio({ enviando: true, ok: false, error: null });
    try {
      await api.enviarEncuesta(municipio, respuestas);
      setEnvio({ enviando: false, ok: true, error: null });
    } catch (err) {
      setEnvio({ enviando: false, ok: false, error: err.mensaje });
    }
  };

  if (envio.ok) {
    return (
      <section className="section">
        <Title title="Gracias por responder" text="Tu respuesta es anónima y ayuda a conocer la situación de tu comunidad." />
      </section>
    );
  }

  return (
    <section className="section">
      <Title title="Encuesta" text="Es anónima: no pedimos tu nombre, correo ni ubicación, solo tu municipio." />
      <form className="survey" onSubmit={enviar}>
        <div className="selector">
          <label htmlFor="municipio">Municipio donde vives</label>
          <select id="municipio" value={municipio} onChange={(e) => setMunicipio(e.target.value)} required>
            <option value="">Selecciona tu municipio</option>
            {municipios.datos?.map((m) => <option key={m.clave_inegi} value={m.clave_inegi}>{m.nombre}</option>)}
          </select>
          {municipios.error && <small className="error-text">{municipios.error}</small>}
        </div>

        {PREGUNTAS.map((p) => (
          <fieldset className="survey-question" key={p.id}>
            <legend>{p.texto}</legend>
            {[['Sí', true], ['No', false]].map(([texto, valor]) => (
              <label key={texto}>
                <input type="radio" name={p.id} checked={respuestas[p.id] === valor} onChange={() => setRespuestas({ ...respuestas, [p.id]: valor })} /> {texto}
              </label>
            ))}
          </fieldset>
        ))}

        <label className="consent">
          <input type="checkbox" checked={consentimiento} onChange={(e) => setConsentimiento(e.target.checked)} />
          Acepto que mis respuestas anónimas se usen con fines estadísticos de salud pública.
        </label>

        {envio.error && <div className="empty error-box">{envio.error}</div>}
        <button className="primary" type="submit" disabled={!completa || envio.enviando}>
          {envio.enviando ? 'Enviando…' : 'Enviar respuestas'}
        </button>
      </form>
    </section>
  );
}

// ---------- Acerca de ----------

export function About() {
  return (
    <section className="section">
      <Title title="Acerca de este sitio" text="Proyecto de vigilancia epidemiológica del dengue para los 14 municipios de la región costera de Jalisco. Las alertas se generan con un modelo predictivo y solo se publican después de que una organización de salud las revisa." />
    </section>
  );
}
