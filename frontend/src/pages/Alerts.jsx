import { useAlertas } from '../hooks/useAlertas';
import { Title, AlertCard, LoadingState, EmptyState, ErrorState } from '../components/UI';

export default function Alerts({ go }) {
  const { data: alerts, loading, error, recargar } = useAlertas();

  return (
    <section className="section">
      <Title
        eyebrow="AVISOS OFICIALES"
        title="Alertas epidemiológicas vigentes"
        text="Avisos confirmados y validados por las organizaciones de salud pública para la región costera de Jalisco (14 municipios)."
      />

      {loading && <LoadingState message="Consultando alertas epidemiológicas vigentes..." />}

      {error && !loading && (
        <ErrorState
          title="No se pudieron consultar las alertas"
          error={error}
          onRetry={recargar}
        />
      )}

      {!loading && !error && (!alerts || alerts.length === 0) && (
        <EmptyState
          title="No hay alertas públicas vigentes"
          message="En este momento no existen alertas activas emitidas por las autoridades de salud para la región costera. Cuando se valide un aviso oficial para el periodo actual o próximo, aparecerá publicado en este espacio."
        />
      )}

      {!loading && !error && alerts && alerts.length > 0 && (
        <div className="alert-list">
          {alerts.map((alerta) => (
            <AlertCard key={alerta.id} alert={alerta} />
          ))}
        </div>
      )}

      <div className="data" style={{ marginTop: '30px' }}>
        <b>i</b>
        <p>
          <strong>Criterio epidemiológico regional:</strong> Las alertas aplican a toda la región costera de Jalisco (Costa Sur y Costa-Sierra Occidental). Los avisos se publican únicamente cuando una organización de salud los confirma tras evaluar el modelo predictivo.
        </p>
      </div>
    </section>
  );
}
