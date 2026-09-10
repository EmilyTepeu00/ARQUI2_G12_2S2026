import { useState } from "react";
import toast from "react-hot-toast";
import { FileDown, FileText } from "lucide-react";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { descargarReportePdf } from "../api/reports";

export function Reportes() {
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
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader
          title="Generar reporte PDF"
          subtitle="Resumen del estado de la incubadora y las lecturas registradas"
          icon={<FileText size={18} />}
        />
        <div className="space-y-4 px-6 pb-6">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Técnico responsable (opcional)</span>
            <input
              value={tecnico}
              onChange={(e) => setTecnico(e.target.value)}
              placeholder="Nombre del técnico"
              className="input"
            />
          </label>

          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-400">
            El reporte incluye la información del proyecto, el técnico indicado y los datos más
            recientes capturados por los sensores del Arduino.
          </div>

          <Button onClick={handleDownload} disabled={loading} className="w-full">
            <FileDown size={16} />
            {loading ? "Generando reporte..." : "Descargar reporte PDF"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
