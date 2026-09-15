import clsx from "clsx";

const VARIANTS = {
  neutral: "bg-slate-800 text-slate-300 border-slate-700",
  success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  warning: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  danger: "bg-red-500/10 text-red-400 border-red-500/30",
  info: "bg-sky-500/10 text-sky-400 border-sky-500/30",
};

export function Badge({ variant = "neutral", children, dot = false, className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        VARIANTS[variant],
        className
      )}
    >
      {dot && (
        <span
          className={clsx("h-1.5 w-1.5 rounded-full", {
            "bg-slate-400": variant === "neutral",
            "bg-emerald-400": variant === "success",
            "bg-amber-400": variant === "warning",
            "bg-red-400": variant === "danger",
            "bg-sky-400": variant === "info",
          })}
        />
      )}
      {children}
    </span>
  );
}
