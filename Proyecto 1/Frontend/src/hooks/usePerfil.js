import { useCallback, useEffect, useState } from "react";
import { perfilApi } from "../api/perfil";

export function usePerfil() {
  const [perfil, setPerfil] = useState(null);
  const [informe, setInforme] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, i] = await Promise.all([perfilApi.obtener(), perfilApi.informe({ dias: 7 })]);
      setPerfil(p);
      setInforme(i);
    } catch (err) {
      setError(err.message || "No se pudo cargar su perfil");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { perfil, informe, loading, error, refresh };
}