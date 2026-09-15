import { useState } from "react";
import toast from "react-hot-toast";
import { UserCircle, FileDown, DoorOpen, Thermometer, Droplets, BellRing } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePerfil } from "../hooks/usePerfil";
import { descargarReportePropio } from "../api/perfil";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { StatCard } from "../components/ui/StatCard";

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
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <EmptyState title="No se pudo cargar su perfil" description={error} />;
  }

  const esOperador = Boolean(perfil?.operador);
  const est = informe?.estadisticas_ambientales;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title={perfil?.usuario?.nombre || usuario?.nombre || usuario?.username}
          subtitle={ROL_LABEL[perfil?.usuario?.rol] || perfil?.usuario?.rol}
          icon={<UserCircle size={20} />}
          action={
            <Button onClick={handleDescargar} disabled={descargando} className="px-3 py-2 text-xs">
              <FileDown size={14} /> {descargando ? "Generando..." : "Descargar mi reporte"}
            </Button>
          }
        />

        {!esOperador && (
          <div className="mx-5 mb-5 rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-400">
            Como administrador no tiene una ficha de operador asociada. Aquí ve su propio reporte de la plataforma para gestionar a los operadores ve a la sección{" "}
            <span className="font-medium text-slate-200">Operadores</span>.
          </div>
        )}

        {esOperador && (
          <div className="grid grid-cols-1 gap-3 px-5 pb-5 text-sm sm:grid-cols-3">
            <InfoRow label="ID de operador" value={perfil.operador.id_operador} />
            <InfoRow label="Método de acceso" value={perfil.operador.metodo_acceso} />
            <InfoRow
              label="Estado"
              value={
                <Badge variant={perfil.operador.activo ? "success" : "danger"} dot>
                  {perfil.operador.activo ? "Activo" : "Inactivo"}
                </Badge>
              }
            />
          </div>
        )}
      </Card>

      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-300">Últimos 7 días</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            icon={<Thermometer size={16} />}
            label="Temp. promedio"
            value={est?.temp_prom != null ? `${est.temp_prom.toFixed(1)}°C` : "—"}
          />
          <StatCard
            icon={<Droplets size={16} />}
            label="Humedad promedio"
            value={est?.hum_prom != null ? `${est.hum_prom.toFixed(1)}%` : "—"}
          />
          <StatCard icon={<BellRing size={16} />} label="Alarmas" value={informe?.total_alarmas ?? 0} />
          <StatCard
            icon={<DoorOpen size={16} />}
            label="Veces abrió la puerta"
            value={informe?.actividad_puerta?.veces_abierta ?? 0}
          />
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2.5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-200">{value}</p>
    </div>
  );
}