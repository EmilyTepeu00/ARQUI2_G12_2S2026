import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { LayoutDashboard, History, BellRing, Boxes, FileDown, UserCircle, Users, LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import logoIcono from "../../assets/logo-icono.png";

const LINKS = [
  { to: "/", label: "Panel", icon: LayoutDashboard, end: true },
  { to: "/historial", label: "Historial", icon: History },
  { to: "/alarmas", label: "Alarmas", icon: BellRing },
  { to: "/lotes", label: "Lotes", icon: Boxes },
  { to: "/reportes", label: "Reportes", icon: FileDown },
  { to: "/perfil", label: "Perfil", icon: UserCircle },
];

const LINKS_ADMIN = [{ to: "/operadores", label: "Operadores", icon: Users }];

/* Vertical en escritorio; en pantallas chicas se vuelve una fila con scroll. */
export function Sidebar() {
  const { esAdministrador, logout } = useAuth();
  const links = esAdministrador ? [...LINKS, ...LINKS_ADMIN] : LINKS;

  return (
    <aside className="flex shrink-0 flex-col border-b border-line bg-black/20 lg:w-56 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-2.5 px-6 pb-2 pt-5 lg:pb-8 lg:pt-7">
        <img src={logoIcono} alt="" className="h-8 w-8 object-contain" />
        <span className="text-lg font-bold tracking-tight">SmartEgg</span>
      </div>

      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-1 lg:flex-col lg:pb-0">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                "group flex shrink-0 items-center gap-3 rounded-full py-1.5 pl-1.5 pr-4 text-sm transition-colors",
                isActive ? "bg-white/[0.06] text-ink" : "text-muted hover:text-ink"
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={clsx(
                    "flex h-8 w-8 items-center justify-center rounded-full transition",
                    isActive
                      ? "bg-gradient-to-b from-[#5b78ff] to-[#3a55e6] text-white shadow-[0_0_18px_rgb(76_107_255/0.7)]"
                      : "bg-white/[0.04] group-hover:bg-white/[0.08]"
                  )}
                >
                  <Icon size={15} />
                </span>
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="hidden px-3 pb-6 lg:block">
        <button onClick={logout} className="flex w-full items-center gap-3 rounded-full py-1.5 pl-1.5 pr-4 text-sm text-muted transition-colors hover:text-bad">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/[0.04]">
            <LogOut size={15} />
          </span>
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
