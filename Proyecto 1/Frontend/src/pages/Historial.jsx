import { useEffect, useState } from "react";
import { History, RefreshCw, Thermometer, Droplets } from "lucide-react";
import { sensorsApi } from "../api/sensors";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { formatDateTime } from "../utils/format";
import { THRESHOLDS } from "../utils/constants";

const LIMITS = [50, 100, 250, 500];

export function Historial() {
  const [limit, setLimit] = useState(100);
  const [lecturas, setLecturas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const cargar = () => {
    setLoading(true);
    setError(null);
    sensorsApi
      .historial(limit)
      .then((data) => setLecturas(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message || "No se pudo cargar el historial."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit]);

  const fueraDeRango = (l) =>
    l.temperatura < THRESHOLDS.TEMP_MIN ||
    l.temperatura > THRESHOLDS.TEMP_MAX ||
    l.humedad < THRESHOLDS.HUM_MIN ||
    l.humedad > THRESHOLDS.HUM_MAX;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Historial de lecturas"
          subtitle="Registros almacenados en la base de datos, más recientes primero"
          icon={<History size={18} />}
          action={
            <div className="flex items-center gap-2">
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
              >
                {LIMITS.map((l) => (
                  <option key={l} value={l}>
                    Últimas {l}
                  </option>
                ))}
              </select>
              <Button variant="secondary" className="px-3 py-1.5" onClick={cargar}>
                <RefreshCw size={14} />
              </Button>
            </div>
          }
        />

        <div className="px-2 pb-4 sm:px-4">
          {loading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <EmptyState title="Error al cargar" description={error} />
          ) : lecturas.length === 0 ? (
            <EmptyState
              icon={<History size={32} />}
              title="Sin lecturas registradas"
              description="Todavía no hay datos guardados en la base de datos."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2 font-medium">Fecha</th>
                    <th className="px-3 py-2 font-medium">
                      <span className="inline-flex items-center gap-1">
                        <Thermometer size={13} /> Temp.
                      </span>
                    </th>
                    <th className="px-3 py-2 font-medium">
                      <span className="inline-flex items-center gap-1">
                        <Droplets size={13} /> Humedad
                      </span>
                    </th>
                    <th className="px-3 py-2 font-medium">Sistema</th>
                    <th className="px-3 py-2 font-medium">Espacios</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {lecturas.map((l) => (
                    <tr
                      key={l.id || l.timestamp}
                      className="border-b border-slate-900 text-slate-300 hover:bg-slate-900/60"
                    >
                      <td className="whitespace-nowrap px-3 py-2.5 text-slate-400">
                        {formatDateTime(l.timestamp)}
                      </td>
                      <td className="px-3 py-2.5 font-medium">{l.temperatura?.toFixed?.(1) ?? l.temperatura} °C</td>
                      <td className="px-3 py-2.5 font-medium">{l.humedad?.toFixed?.(1) ?? l.humedad} %</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={l.sistema_encendido ? "success" : "neutral"}>
                          {l.sistema_encendido ? "Encendido" : "Apagado"}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5">{l.espacios_libres}</td>
                      <td className="px-3 py-2.5">
                        {l.alarma || fueraDeRango(l) ? (
                          <Badge variant="danger" dot>
                            Fuera de rango
                          </Badge>
                        ) : (
                          <Badge variant="success" dot>
                            Normal
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
