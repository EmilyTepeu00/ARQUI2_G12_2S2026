import { useCallback, useEffect, useState } from "react";
import { operadoresApi } from "../api/operadores";

export function useOperadores() {
  const [operadores, setOperadores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await operadoresApi.listar();
      setOperadores(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "No se pudieron cargar los operadores");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const crear = useCallback(
    async (data) => {
      const nuevo = await operadoresApi.crear(data);
      await refresh();
      return nuevo;
    },
    [refresh]
  );

  const actualizar = useCallback(
    async (id, data) => {
      const actualizado = await operadoresApi.actualizar(id, data);
      await refresh();
      return actualizado;
    },
    [refresh]
  );

  const eliminar = useCallback(
    async (id) => {
      await operadoresApi.eliminar(id);
      await refresh();
    },
    [refresh]
  );

  return { operadores, loading, error, refresh, crear, actualizar, eliminar };
}