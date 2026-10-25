import clsx from "clsx";

const TONES = {
  neutral: "bg-muted",
  ok: "bg-ok shadow-[0_0_10px] shadow-ok",
  warn: "bg-warn shadow-[0_0_10px] shadow-warn",
  bad: "bg-bad shadow-[0_0_10px] shadow-bad",
  cool: "bg-cool shadow-[0_0_10px] shadow-cool",
  accent: "bg-accent-2 shadow-[0_0_10px] shadow-accent",
};

export function StatGrid({ className, children }) {
  return <div className={clsx("grid gap-3", className)}>{children}</div>;
}

export function Stat({ label, value, hint, tone, live = false }) {
  return (
    <div className="glass flex flex-col gap-2 rounded-2xl px-5 py-4">
      <p className="label flex items-center gap-2">
        {tone && <span className={clsx("h-2 w-2 rounded-full", TONES[tone], live && "animate-blink")} />}
        {label}
      </p>
      <p className="truncate text-xl font-semibold tracking-tight text-ink">{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}
