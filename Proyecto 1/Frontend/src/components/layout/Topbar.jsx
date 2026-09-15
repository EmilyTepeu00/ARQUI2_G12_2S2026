import { Menu, LogOut, User } from "lucide-react";
import { ConnectionPill } from "../ui/ConnectionPill";
import { useAuth } from "../../context/AuthContext";

const ROL_LABEL = { administrador: "Administrador", operador_1: "Operador 1", operador_2: "Operador 2" };

export function Topbar({ onMenuClick, estado }) {
  const conectado = Boolean(estado?.serial_conectado);
  const { usuario, logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-slate-800/80 bg-slate-950/80 px-4 py-3 backdrop-blur-md sm:px-6">
      <div className="flex items-center gap-3">
        <button onClick={onMenuClick} className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-200 lg:hidden">
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-base font-semibold text-slate-100 sm:text-lg">Monitoreo en tiempo real</h1>
          <p className="hidden text-xs text-slate-500 sm:block">Datos transmitidos por el Arduino vía puerto serial</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <ConnectionPill connected={conectado} label={conectado ? `Arduino conectado${estado?.puerto ? ` · ${estado.puerto}` : ""}` : "Arduino desconectado"} />
        {usuario && (
          <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 py-1 pl-1 pr-2 sm:pr-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-slate-300">
              <User size={14} />
            </span>
            <div className="hidden leading-tight sm:block">
              <p className="text-xs font-medium text-slate-200">{usuario.nombre || usuario.username}</p>
              <p className="text-[11px] text-slate-500">{ROL_LABEL[usuario.rol] || usuario.rol}</p>
            </div>
            <button onClick={logout} title="Cerrar sesión" className="ml-1 rounded-full p-1.5 text-slate-500 hover:bg-slate-800 hover:text-red-400">
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
