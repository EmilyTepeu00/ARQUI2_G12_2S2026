import clsx from "clsx";

export function Card({ children, className, ...props }) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-sm shadow-lg shadow-black/20",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, icon, action }) {
  return (
    <div className="flex items-start justify-between gap-3 p-5 pb-3">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-800/80 text-slate-300">
            {icon}
          </div>
        )}
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}
