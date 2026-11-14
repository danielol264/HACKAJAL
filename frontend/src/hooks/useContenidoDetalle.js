import { useState, useEffect, useCallback, useRef } from 'react';
import { obtenerArticulo } from '../services/contenidoService';

/**
 * Hook para consultar el detalle de un contenido individual (GET /contenido/{id}/)
 * Contempla: loading, success, 404 (Contenido no disponible), error y recargar/refetch.
 * 
 * @param {string|number} id - Identificador del contenido
 */
export function useContenidoDetalle(id) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(id));
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const fetchData = useCallback(async () => {
    if (!id) {
      setData(null);
      setLoading(false);
      return;
    }

    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await obtenerArticulo(id, { signal: controller.signal });
      setData(result);
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

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
