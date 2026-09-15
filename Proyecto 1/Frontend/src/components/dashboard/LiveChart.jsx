import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardHeader } from "../ui/Card";
import { Activity } from "lucide-react";
import { formatTime } from "../../utils/format";
import { EmptyState } from "../ui/EmptyState";

export function LiveChart({ history }) {
  const data = history.map((h) => ({
    time: formatTime(h.timestamp),
    Temperatura: h.temperatura,
    Humedad: h.humedad,
  }));

  return (
    <Card>
      <CardHeader
        title="Tendencia en vivo"
        subtitle="Temperatura y humedad de las últimas lecturas"
        icon={<Activity size={18} />}
      />
      <div className="h-72 px-2 pb-4 sm:px-4">
        {data.length < 2 ? (
          <EmptyState
            title="Esperando datos suficientes"
            description="La gráfica aparecerá en cuanto lleguen al menos dos lecturas del Arduino."
          />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
              <defs>
                <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#fbbf24" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="humGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={{ stroke: "#1e293b" }}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                yAxisId="temp"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={36}
                domain={["dataMin - 2", "dataMax + 2"]}
              />
              <YAxis
                yAxisId="hum"
                orientation="right"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={36}
                domain={["dataMin - 5", "dataMax + 5"]}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: 12,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#94a3b8" }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
              <Area
                yAxisId="temp"
                type="monotone"
                dataKey="Temperatura"
                stroke="#fbbf24"
                strokeWidth={2}
                fill="url(#tempGradient)"
                dot={false}
                isAnimationActive={false}
              />
              <Area
                yAxisId="hum"
                type="monotone"
                dataKey="Humedad"
                stroke="#38bdf8"
                strokeWidth={2}
                fill="url(#humGradient)"
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
