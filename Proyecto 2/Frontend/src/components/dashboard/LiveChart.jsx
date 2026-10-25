import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Card, CardHeader } from "../ui/Card";
import { formatTime } from "../../utils/format";
import { EmptyState } from "../ui/EmptyState";

const TEMP = "#ff9f6b";
const HUM = "#6f8bff";
const AXIS = { fill: "#7c84a3", fontSize: 11 };

export function LiveChart({ history }) {
  const data = history.map((h) => ({
    time: formatTime(h.timestamp),
    Temperatura: h.temperatura,
    Humedad: h.humedad,
  }));

  return (
    <Card>
      <CardHeader
        title="Tendencia"
        subtitle="Últimas lecturas recibidas en esta sesión"
        action={
          <div className="flex gap-4 text-xs text-ink-2">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: TEMP }} /> Temp °C</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: HUM }} /> Hum %</span>
          </div>
        }
      />
      <div className="h-72 p-4">
        {data.length < 2 ? (
          <EmptyState
            title="Esperando datos"
            description="La gráfica aparece en cuanto lleguen al menos dos lecturas del Arduino."
          />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="time" tick={AXIS} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} tickLine={false} minTickGap={32} />
              <YAxis yAxisId="temp" tick={AXIS} axisLine={false} tickLine={false} width={36} tickFormatter={(v) => v.toFixed(0)} domain={["dataMin - 2", "dataMax + 2"]} />
              <YAxis yAxisId="hum" orientation="right" tick={AXIS} axisLine={false} tickLine={false} width={36} tickFormatter={(v) => v.toFixed(0)} domain={["dataMin - 5", "dataMax + 5"]} />
              <Tooltip
                contentStyle={{ background: "rgba(18,25,51,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 14, fontSize: 12, backdropFilter: "blur(12px)" }}
                labelStyle={{ color: "#7c84a3" }}
                cursor={{ stroke: "rgba(255,255,255,0.2)", strokeWidth: 1 }}
              />
              <Line yAxisId="temp" type="monotone" dataKey="Temperatura" stroke={TEMP} strokeWidth={2.25} dot={false} isAnimationActive={false} />
              <Line yAxisId="hum" type="monotone" dataKey="Humedad" stroke={HUM} strokeWidth={2.25} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
