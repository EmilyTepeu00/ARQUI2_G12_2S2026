import clsx from "clsx";

const SIZE = 132;
const STROKE = 10;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Anillo circular tipo gauge. `min`/`max` definen el rango visible completo,
 * `softMin`/`softMax` marcan el rango "seguro" (usado para colorear).
 */
export function GaugeRing({ value, min, max, softMin, softMax, unit, label, icon, accent = "amber" }) {
  const safeValue = typeof value === "number" ? value : min;
  const clamped = Math.min(Math.max(safeValue, min), max);
  const pct = (clamped - min) / (max - min || 1);
  const dashOffset = CIRCUMFERENCE * (1 - pct);

  const inRange = typeof value === "number" && value >= softMin && value <= softMax;
  const ringColor = value == null ? "stroke-slate-700" : inRange ? RING_COLORS[accent] : "stroke-red-500";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} className="-rotate-90">
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE}
            className="stroke-slate-800"
          />
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            className={clsx("transition-all duration-700 ease-out", ringColor)}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className={clsx("mb-0.5", inRange ? TEXT_COLORS[accent] : "text-red-400")}>{icon}</div>
          <span className="text-2xl font-bold tabular-nums text-slate-50">
            {typeof value === "number" ? value.toFixed(1) : "--"}
            <span className="ml-0.5 text-sm font-medium text-slate-500">{unit}</span>
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-slate-300">{label}</p>
        <p className="text-xs text-slate-500">
          rango seguro {softMin}–{softMax}
          {unit}
        </p>
      </div>
    </div>
  );
}

const RING_COLORS = {
  amber: "stroke-amber-400",
  sky: "stroke-sky-400",
};

const TEXT_COLORS = {
  amber: "text-amber-400",
  sky: "text-sky-400",
};
