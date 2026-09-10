import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../api/client";
import { sensorsApi } from "../api/sensors";
import { MAX_CHART_POINTS } from "../utils/constants";

/**
 * Se suscribe al stream SSE del backend (/api/sensores/stream) para recibir
 * lecturas del Arduino en tiempo real, y mantiene un historial reciente para
 * graficar. Si el stream se cae, EventSource reintenta solo; además hacemos
 * polling de respaldo a /api/sensores/actual mientras el stream no esté vivo.
 */
export function useSensorStream() {
  const [lectura, setLectura] = useState(null);
  const [history, setHistory] = useState([]);
  const [streamConnected, setStreamConnected] = useState(false);
  const [error, setError] = useState(null);
  const fallbackIntervalRef = useRef(null);

  const pushLectura = (data) => {
    setLectura(data);
    setHistory((prev) => {
      const next = [...prev, { ...data, _t: Date.now() }];
      return next.slice(-MAX_CHART_POINTS);
    });
  };

  useEffect(() => {
    let cancelled = false;

    sensorsApi
      .actual()
      .then((data) => {
        if (!cancelled && data) pushLectura(data);
      })
      .catch(() => {});

    sensorsApi
      .historial(MAX_CHART_POINTS)
      .then((data) => {
        if (cancelled || !Array.isArray(data)) return;
        const ordered = [...data].reverse();
        setHistory((prev) => (prev.length ? prev : ordered.map((d) => ({ ...d, _t: Date.now() }))));
      })
      .catch(() => {});

    const source = new EventSource(`${API_BASE_URL}/api/sensores/stream`);

    source.onopen = () => {
      if (cancelled) return;
      setStreamConnected(true);
      setError(null);
      if (fallbackIntervalRef.current) {
        clearInterval(fallbackIntervalRef.current);
        fallbackIntervalRef.current = null;
      }
    };

    source.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data);
        pushLectura(data);
        setStreamConnected(true);
      } catch {
        // línea inválida, se ignora
      }
    };

    source.onerror = () => {
      if (cancelled) return;
      setStreamConnected(false);
      setError("Sin conexión con el stream del backend, reintentando...");
      if (!fallbackIntervalRef.current) {
        fallbackIntervalRef.current = setInterval(() => {
          sensorsApi
            .actual()
            .then((data) => {
              if (!cancelled && data) pushLectura(data);
            })
            .catch(() => {});
        }, 3000);
      }
    };

    return () => {
      cancelled = true;
      source.close();
      if (fallbackIntervalRef.current) clearInterval(fallbackIntervalRef.current);
    };
  }, []);

  return { lectura, history, streamConnected, error };
}
