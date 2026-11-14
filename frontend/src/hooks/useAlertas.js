import { useState, useEffect, useCallback, useRef } from 'react';
import { obtenerAlertas } from '../services/alertasService';

/**
 * Hook para consultar las alertas públicas vigentes (GET /alertas-publicas/)
 * Contempla los 5 estados: loading, success, empty, error y retry (recargar).
 */
export function useAlertas() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const fetchData = useCallback(async () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await obtenerAlertas({ signal: controller.signal });
      setData(result);
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    return () => {
      if (controllerRef.current) controllerRef.current.abort();
    };
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    recargar: fetchData,
    refetch: fetchData,
  };
}
