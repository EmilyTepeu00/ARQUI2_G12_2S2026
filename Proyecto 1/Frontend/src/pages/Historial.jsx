import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { sensorsApi } from "../api/sensors";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
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
      <PageHeader eyebrow="Base de datos" title="Historial" description="Lecturas almacenadas, de la más reciente a la más antigua.">
        <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} className="input w-auto py-1.5">
          {LIMITS.map((l) => (
            <option key={l} value={l}>
              Últimas {l}
            </option>
          ))}
        </select>
        <Button variant="secondary" className="px-2.5" onClick={cargar} aria-label="Recargar">
          <RefreshCw size={15} />
        </Button>
      </PageHeader>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : error ? (
        <EmptyState title="Error al cargar" description={error} />
      ) : lecturas.length === 0 ? (
        <EmptyState title="Sin lecturas registradas" description="Todavía no hay datos guardados en la base de datos." />
      ) : (
        <Card className="overflow-x-auto px-2">
          <table className="table-base min-w-[640px]">
            <thead>
              <tr>
                <th>Fecha</th>
                <th className="text-right">Temp.</th>
                <th className="text-right">Humedad</th>
                <th>Sistema</th>
                <th className="text-right">Espacios</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {lecturas.map((l) => (
                <tr key={l.id || l.timestamp}>
                  <td className="whitespace-nowrap font-mono text-xs">{formatDateTime(l.timestamp)}</td>
                  <td className="text-right font-mono tabular-nums text-ink">{l.temperatura?.toFixed?.(1) ?? l.temperatura} °C</td>
                  <td className="text-right font-mono tabular-nums text-ink">{l.humedad?.toFixed?.(1) ?? l.humedad} %</td>
                  <td>{l.sistema_encendido ? "Encendido" : "Apagado"}</td>
                  <td className="text-right font-mono tabular-nums">{l.espacios_libres}</td>
                  <td>
                    {l.alarma || fueraDeRango(l) ? (
                      <Badge variant="danger" dot>Fuera de rango</Badge>
                    ) : (
                      <Badge variant="success" dot>Normal</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
