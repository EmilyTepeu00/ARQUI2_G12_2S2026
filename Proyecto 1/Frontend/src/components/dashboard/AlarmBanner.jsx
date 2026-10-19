export function AlarmBanner({ lectura }) {
  if (!lectura?.alarma) return null;

  return (
    <div role="alert" className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl border border-bad/40 bg-bad/20 px-5 py-3.5 text-white shadow-[0_0_40px_-10px] shadow-bad backdrop-blur-xl">
      <span className="flex items-center gap-2 text-sm font-semibold text-bad">
        <span className="h-2 w-2 animate-blink rounded-full bg-bad shadow-[0_0_10px] shadow-bad" />
        Alarma activa
      </span>
      <span className="text-sm text-ink-2">
        Temperatura o humedad fuera del rango seguro. Revisa la incubadora y el historial de alarmas.
      </span>
    </div>
  );
}
