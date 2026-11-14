import { useContenidoDetalle } from '../hooks/useContenidoDetalle';
import { Title, Button, LoadingState, ErrorState } from '../components/UI';

export default function ContentDetail({ id, go }) {
  const { data: item, loading, error, recargar } = useContenidoDetalle(id);

  if (loading) {
    return (
      <section className="section">
        <LoadingState message="Cargando artículo de salud..." />
      </section>
    );
  }

  if (error || !item) {
    const es404 = error?.status === 404 || !item;
    return (
      <section className="section">
        <div style={{ marginBottom: '20px' }}>
          <button className="back-button" onClick={() => go('prevencion')}>
            ← Volver a Información de Salud
          </button>
        </div>
        <ErrorState
          title={es404 ? 'Contenido no disponible' : 'Error al cargar el contenido'}
          error={
            es404
              ? 'El artículo solicitado no existe, fue retirado o no está publicado para consulta pública.'
              : error
          }
          onRetry={es404 ? null : recargar}
        />
      </section>
    );
  }

  return (
    <section className="section">
      <div style={{ marginBottom: '24px' }}>
        <button className="back-button" onClick={() => go('prevencion')}>
          ← Volver a Información de Salud
        </button>
      </div>

      <article className="content-detail-view">
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '6px',
              background: '#e8f5f4',
              color: '#087b7e',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
            }}
          >
            {item.tipoEtiqueta || item.tipo}
          </span>
          {item.enfermedad && (
            <span
              style={{
                padding: '4px 10px',
                borderRadius: '6px',
                background: '#f2f4f5',
                color: '#556972',
                fontSize: '11px',
                fontWeight: 600,
              }}
            >
              Enfermedad: {item.enfermedad.toUpperCase()}
            </span>
          )}
        </div>

        <h1 style={{ fontSize: '32px', lineHeight: 1.25, color: '#1a2830', margin: '0 0 16px' }}>
          {item.titulo}
        </h1>

        <div className="content-detail-meta">
          {item.autor && <span>Por: <strong>{item.autor}</strong></span>}
          {item.fechaFormateada && <span>Publicado: <strong>{item.fechaFormateada}</strong></span>}
        </div>

        {item.tieneImagen && (
          <img
            src={item.imagen_url}
            alt={item.titulo}
            className="content-detail-img"
            loading="lazy"
          />
        )}

        <div className="content-detail-body">
          {item.cuerpo}
        </div>

        {item.tieneFuente && (
          <div
            style={{
              marginTop: '32px',
              paddingTop: '20px',
              borderTop: '1px solid #eef3f4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <span style={{ fontSize: '12px', color: '#68808b' }}>
              Fuente oficial / Enlace institucional:
            </span>
            <a
              href={item.url_fuente}
              target="_blank"
              rel="noopener noreferrer"
              className="primary"
              style={{
                textDecoration: 'none',
                display: 'inline-block',
                padding: '10px 16px',
                fontSize: '12px',
              }}
            >
              Consultar fuente externa ↗
            </a>
          </div>
        )}
      </article>
    </section>
  );
}
