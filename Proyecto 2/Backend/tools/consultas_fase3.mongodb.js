// Ejecutar con mongosh. Ajustar nodeId y fechas para la revisión.
db = db.getSiblingDB("smartegg");

const nodeId = "incubadora-01";
const desde = new Date(Date.now() - 24 * 60 * 60 * 1000);
const hasta = new Date();

// 1. Lecturas recientes del nodo.
db.lecturas.find(
  { node_id: nodeId, timestamp: { $gte: desde, $lte: hasta } },
  { _id: 0, node_id: 1, timestamp: 1, temperatura: 1, humedad: 1, alarma: 1 }
).sort({ timestamp: -1 }).limit(100);

// 2. Resumen diario de temperatura y humedad.
db.lecturas.aggregate([
  { $match: { node_id: nodeId, timestamp: { $gte: desde, $lte: hasta } } },
  {
    $group: {
      _id: { $dateTrunc: { date: "$timestamp", unit: "day", timezone: "America/Guatemala" } },
      lecturas: { $sum: 1 },
      temperatura_min: { $min: "$temperatura" },
      temperatura_max: { $max: "$temperatura" },
      temperatura_promedio: { $avg: "$temperatura" },
      humedad_min: { $min: "$humedad" },
      humedad_max: { $max: "$humedad" },
      humedad_promedio: { $avg: "$humedad" }
    }
  },
  { $sort: { _id: 1 } }
]);

// 3. Estados y comandos de actuadores.
db.actuadores_estado.find(
  { node_id: nodeId, timestamp: { $gte: desde, $lte: hasta } }
).sort({ timestamp: -1 }).limit(100);

// 4. Anomalías detectadas por el módulo de ML.
db.ml_anomalias.find(
  { node_id: nodeId, timestamp: { $gte: desde, $lte: hasta } }
).sort({ timestamp: -1 }).limit(100);

// 5. Resultados de visión y eventos de bloqueo/desbloqueo.
db.vision_resultados.find(
  { node_id: nodeId, timestamp: { $gte: desde, $lte: hasta } }
).sort({ timestamp: -1 }).limit(100);

db.sistema_eventos.find(
  {
    node_id: nodeId,
    timestamp: { $gte: desde, $lte: hasta },
    tipo: { $in: ["bloqueo_automatico", "desbloqueo_autorizado", "desbloqueo_rechazado"] }
  }
).sort({ timestamp: -1 });

// 6. Último acumulado histórico y del ciclo (snapshots, no sumar entre documentos).
db.estado_energia.find(
  { node_id: nodeId },
  {
    _id: 0, node_id: 1, timestamp: 1, inicio_ciclo: 1,
    potencia_actual_w: 1, energia_kwh: 1, kwh_por_actuador: 1,
    energia_ciclo_kwh: 1, kwh_ciclo_por_actuador: 1,
    limite_ciclo_kwh: 1, limite_ciclo_superado: 1
  }
).sort({ timestamp: -1 }).limit(1);

// 7. Consumo histórico más reciente de cada incubadora.
db.estado_energia.aggregate([
  { $sort: { timestamp: -1 } },
  {
    $group: {
      _id: "$node_id",
      timestamp: { $first: "$timestamp" },
      energia_historica_kwh: { $first: "$energia_kwh" },
      energia_ciclo_kwh: { $first: "$energia_ciclo_kwh" },
      limite_ciclo_kwh: { $first: "$limite_ciclo_kwh" }
    }
  },
  { $sort: { _id: 1 } }
]);
