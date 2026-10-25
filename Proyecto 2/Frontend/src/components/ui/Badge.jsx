import clsx from "clsx";

const VARIANTS = {
  neutral: "bg-white/[0.06] text-ink-2",
  success: "bg-ok-soft text-ok",
  warning: "bg-warn-soft text-warn",
  danger: "bg-bad-soft text-bad",
  info: "bg-cool-soft text-cool",
};

export function Badge({ variant = "neutral", children, dot = false, className }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium capitalize", VARIANTS[variant], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
