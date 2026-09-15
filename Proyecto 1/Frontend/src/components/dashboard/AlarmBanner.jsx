import { AlertTriangle } from "lucide-react";

export function AlarmBanner({ lectura }) {
  if (!lectura?.alarma) return null;

  return (
    <div className="animate-fade-in-up flex items-center gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 px-5 py-4">
      <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
        <span className="animate-pulse-ring absolute h-10 w-10 rounded-full bg-red-500/40" />
        <span className="relative flex h-10 w-10 items-center justify-center rounded-full bg-red-500/20 text-red-400">
          <AlertTriangle size={20} />
        </span>
      </div>
      <div>
        <p className="text-sm font-semibold text-red-300">Alarma activa en la incubadora</p>
        <p className="text-xs text-red-400/80">
          Temperatura o humedad fuera del rango seguro. Revisa el panel y el historial de alarmas.
        </p>
      </div>
    </div>
  );
}
