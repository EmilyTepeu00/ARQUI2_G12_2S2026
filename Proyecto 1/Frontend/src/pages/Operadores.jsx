import { useState } from "react";
import toast from "react-hot-toast";
import { Users, Plus, DoorOpen, ArrowDownToLine, ArrowUpFromLine } from "lucide-react";
import { useOperadores } from "../hooks/useOperadores";
import { usePuertaEventos } from "../hooks/usePuertaEventos";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { StatCard } from "../components/ui/StatCard";
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
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Operadores"
          subtitle="Personas autorizadas a abrir la incubadora (RFID, huella o llave)"
          icon={<Users size={18} />}
          action={
            <Button onClick={openCreate} className="px-3 py-2 text-xs">
              <Plus size={14} /> Nuevo operador
            </Button>
          }
        />

        <div className="px-5 pb-5">
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : error ? (
            <EmptyState title="Error al cargar operadores" description={error} />
          ) : operadores.length === 0 ? (
            <EmptyState
              icon={<Users size={32} />}
              title="Aún no hay operadores registrados"
              description="Crea el primer operador para poder controlar el acceso a la incubadora"
              action={
                <Button onClick={openCreate} className="mt-2 px-3 py-2 text-xs">
                  <Plus size={14} /> Nuevo operador
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-2 pr-4 font-medium">ID</th>
                    <th className="pb-2 pr-4 font-medium">Nombre</th>
                    <th className="pb-2 pr-4 font-medium">Rol</th>
                    <th className="pb-2 pr-4 font-medium">Acceso</th>
                    <th className="pb-2 pr-4 font-medium">Estado</th>
                    <th className="pb-2 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {operadores.map((op) => (
                    <tr key={op.id_operador} className="border-b border-slate-800/60 text-slate-300">
                      <td className="py-3 pr-4 font-mono text-xs text-slate-400">{op.id_operador}</td>
                      <td className="py-3 pr-4 font-medium text-slate-100">{op.nombre}</td>
                      <td className="py-3 pr-4">{op.rol?.replace("_", " ")}</td>
                      <td className="py-3 pr-4 capitalize">{op.metodo_acceso}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={op.activo ? "success" : "danger"} dot>
                          {op.activo ? "Activo" : "Inactivo"}
                        </Badge>
                      </td>
                      <td className="py-3 text-right">
                        <button onClick={() => openEdit(op)} className="mr-3 text-xs font-medium text-amber-400 hover:underline">Editar</button>
                        <button onClick={() => handleDelete(op)} className="text-xs font-medium text-red-400 hover:underline">Eliminar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-300">
          <DoorOpen size={16} /> Actividad de puerta (últimos 7 días)
        </h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard icon={<DoorOpen size={16} />} label="Veces abierta" value={resumen?.veces_abierta ?? 0} />
          <StatCard icon={<DoorOpen size={16} />} label="Veces cerrada" value={resumen?.veces_cerrada ?? 0} />
          <StatCard icon={<ArrowDownToLine size={16} />} label="Huevos ingresados" value={resumen?.huevos_ingresados ?? 0} accent="emerald" />
          <StatCard icon={<ArrowUpFromLine size={16} />} label="Huevos retirados" value={resumen?.huevos_retirados ?? 0} accent="red" />
        </div>
      </div>

      <Card>
        <CardHeader title="Últimos eventos" subtitle="Aperturas y cierres recientes, incluyendo el operador y el método usado" icon={<DoorOpen size={18} />} />
        <div className="px-5 pb-5">
          {loadingEventos ? (
            <Skeleton className="h-40 w-full" />
          ) : eventos.length === 0 ? (
            <EmptyState title="Sin eventos registrados aún" description="Aquí aparecerán las aperturas y cierres en cuanto ocurran." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-2 pr-4 font-medium">Fecha</th>
                    <th className="pb-2 pr-4 font-medium">Acción</th>
                    <th className="pb-2 pr-4 font-medium">Operador</th>
                    <th className="pb-2 pr-4 font-medium">Método</th>
                    <th className="pb-2 pr-4 font-medium">Huevos</th>
                    <th className="pb-2 font-medium">Autorizado</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map((ev) => (
                    <tr key={ev.id} className="border-b border-slate-800/60 text-slate-300">
                      <td className="py-2.5 pr-4 text-xs text-slate-500">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "—"}</td>
                      <td className="py-2.5 pr-4 capitalize">{ev.accion}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{ev.id_operador}</td>
                      <td className="py-2.5 pr-4 capitalize">{ev.metodo}</td>
                      <td className="py-2.5 pr-4">{ev.huevos_delta > 0 ? `+${ev.huevos_delta}` : ev.huevos_delta || "—"}</td>
                      <td className="py-2.5">
                        <Badge variant={ev.autorizado ? "success" : "warning"} dot>{ev.autorizado ? "Sí" : "No"}</Badge>
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