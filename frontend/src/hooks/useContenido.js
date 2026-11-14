import { useState, useEffect, useCallback, useRef } from 'react';
import { obtenerContenido } from '../services/contenidoService';

/**
 * Hook para consultar la lista de contenido de salud (GET /contenido/)
 * Soporta filtros por tipo ('prevencion' | 'articulo' | 'nota') y por clave de enfermedad.
 * Contempla: loading, success, empty, error y recargar/refetch.
 * 
 * @param {Object} filters - { tipo?, enfermedad? }
 */
export function useContenido(filters = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const filtersKey = JSON.stringify(filters);

  const fetchData = useCallback(async () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await obtenerContenido(filters, { signal: controller.signal });
      setData(result);
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filtersKey]);

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
