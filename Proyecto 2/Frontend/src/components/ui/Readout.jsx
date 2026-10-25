import clsx from "clsx";

export function Readout({ label, value, unit, min, max, softMin, softMax }) {
  const hasValue = typeof value === "number";
  const pos = (v) => `${((Math.min(Math.max(v, min), max) - min) / (max - min)) * 100}%`;
  const inRange = hasValue && value >= softMin && value <= softMax;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm font-medium text-ink-2">{label}</p>
        <p className={clsx("rounded-full px-2.5 py-1 text-xs font-medium", !hasValue ? "bg-white/[0.06] text-muted" : inRange ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad")}>
          {!hasValue ? "sin señal" : inRange ? "en rango" : "fuera de rango"}
        </p>
      </div>
      <p className="text-6xl font-semibold leading-none tracking-tighter text-ink tabular-nums sm:text-7xl">
        {hasValue ? value.toFixed(1) : "--.-"}
        <span className="ml-1 text-2xl text-muted">{unit}</span>
      </p>
      <div>
        <div className="relative h-2 overflow-visible rounded-full bg-white/[0.06]">
          <div className="absolute inset-y-0 rounded-full bg-gradient-to-r from-accent/50 to-accent-2/60" style={{ left: pos(softMin), right: `calc(100% - ${pos(softMax)})` }} />
          {hasValue && (
            <div
              className={clsx("absolute -top-1 h-4 w-1 -translate-x-1/2 rounded-full transition-[left] duration-700", inRange ? "bg-white shadow-[0_0_12px_rgb(138_162_255)]" : "bg-bad")}
              style={{ left: pos(value) }}
            />
          )}
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[11px] text-muted tabular-nums">
          <span>{min}</span>
          <span>
            seguro {softMin}–{softMax}
            {unit}
          </span>
          <span>{max}</span>
        </div>
      </div>
    </div>
  );
}
