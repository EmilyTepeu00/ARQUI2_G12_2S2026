import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { sensorsApi } from "../api/sensors";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { formatDateTime } from "../utils/format";

export function Alarmas() {
  const [alarmas, setAlarmas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const cargar = () => {
    setLoading(true);
    setError(null);
    sensorsApi
      .alarmas(50)
      .then((data) => setAlarmas(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message || "No se pudieron cargar las alarmas."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    cargar();
    const id = setInterval(cargar, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Registro" title="Alarmas" description="Condiciones críticas detectadas por el nodo físico. Se actualiza cada 15 s.">
        <Button variant="secondary" className="px-2.5" onClick={cargar} aria-label="Recargar">
          <RefreshCw size={15} />
        </Button>
      </PageHeader>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : error ? (
        <EmptyState title="Error al cargar" description={error} />
      ) : alarmas.length === 0 ? (
        <EmptyState title="Sin alarmas" description="La incubadora se ha mantenido dentro de los rangos seguros." />
      ) : (
        <Card>
          <ol className="divide-y divide-line">
            {alarmas.map((a) => (
              <li key={a.id || a.timestamp} className="grid grid-cols-1 gap-1 border-l-2 border-bad px-5 py-3.5 sm:grid-cols-[11rem_1fr_auto] sm:items-baseline sm:gap-6">
                <span className="font-mono text-xs text-muted">{formatDateTime(a.timestamp)}</span>
                <span className="text-sm text-ink">{a.mensaje || "Alarma detectada"}</span>
                <span className="flex gap-4 font-mono text-xs tabular-nums text-ink-2">
                  {a.temperatura != null && <span>{a.temperatura} °C</span>}
                  {a.humedad != null && <span>{a.humedad} %</span>}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}
