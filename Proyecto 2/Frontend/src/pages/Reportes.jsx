import { useState } from "react";
import toast from "react-hot-toast";
import { FileDown } from "lucide-react";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { PageHeader } from "../components/ui/PageHeader";
import { useAuth } from "../context/AuthContext";
import { useOperadores } from "../hooks/useOperadores";
import { descargarReportePdf, descargarReportePorOperador } from "../api/reports";

export function Reportes() {
  const { usuario, esAdministrador } = useAuth();
  const [tecnico, setTecnico] = useState("");
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      await descargarReportePdf(tecnico.trim() || undefined);
      toast.success("Reporte generado y descargado.");
    } catch (err) {
      toast.error(err.message || "No se pudo generar el reporte.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Exportar" title="Reportes" description="Documentos PDF generados con los datos más recientes de la incubadora." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Reporte general" subtitle="Información del proyecto, técnico responsable y últimas lecturas de los sensores" />
          <div className="space-y-4 p-5">
            <label className="flex flex-col gap-1.5">
              <span className="label">Técnico responsable (opcional)</span>
              <input value={tecnico} onChange={(e) => setTecnico(e.target.value)} placeholder="Nombre del técnico" className="input" />
            </label>
            <Button onClick={handleDownload} disabled={loading} className="w-full">
              <FileDown size={15} />
              {loading ? "Generando reporte..." : "Descargar PDF"}
            </Button>
          </div>
        </Card>

        <ReportePorOperador usuario={usuario} esAdministrador={esAdministrador} />
      </div>
    </div>
  );
}

function ReportePorOperador({ usuario, esAdministrador }) {
  const { operadores, loading: loadingOperadores } = useOperadores();
  const [idOperador, setIdOperador] = useState(esAdministrador ? "" : usuario?.id_operador || "");
  const [loading, setLoading] = useState(false);

  if (!esAdministrador) return null;

  const handleDownload = async () => {
    if (!idOperador) {
      toast.error("Selecciona un operador primero.");
      return;
    }
    setLoading(true);
    try {
      await descargarReportePorOperador(idOperador);
      toast.success("Reporte del operador generado y descargado.");
    } catch (err) {
      toast.error(err.message || "No se pudo generar el reporte del operador");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader
        title="Reporte por operador"
        subtitle="Reporte individual de cualquier operador registrado"
      />
      <div className="space-y-4 p-5">
        <label className="flex flex-col gap-1.5">
          <span className="label">Operador</span>
          <select value={idOperador} onChange={(e) => setIdOperador(e.target.value)} className="input" disabled={loadingOperadores}>
            <option value="">Selecciona un operador...</option>
            {operadores.map((op) => (
              <option key={op.id_operador} value={op.id_operador}>{op.id_operador} — {op.nombre}</option>
            ))}
          </select>
        </label>

        <Button onClick={handleDownload} disabled={loading || !idOperador} className="w-full">
          <FileDown size={15} />
          {loading ? "Generando reporte..." : "Descargar PDF del operador"}
        </Button>
      </div>
    </Card>
  );
}