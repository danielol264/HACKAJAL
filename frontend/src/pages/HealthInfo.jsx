import { useState } from 'react';
import { useContenido } from '../hooks/useContenido';
import { useEnfermedades } from '../hooks/useEnfermedades';
import { Title, LoadingState, EmptyState, ErrorState } from '../components/UI';

export default function HealthInfo({ go }) {
  const [tipoFiltro, setTipoFiltro] = useState('');
  const [enfermedadFiltro, setEnfermedadFiltro] = useState('');

  const filtros = {};
  if (tipoFiltro) filtros.tipo = tipoFiltro;
  if (enfermedadFiltro) filtros.enfermedad = enfermedadFiltro;

  const { data: contenidos, loading, error, recargar } = useContenido(filtros);
  const { data: enfermedades, loading: loadingEnf } = useEnfermedades();

  return (
    <>
      <section className="pre-hero">
        <div>
          <span>INFORMACIÓN Y PREVENCIÓN DE SALUD</span>
          <h1>Recomendaciones, notas y artículos oficiales.</h1>
          <p>
            Medidas preventivas para el cuidado de la salud comunitaria: dengue, diabetes, hipertensión arterial y hábitos saludables en Jalisco.
          </p>
        </div>
        <b>◌</b>
      </section>

      <section className="section">
        <Title
          eyebrow="CONTENIDOS PUBLICADOS"
          title="Prevención y guías de salud"
          text="Consulta recomendaciones verificadas para la población de la región costera."
        />

        {/* Barra de filtros dinámicos conforme a GET /contenido/?tipo=&enfermedad= y GET /enfermedades/ */}
        <div className="filter-row" style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', border: '1px solid #dfebea', marginBottom: '28px' }}>
          <label>
            <span>Tipo de contenido</span>
            <select
              value={tipoFiltro}
              onChange={(e) => setTipoFiltro(e.target.value)}
              aria-label="Filtrar por tipo de contenido"
            >
              <option value="">Todos los contenidos</option>
              <option value="prevencion">Medidas preventivas</option>
              <option value="articulo">Artículos científicos</option>
              <option value="nota">Notas informativas</option>
            </select>
          </label>

          <label>
            <span>Enfermedad o tema</span>
            <select
              value={enfermedadFiltro}
              onChange={(e) => setEnfermedadFiltro(e.target.value)}
              aria-label="Filtrar por enfermedad"
              disabled={loadingEnf}
            >
              <option value="">Todas las enfermedades</option>
              {enfermedades &&
                enfermedades.map((enf) => (
                  <option key={enf.clave} value={enf.clave}>
                    {enf.nombre}
                  </option>
                ))}
            </select>
          </label>

          {(tipoFiltro || enfermedadFiltro) && (
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                className="secondary"
                onClick={() => {
                  setTipoFiltro('');
                  setEnfermedadFiltro('');
                }}
                style={{ padding: '9px 14px', fontSize: '11px' }}
              >
                Limpiar filtros
              </button>
            </div>
          )}
        </div>

        {/* Estados de carga, error, vacío y lista */}
        {loading && <LoadingState message="Consultando información de salud..." />}

        {error && !loading && (
          <ErrorState
            title="No se pudieron consultar los contenidos"
            error={error}
            onRetry={recargar}
          />
        )}

        {!loading && !error && (!contenidos || contenidos.length === 0) && (
          <EmptyState
            title="Sin contenidos disponibles"
            message="No se encontraron artículos o notas que coincidan con los filtros seleccionados."
          />
        )}

        {!loading && !error && contenidos && contenidos.length > 0 && (
          <div className="grid three">
            {contenidos.map((item) => (
              <article
                className="pre-card"
                key={item.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  background: '#fff',
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: '#edf8f7',
                        color: '#087b7e',
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                      }}
                    >
                      {item.tipoEtiqueta || item.tipo}
                    </span>
                    {item.fechaFormateada && (
                      <small style={{ color: '#8898a1', fontSize: '10px' }}>
                        {item.fechaFormateada}
                      </small>
                    )}
                  </div>

                  {item.tieneImagen && (
                    <img
                      src={item.imagen_url}
                      alt={item.titulo}
                      style={{
                        width: '100%',
                        height: '140px',
                        objectFit: 'cover',
                        borderRadius: '6px',
                        marginBottom: '12px',
                      }}
                      loading="lazy"
                    />
                  )}

                  <h2 style={{ fontSize: '18px', margin: '6px 0 10px', color: '#1d2e37' }}>
                    {item.titulo}
                  </h2>

                  <p
                    style={{
                      color: '#657780',
                      fontSize: '12px',
                      lineHeight: 1.6,
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {item.cuerpo}
                  </p>
                </div>

                <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #f0f4f5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  {item.autor ? (
                    <small style={{ color: '#7a8c95', fontSize: '10px' }}>Por: {item.autor}</small>
                  ) : (
                    <span />
                  )}
                  <button
                    className="secondary"
                    onClick={() => go('contenidos', { id: item.id })}
                    style={{ padding: '6px 10px', fontSize: '11px', margin: 0 }}
                  >
                    Leer completo →
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
