import { useState, useEffect, useCallback, useRef } from 'react';
import { obtenerEnfermedades } from '../services/enfermedadesService';

/**
 * Hook para consultar el catálogo de enfermedades (GET /enfermedades/)
 * Contempla: loading, success, empty, error y recargar/refetch.
 */
export function useEnfermedades() {
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
      const result = await obtenerEnfermedades({ signal: controller.signal });
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
