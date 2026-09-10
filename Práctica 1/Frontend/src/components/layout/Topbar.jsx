import { Menu } from "lucide-react";
import { ConnectionPill } from "../ui/ConnectionPill";

export function Topbar({ onMenuClick, estado }) {
  const conectado = Boolean(estado?.serial_conectado);

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-slate-800/80 bg-slate-950/80 px-4 py-3 backdrop-blur-md sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-200 lg:hidden"
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-base font-semibold text-slate-100 sm:text-lg">
            Monitoreo en tiempo real
          </h1>
          <p className="hidden text-xs text-slate-500 sm:block">
            Datos transmitidos por el Arduino vía puerto serial
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <ConnectionPill
          connected={conectado}
          label={conectado ? `Arduino conectado${estado?.puerto ? ` · ${estado.puerto}` : ""}` : "Arduino desconectado"}
        />
      </div>
    </header>
  );
}
