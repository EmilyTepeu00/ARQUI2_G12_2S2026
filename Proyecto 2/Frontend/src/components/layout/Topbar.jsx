import clsx from "clsx";
import { LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const ROL_LABEL = { administrador: "Administrador", operador_1: "Operador 1", operador_2: "Operador 2" };

export function Topbar({ estado }) {
  const conectado = Boolean(estado?.serial_conectado);
  const { usuario, logout } = useAuth();
  const nombre = usuario?.nombre || usuario?.username || "";

  return (
    <header className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8 lg:pt-6">
      <div className="ml-auto flex items-center gap-2">
        <span
          className={clsx(
            "flex items-center gap-2 rounded-full border border-line bg-white/[0.04] px-3 py-1.5 text-xs",
            conectado ? "text-ink-2" : "text-bad"
          )}
        >
          <span className={clsx("h-2 w-2 rounded-full", conectado ? "animate-blink bg-ok shadow-[0_0_8px] shadow-ok" : "bg-bad")} />
          {conectado ? `Arduino${estado?.puerto ? ` · ${estado.puerto}` : ""}` : "Arduino desconectado"}
        </span>
        {usuario && (
          <div className="flex items-center gap-2.5 rounded-full border border-line bg-white/[0.04] py-1 pl-1 pr-1 sm:pr-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent-2 to-accent text-xs font-semibold text-white">
              {nombre.slice(0, 1).toUpperCase()}
            </span>
            <div className="hidden leading-tight sm:block">
              <p className="text-xs font-medium text-ink">{nombre}</p>
              <p className="text-[11px] text-muted">{ROL_LABEL[usuario.rol] || usuario.rol}</p>
            </div>
            <button onClick={logout} aria-label="Cerrar sesión" className="rounded-full p-1.5 text-muted hover:text-bad lg:hidden">
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
