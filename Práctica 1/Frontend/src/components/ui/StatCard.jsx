import clsx from "clsx";
import { Card } from "./Card";

export function StatCard({ icon, label, value, hint, accent = "slate", pulse = false }) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div
        className={clsx(
          "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl",
          ACCENTS[accent]
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-0.5 truncate text-xl font-bold text-slate-50">
          {value}
          {pulse && (
            <span className="ml-2 inline-block h-2 w-2 rounded-full bg-emerald-400 align-middle animate-pulse" />
          )}
        </p>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
    </Card>
  );
}

const ACCENTS = {
  slate: "bg-slate-800 text-slate-300",
  amber: "bg-amber-500/10 text-amber-400",
  sky: "bg-sky-500/10 text-sky-400",
  emerald: "bg-emerald-500/10 text-emerald-400",
  red: "bg-red-500/10 text-red-400",
  violet: "bg-violet-500/10 text-violet-400",
};
