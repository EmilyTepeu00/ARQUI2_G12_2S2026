import { useEffect, useState } from "react";
import { BellRing, RefreshCw, Thermometer, Droplets, AlertTriangle } from "lucide-react";
import { sensorsApi } from "../api/sensors";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
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
    <Card>
      <CardHeader
        title="Historial de alarmas"
        subtitle="Condiciones críticas detectadas por el nodo físico"
        icon={<BellRing size={18} />}
        action={
          <Button variant="secondary" className="px-3 py-1.5" onClick={cargar}>
            <RefreshCw size={14} />
          </Button>
        }
      />

      <div className="px-4 pb-5">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : error ? (
          <EmptyState title="Error al cargar" description={error} />
        ) : alarmas.length === 0 ? (
          <EmptyState
            icon={<BellRing size={32} />}
            title="Sin alarmas registradas"
            description="La incubadora se ha mantenido dentro de los rangos seguros."
          />
        ) : (
          <ul className="space-y-3">
            {alarmas.map((a) => (
              <li
                key={a.id || a.timestamp}
                className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3"
              >
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-500/10 text-red-400">
                  <AlertTriangle size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium text-red-300">{a.mensaje || "Alarma detectada"}</p>
                    <span className="text-xs text-slate-500">{formatDateTime(a.timestamp)}</span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-3 text-xs text-slate-500">
                    {a.temperatura != null && (
                      <span className="inline-flex items-center gap-1">
                        <Thermometer size={12} /> {a.temperatura} °C
                      </span>
                    )}
                    {a.humedad != null && (
                      <span className="inline-flex items-center gap-1">
                        <Droplets size={12} /> {a.humedad} %
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
