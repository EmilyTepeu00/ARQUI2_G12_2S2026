import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { LayoutDashboard, History, BellRing, Boxes, FileDown, Egg } from "lucide-react";

const LINKS = [
  { to: "/", label: "Panel en vivo", icon: LayoutDashboard, end: true },
  { to: "/historial", label: "Historial", icon: History },
  { to: "/alarmas", label: "Alarmas", icon: BellRing },
  { to: "/lotes", label: "Lotes", icon: Boxes },
  { to: "/reportes", label: "Reportes", icon: FileDown },
];

export function Sidebar({ open, onClose }) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-800/80 bg-slate-950/95 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-3 border-b border-slate-800/80 px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-lg shadow-lg shadow-amber-500/20">
            <Egg size={20} className="text-slate-950" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight text-slate-50">SmartEgg</p>
            <p className="text-xs text-slate-500">Incubadora inteligente</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-amber-500/10 text-amber-400"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800/80 px-5 py-4">
          <p className="text-xs text-slate-600">Proyecto SmartEgg &middot; AYC2 G12</p>
        </div>
      </aside>
    </>
  );
}
