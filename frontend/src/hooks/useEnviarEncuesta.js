import { useState, useRef, useCallback } from 'react';
import { enviarEncuesta } from '../services/encuestaService';

/**
 * Hook para gestionar el envío anónimo de la encuesta ciudadana (POST /encuesta/)
 * Contempla:
 * - Prevención de envíos duplicados mientras está enviando.
 * - Manejo de estados: loading, error, success.
 * - Cancelación segura con AbortController.
 * - Función reset() para reiniciar el formulario tras un envío o error.
 */
export function useEnviarEncuesta() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const controllerRef = useRef(null);

  const send = useCallback(async (municipio, respuestas) => {
    if (loading) return;

    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await enviarEncuesta(municipio, respuestas, { signal: controller.signal });
      setSuccess(true);
      return response;
    } catch (e) {
      if (e.name === 'AbortError') return;
      setError(e);
      throw e;
    } finally {
      setLoading(false);
      controllerRef.current = null;
    }
  }, [loading]);

  const cancel = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    setLoading(false);
  }, []);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setSuccess(false);
  }, []);

  return {
    send,
    loading,
    error,
    success,
    cancel,
    reset,
  };
}
