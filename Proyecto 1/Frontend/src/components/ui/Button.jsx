import clsx from "clsx";

const VARIANTS = {
  primary: "bg-amber-500 text-slate-950 hover:bg-amber-400 shadow-amber-500/20",
  secondary: "bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700",
  ghost: "bg-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200",
  danger: "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30",
};

export function Button({ variant = "primary", className, children, ...props }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold shadow-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
