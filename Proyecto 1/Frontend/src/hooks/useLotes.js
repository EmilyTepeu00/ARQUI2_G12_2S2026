import { useCallback, useEffect, useState } from "react";
import { lotesApi } from "../api/lotes";

export function useLotes() {
  const [lotes, setLotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await lotesApi.listar();
      setLotes(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "No se pudieron cargar los lotes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const crear = useCallback(
    async (data) => {
      const nuevo = await lotesApi.crear(data);
      await refresh();
      return nuevo;
    },
    [refresh]
  );

  const actualizar = useCallback(
    async (id, data) => {
      const actualizado = await lotesApi.actualizar(id, data);
      await refresh();
      return actualizado;
    },
    [refresh]
  );

  const eliminar = useCallback(
    async (id) => {
      await lotesApi.eliminar(id);
      await refresh();
    },
    [refresh]
  );

  return { lotes, loading, error, refresh, crear, actualizar, eliminar };
}
