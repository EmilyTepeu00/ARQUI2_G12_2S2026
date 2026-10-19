import clsx from "clsx";

export function Card({ children, className, accent = false, ...props }) {
  return (
    <div className={clsx("rounded-3xl", accent ? "glass-accent" : "glass", className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 px-6 pb-2 pt-5">
      <div>
        <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
