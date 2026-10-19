import { useState } from "react";
import toast from "react-hot-toast";
import { Plus } from "lucide-react";
import { useOperadores } from "../hooks/useOperadores";
import { usePuertaEventos } from "../hooks/usePuertaEventos";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { Stat, StatGrid } from "../components/ui/Stat";
import { PageHeader } from "../components/ui/PageHeader";
import { formatDateTime } from "../utils/format";
import { OperadorFormModal } from "../components/operadores/OperadorFormModal";

export function Operadores() {
  const { operadores, loading, error, crear, actualizar, eliminar } = useOperadores();
  const { eventos, resumen, loading: loadingEventos } = usePuertaEventos({ limit: 15 });
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (operador) => {
    setEditing(operador);
    setModalOpen(true);
  };

  const handleSubmit = async (data) => {
    if (editing) {
      await actualizar(editing.id_operador, data);
      toast.success("Operador actualizado correctamente.");
    } else {
      await crear(data);
      toast.success("Operador creado correctamente.");
    }
  };

  const handleDelete = async (operador) => {
    if (!window.confirm(`¿Eliminar al operador "${operador.nombre}"? Esta acción no se puede deshacer`)) return;
    try {
      await eliminar(operador.id_operador);
      toast.success("Operador eliminado.");
    } catch (err) {
      toast.error(err.message || "No se pudo eliminar el operador");
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Administración" title="Operadores" description="Personas autorizadas a abrir la incubadora con RFID, huella o llave.">
        <Button onClick={openCreate}>
          <Plus size={15} /> Nuevo operador
        </Button>
      </PageHeader>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : error ? (
        <EmptyState title="Error al cargar operadores" description={error} />
      ) : operadores.length === 0 ? (
        <EmptyState
          title="Aún no hay operadores"
          description="Crea el primer operador para poder controlar el acceso a la incubadora."
          action={
            <Button onClick={openCreate} className="mt-2">
              <Plus size={15} /> Nuevo operador
            </Button>
          }
        />
      ) : (
        <Card className="overflow-x-auto px-2">
          <table className="table-base min-w-[560px]">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Acceso</th>
                <th>Estado</th>
                <th className="text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {operadores.map((op) => (
                <tr key={op.id_operador}>
                  <td className="font-mono text-xs">{op.id_operador}</td>
                  <td className="font-medium text-ink">{op.nombre}</td>
                  <td>{op.rol?.replace("_", " ")}</td>
                  <td className="capitalize">{op.metodo_acceso}</td>
                  <td>
                    <Badge variant={op.activo ? "success" : "danger"} dot>
                      {op.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  <td className="whitespace-nowrap text-right">
                    <button onClick={() => openEdit(op)} className="mr-4 text-ink underline-offset-4 hover:underline">Editar</button>
                    <button onClick={() => handleDelete(op)} className="text-bad underline-offset-4 hover:underline">Eliminar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <section className="space-y-3">
        <h2 className="label">Actividad de puerta · últimos 7 días</h2>
        <StatGrid className="grid-cols-2 sm:grid-cols-4">
          <Stat label="Veces abierta" value={resumen?.veces_abierta ?? 0} />
          <Stat label="Veces cerrada" value={resumen?.veces_cerrada ?? 0} />
          <Stat label="Huevos ingresados" value={resumen?.huevos_ingresados ?? 0} tone="ok" />
          <Stat label="Huevos retirados" value={resumen?.huevos_retirados ?? 0} tone="bad" />
        </StatGrid>
      </section>

      <Card>
        <CardHeader title="Últimos eventos" subtitle="Aperturas y cierres recientes con operador y método" />
        <div className="px-2 pb-2">
          {loadingEventos ? (
            <Skeleton className="m-3 h-40" />
          ) : eventos.length === 0 ? (
            <p className="px-3 py-8 text-sm text-muted">Aquí aparecerán las aperturas y cierres en cuanto ocurran.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="table-base min-w-[560px]">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Acción</th>
                    <th>Operador</th>
                    <th>Método</th>
                    <th className="text-right">Huevos</th>
                    <th>Autorizado</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map((ev) => (
                    <tr key={ev.id}>
                      <td className="whitespace-nowrap font-mono text-xs">{ev.timestamp ? formatDateTime(ev.timestamp) : "—"}</td>
                      <td className="capitalize">{ev.accion}</td>
                      <td className="font-mono text-xs">{ev.id_operador}</td>
                      <td className="capitalize">{ev.metodo}</td>
                      <td className="text-right font-mono tabular-nums">{ev.huevos_delta > 0 ? `+${ev.huevos_delta}` : ev.huevos_delta || "—"}</td>
                      <td>
                        <Badge variant={ev.autorizado ? "success" : "warning"}>{ev.autorizado ? "Sí" : "No"}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      <OperadorFormModal open={modalOpen} onClose={() => setModalOpen(false)} onSubmit={handleSubmit} initialData={editing} />
    </div>
  );
}
