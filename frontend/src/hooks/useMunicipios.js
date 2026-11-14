import { useState, useEffect, useCallback, useRef } from 'react';
import { obtenerMunicipios } from '../services/municipiosService';

/**
 * Hook para consultar la lista de los 14 municipios (GET /municipios/)
 * Contempla: loading, success, empty, error y recargar/refetch.
 */
export function useMunicipios() {
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
      const result = await obtenerMunicipios({ signal: controller.signal });
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
