import { useState } from "react";
import toast from "react-hot-toast";
import { FileDown } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePerfil } from "../hooks/usePerfil";
import { descargarReportePropio } from "../api/perfil";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { Stat, StatGrid } from "../components/ui/Stat";
import { PageHeader } from "../components/ui/PageHeader";

const ROL_LABEL = {
  administrador: "Administrador",
  operador_1: "Operador 1",
  operador_2: "Operador 2",
};

export function Perfil() {
  const { usuario } = useAuth();
  const { perfil, informe, loading, error } = usePerfil();
  const [descargando, setDescargando] = useState(false);

  const handleDescargar = async () => {
    setDescargando(true);
    try {
      await descargarReportePropio({ dias: 7, detalle: true });
      toast.success("Reporte generado y descargado.");
    } catch (err) {
      toast.error(err.message || "No se pudo generar el reporte");
    } finally {
      setDescargando(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return <EmptyState title="No se pudo cargar su perfil" description={error} />;
  }

  const esOperador = Boolean(perfil?.operador);
  const est = informe?.estadisticas_ambientales;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={ROL_LABEL[perfil?.usuario?.rol] || perfil?.usuario?.rol}
        title={perfil?.usuario?.nombre || usuario?.nombre || usuario?.username}
        description={
          esOperador
            ? undefined
            : "Como administrador no tiene una ficha de operador asociada. Para gestionar operadores vaya a la sección Operadores."
        }
      >
        <Button onClick={handleDescargar} disabled={descargando}>
          <FileDown size={15} /> {descargando ? "Generando..." : "Descargar mi reporte"}
        </Button>
      </PageHeader>

      {esOperador && (
        <StatGrid className="grid-cols-1 sm:grid-cols-3">
          <Stat label="ID de operador" value={<span className="font-mono">{perfil.operador.id_operador}</span>} />
          <Stat label="Método de acceso" value={<span className="capitalize">{perfil.operador.metodo_acceso}</span>} />
          <Stat
            label="Estado"
            value={perfil.operador.activo ? "Activo" : "Inactivo"}
            tone={perfil.operador.activo ? "ok" : "bad"}
          />
        </StatGrid>
      )}

      <section className="space-y-3">
        <h2 className="label">Últimos 7 días</h2>
        <StatGrid className="grid-cols-2 sm:grid-cols-4">
          <Stat label="Temp. promedio" value={est?.temp_prom != null ? `${est.temp_prom.toFixed(1)} °C` : "—"} />
          <Stat label="Humedad promedio" value={est?.hum_prom != null ? `${est.hum_prom.toFixed(1)} %` : "—"} />
          <Stat label="Alarmas" value={informe?.total_alarmas ?? 0} />
          <Stat label="Aperturas de puerta" value={informe?.actividad_puerta?.veces_abierta ?? 0} />
        </StatGrid>
      </section>
    </div>
  );
}
