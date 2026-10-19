import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

const ESTADO_VARIANT = {
  incubando: "warning",
  eclosionado: "success",
  descartado: "danger",
};

export function LoteCard({ lote, onEdit, onDelete }) {
  return (
    <Card className="flex flex-col">
      <div className="flex flex-1 flex-col gap-4 p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs text-muted">{lote.codigo}</span>
          <Badge variant={ESTADO_VARIANT[lote.estado] || "neutral"}>{lote.estado}</Badge>
        </div>

        <div>
          <h3 className="text-lg font-semibold leading-tight text-ink">{lote.nombre_lote}</h3>
          <p className="mt-1 text-sm text-ink-2">
            {[lote.raza, lote.responsable].filter(Boolean).join(" · ") || "Sin raza ni responsable"}
          </p>
        </div>

        <p className="text-3xl font-semibold tracking-tight text-ink tabular-nums">
          {lote.cantidad_huevos}
          <span className="ml-1.5 text-sm text-muted">huevos</span>
        </p>

        {lote.observaciones && <p className="line-clamp-2 text-xs text-muted">{lote.observaciones}</p>}
      </div>

      <div className="flex border-t border-line text-sm">
        <button onClick={() => onEdit(lote)} className="flex-1 py-2.5 text-ink-2 hover:bg-white/[0.04] hover:text-ink">
          Editar
        </button>
        <button onClick={() => onDelete(lote)} className="flex-1 border-l border-line py-2.5 text-ink-2 hover:bg-bad-soft hover:text-bad">
          Eliminar
        </button>
      </div>
    </Card>
  );
}
