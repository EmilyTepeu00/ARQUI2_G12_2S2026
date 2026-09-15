import { useCallback, useEffect, useState } from "react";
import { puertaApi } from "../api/puerta";

export function usePuertaEventos(params = { limit: 20 }) {
  const [eventos, setEventos] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [e, r] = await Promise.all([puertaApi.eventos(params), puertaApi.resumen()]);
      setEventos(Array.isArray(e) ? e : []);
      setResumen(r);
    } catch (err) {
      setError(err.message || "No se pudieron cargar los eventos de puerta.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { eventos, resumen, loading, error, refresh };
}