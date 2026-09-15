import { useEffect, useState } from "react";
import { sensorsApi } from "../api/sensors";

export function useConnectionStatus(intervalMs = 5000) {
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetchEstado = () => {
      sensorsApi
        .estado()
        .then((data) => {
          if (!cancelled) setEstado(data);
        })
        .catch(() => {
          if (!cancelled) setEstado((prev) => prev ?? { serial_conectado: false });
        });
    };

    fetchEstado();
    const id = setInterval(fetchEstado, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return estado;
}
