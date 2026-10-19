import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { useSensorStream } from "../hooks/useSensorStream";
import { Readout } from "../components/ui/Readout";
import { Stat, StatGrid } from "../components/ui/Stat";
import { Card, CardHeader } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { AlarmBanner } from "../components/dashboard/AlarmBanner";
import { LiveChart } from "../components/dashboard/LiveChart";
import { THRESHOLDS } from "../utils/constants";
import { formatDateTime, timeAgo } from "../utils/format";
import { IncubadoraViz } from "../viz/IncubadoraViz";

export function Dashboard() {
  const { lectura, history, streamConnected, error } = useSensorStream();
  const prevAlarma = useRef(false);

  useEffect(() => {
    if (lectura?.alarma && !prevAlarma.current) {
      toast.error("¡Alarma activada! Temperatura o humedad fuera de rango.");
    }
    prevAlarma.current = Boolean(lectura?.alarma);
  }, [lectura?.alarma]);

  // Devuelve [texto, tono] según el campo booleano de la lectura.
  const estado = (campo, si, no, tonoSi, tonoNo = "neutral") =>
    lectura ? (lectura[campo] ? [si, tonoSi] : [no, tonoNo]) : ["Sin datos", undefined];

  const [sistema, tSistema] = estado("sistema_encendido", "Encendido", "Apagado", "ok");
  const [alarma, tAlarma] = estado("alarma", "Activa", "Normal", "bad", "ok");
  const [calor, tCalor] = estado("calefaccion", "Encendida", "Apagada", "accent");
  const [vent, tVent] = estado("ventilacion", "Encendida", "Apagada", "cool");
  const [rot, tRot] = estado("rotacion", "Girando", "Detenida", "accent");
  const [puerta, tPuerta] = estado("puerta_abierta", "Abierta", "Cerrada", "warn", "ok");

  return (
    <div className="space-y-6">
      <PageHeader title="Incubadora en vivo" description="Condiciones, actuadores y estado del nodo físico en tiempo real.">
        <p className="flex items-center gap-2 rounded-full border border-line bg-white/[0.04] px-3.5 py-2 text-xs text-ink-2">
          <span className={streamConnected ? "h-2 w-2 animate-blink rounded-full bg-ok shadow-[0_0_8px] shadow-ok" : "h-2 w-2 rounded-full bg-warn"} />
          {streamConnected ? "Stream activo" : "Reconectando"}
          <span className="text-muted">· {lectura ? timeAgo(lectura.timestamp) : "sin lecturas"}</span>
        </p>
      </PageHeader>

      <AlarmBanner lectura={lectura} />

      {error && !streamConnected && (
        <p className="rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">{error}</p>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card accent className="grid grid-cols-1 gap-10 p-6 sm:p-8 lg:col-span-7">
          <Readout label="Temperatura" value={lectura?.temperatura} unit="°C" min={20} max={45} softMin={THRESHOLDS.TEMP_MIN} softMax={THRESHOLDS.TEMP_MAX} />
          <div className="h-px bg-gradient-to-r from-transparent via-line-strong to-transparent" />
          <Readout label="Humedad relativa" value={lectura?.humedad} unit="%" min={0} max={100} softMin={THRESHOLDS.HUM_MIN} softMax={THRESHOLDS.HUM_MAX} />
        </Card>

        <Card className="flex flex-col overflow-hidden lg:col-span-5">
          <CardHeader title="Bandeja" subtitle="Modelo 3D · arrastra para orbitar" />
          <div className="flex-1">
            <IncubadoraViz temperatura={lectura?.temperatura} espaciosLibres={lectura?.espacios_libres ?? 6} rotacionActiva={lectura?.rotacion} />
          </div>
        </Card>
      </div>

      <section className="space-y-3">
        <h2 className="label">Actuadores</h2>
        <StatGrid className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
          <Stat label="Alarma" value={alarma} tone={tAlarma} live={lectura?.alarma} hint="Temp. o humedad fuera de rango" />
          <Stat label="Calefacción" value={calor} tone={tCalor} hint={`Bajo ${THRESHOLDS.TEMP_MIN} °C`} />
          <Stat label="Ventilación" value={vent} tone={tVent} hint={`Sobre ${THRESHOLDS.TEMP_MAX} °C`} />
          <Stat label="Rotación" value={rot} tone={tRot} live={lectura?.rotacion} hint="Volteo periódico" />
          <Stat label="Puerta" value={puerta} tone={tPuerta} hint="Acceso RFID" />
        </StatGrid>
      </section>

      <section className="space-y-3">
        <h2 className="label">Sistema</h2>
        <StatGrid className="grid-cols-1 sm:grid-cols-3">
          <Stat label="Controlador" value={sistema} tone={tSistema} hint="Estado del Arduino" />
          <Stat label="Espacios libres" value={lectura?.espacios_libres ?? "--"} hint="Finales de carrera" />
          <Stat label="Última lectura" value={lectura ? timeAgo(lectura.timestamp) : "Sin datos"} hint={lectura ? formatDateTime(lectura.timestamp) : "Esperando al Arduino"} />
        </StatGrid>
      </section>

      <LiveChart history={history} />
    </div>
  );
}
