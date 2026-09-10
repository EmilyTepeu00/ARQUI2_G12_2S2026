import { Pencil, Trash2, Egg, User } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

const ESTADO_VARIANT = {
  incubando: "warning",
  eclosionado: "success",
  descartado: "danger",
};

export function LoteCard({ lote, onEdit, onDelete }) {
  return (
    <Card className="flex flex-col gap-3 p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{lote.codigo}</p>
          <h3 className="text-base font-semibold text-slate-100">{lote.nombre_lote}</h3>
        </div>
        <Badge variant={ESTADO_VARIANT[lote.estado] || "neutral"} dot>
          {lote.estado}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-4 text-sm text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <Egg size={14} className="text-amber-400" /> {lote.cantidad_huevos} huevos
        </span>
        {lote.raza && <span className="text-slate-500">Raza: {lote.raza}</span>}
        {lote.responsable && (
          <span className="inline-flex items-center gap-1.5">
            <User size={14} /> {lote.responsable}
          </span>
        )}
      </div>

      {lote.observaciones && (
        <p className="line-clamp-2 rounded-lg bg-slate-950/50 px-3 py-2 text-xs text-slate-500">
          {lote.observaciones}
        </p>
      )}

      <div className="mt-auto flex items-center gap-2 pt-2">
        <Button variant="secondary" className="flex-1 px-3 py-2 text-xs" onClick={() => onEdit(lote)}>
          <Pencil size={14} /> Editar
        </Button>
        <Button variant="danger" className="px-3 py-2 text-xs" onClick={() => onDelete(lote)}>
          <Trash2 size={14} />
        </Button>
      </div>
    </Card>
  );
}
