import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Plus, Search } from "lucide-react";
import { useLotes } from "../hooks/useLotes";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { LoteCard } from "../components/lotes/LoteCard";
import { LoteFormModal } from "../components/lotes/LoteFormModal";

export function Lotes() {
  const { lotes, loading, error, crear, actualizar, eliminar } = useLotes();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return lotes;
    return lotes.filter(
      (l) =>
        l.codigo?.toLowerCase().includes(q) ||
        l.nombre_lote?.toLowerCase().includes(q) ||
        l.responsable?.toLowerCase().includes(q)
    );
  }, [lotes, search]);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (lote) => {
    setEditing(lote);
    setModalOpen(true);
  };

  const handleSubmit = async (data) => {
    if (editing) {
      await actualizar(editing.id, data);
      toast.success("Lote actualizado correctamente.");
    } else {
      await crear(data);
      toast.success("Lote creado correctamente.");
    }
  };

  const handleDelete = async (lote) => {
    if (!window.confirm(`¿Eliminar el lote "${lote.nombre_lote}"? Esta acción no se puede deshacer.`)) return;
    try {
      await eliminar(lote.id);
      toast.success("Lote eliminado.");
    } catch (err) {
      toast.error(err.message || "No se pudo eliminar el lote.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Inventario" title="Lotes" description="Lotes de huevos registrados en el sistema.">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar código, nombre o responsable" className="input w-72 max-w-full py-1.5 pl-9" />
        </div>
        <Button onClick={openCreate}>
          <Plus size={15} /> Nuevo lote
        </Button>
      </PageHeader>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : error ? (
        <EmptyState title="Error al cargar lotes" description={error} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={lotes.length === 0 ? "Aún no hay lotes registrados" : "Sin resultados"}
          description={
            lotes.length === 0
              ? "Crea tu primer lote para empezar a llevar el control de la incubación."
              : "Prueba con otro término de búsqueda."
          }
          action={
            lotes.length === 0 && (
              <Button onClick={openCreate} className="mt-2">
                <Plus size={15} /> Nuevo lote
              </Button>
            )
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((lote) => (
            <LoteCard key={lote.id} lote={lote} onEdit={openEdit} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <LoteFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        initialData={editing}
      />
    </div>
  );
}
