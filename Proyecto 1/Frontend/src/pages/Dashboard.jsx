import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { Thermometer, Droplets, Power, PackageOpen, Clock } from "lucide-react";
import { useSensorStream } from "../hooks/useSensorStream";
import { GaugeRing } from "../components/ui/GaugeRing";
import { StatCard } from "../components/ui/StatCard";
import { Card, CardHeader } from "../components/ui/Card";
import { AlarmBanner } from "../components/dashboard/AlarmBanner";
import { LiveChart } from "../components/dashboard/LiveChart";
import { THRESHOLDS } from "../utils/constants";
import { formatDateTime, timeAgo } from "../utils/format";
import { IncubadoraViz} from "../viz/IncubadoraViz";

export function Dashboard() {
  const { lectura, history, streamConnected, error } = useSensorStream();
  const prevAlarma = useRef(false);

  useEffect(() => {
    if (lectura?.alarma && !prevAlarma.current) {
      toast.error("¡Alarma activada! Temperatura o humedad fuera de rango.", {
        icon: "🚨",
      });
    }
    prevAlarma.current = Boolean(lectura?.alarma);
  }, [lectura?.alarma]);

  return (
    <div className="space-y-6">
      <AlarmBanner lectura={lectura} />

      {error && !streamConnected && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Power size={20} />}
          label="Sistema"
          value={lectura ? (lectura.sistema_encendido ? "Encendido" : "Apagado") : "Sin datos"}
          accent={lectura?.sistema_encendido ? "emerald" : "slate"}
          hint="Estado del controlador de la incubadora"
          pulse={streamConnected}
        />
        <StatCard
          icon={<PackageOpen size={20} />}
          label="Espacios libres"
          value={lectura?.espacios_libres ?? "--"}
          accent="violet"
          hint="Disponibilidad detectada por finales de carrera"
        />
        <StatCard
          icon={<Clock size={20} />}
          label="Última lectura"
          value={lectura ? timeAgo(lectura.timestamp) : "Sin datos"}
          accent="sky"
          hint={lectura ? formatDateTime(lectura.timestamp) : "Esperando al Arduino"}
        />
        <StatCard
          icon={<Thermometer size={20} />}
          label="Estado del stream"
          value={streamConnected ? "En vivo" : "Reconectando"}
          accent={streamConnected ? "emerald" : "amber"}
          hint="Server-Sent Events desde el backend"
        />
      </div>

      <Card>
        <CardHeader
          title="Condiciones actuales"
          subtitle="Lectura más reciente enviada por los sensores DHT del Arduino"
          icon={<Thermometer size={18} />}
        />
        <div className="flex flex-col items-center justify-around gap-8 px-6 pb-8 pt-2 sm:flex-row">
          <GaugeRing
            value={lectura?.temperatura}
            min={20}
            max={45}
            softMin={THRESHOLDS.TEMP_MIN}
            softMax={THRESHOLDS.TEMP_MAX}
            unit="°C"
            label="Temperatura"
            icon={<Thermometer size={18} />}
            accent="amber"
          />
          <GaugeRing
            value={lectura?.humedad}
            min={0}
            max={100}
            softMin={THRESHOLDS.HUM_MIN}
            softMax={THRESHOLDS.HUM_MAX}
            unit="%"
            label="Humedad"
            icon={<Droplets size={18} />}
            accent="sky"
          />
        </div>
      </Card>

      <IncubadoraViz temperatura={lectura?.temperatura} espaciosLibres={lectura?.espacios_libres ?? 6} rotacionActiva={lectura?.rotacion} />

      <LiveChart history={history} />
    </div>
  );
}
