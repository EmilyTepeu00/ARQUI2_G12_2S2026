export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-800 px-6 py-16 text-center">
      {icon && <div className="text-slate-600">{icon}</div>}
      <div>
        <p className="text-sm font-semibold text-slate-300">{title}</p>
        {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
