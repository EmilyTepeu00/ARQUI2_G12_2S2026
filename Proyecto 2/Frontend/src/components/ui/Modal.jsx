import { X } from "lucide-react";

export function Modal({ title, onClose, onSubmit, error, footer, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <form onSubmit={onSubmit} className="relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto glass rounded-3xl !bg-surface/90">
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="rounded-full p-1.5 text-muted hover:bg-white/[0.06] hover:text-ink">
            <X size={18} />
          </button>
        </div>
        <div className="grid grid-cols-1 gap-4 px-6 py-5 sm:grid-cols-2">{children}</div>
        {error && <p className="mx-6 mb-3 rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">{error}</p>}
        <div className="flex items-center justify-end gap-2 border-t border-line px-6 py-4">{footer}</div>
      </form>
    </div>
  );
}

export function Field({ label, required, full, children }) {
  return (
    <label className={`flex flex-col gap-1.5 ${full ? "sm:col-span-2" : ""}`}>
      <span className="label">
        {label} {required && <span className="text-accent">*</span>}
      </span>
      {children}
    </label>
  );
}
