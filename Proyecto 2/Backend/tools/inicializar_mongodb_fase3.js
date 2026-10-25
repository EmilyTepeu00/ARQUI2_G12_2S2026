// Colecciones e índices de SmartEgg. Uso: mongosh <URI> tools/inicializar_mongodb_fase3.js
const dbSmartEgg = db.getSiblingDB("smartegg");

const colecciones = [
  "lecturas",
  "alarmas",
  "aperturas_puerta",
  "operadores",
  "lotes",
  "usuarios",
  "actuadores_estado",
  "ml_anomalias",
  "vision_resultados",
  "sistema_eventos",
  "energia_consumo",
  "mqtt_eventos",
  "estado_sistema",
  "estado_energia"
];

const existentes = new Set(dbSmartEgg.getCollectionNames());
for (const nombre of colecciones) {
  if (!existentes.has(nombre)) {
    dbSmartEgg.createCollection(nombre);
    print(`Creada colección ${nombre}`);
  }
}

// Consultas por tiempo y por incubadora.
for (const nombre of [
  "lecturas",
  "actuadores_estado",
  "ml_anomalias",
  "vision_resultados",
  "sistema_eventos",
  "energia_consumo",
  "mqtt_eventos"
]) {
  dbSmartEgg.getCollection(nombre).createIndex({ timestamp: -1 });
  dbSmartEgg.getCollection(nombre).createIndex({ node_id: 1, timestamp: -1 });
}

// Índices de la base heredada de Fase 2.
dbSmartEgg.alarmas.createIndex({ inicio: -1 });
dbSmartEgg.alarmas.createIndex({ timestamp: -1 });
dbSmartEgg.alarmas.createIndex({ activa: 1 });
dbSmartEgg.aperturas_puerta.createIndex({ timestamp: -1 });
dbSmartEgg.aperturas_puerta.createIndex({ id_operador: 1 });
dbSmartEgg.aperturas_puerta.createIndex({ id_operador: 1, timestamp: -1 });
dbSmartEgg.operadores.createIndex({ id_operador: 1 }, { unique: true });
dbSmartEgg.lotes.createIndex({ fecha_ingreso: -1 });
dbSmartEgg.lotes.createIndex({ estado: 1 });
dbSmartEgg.usuarios.createIndex({ username: 1 }, { unique: true });

// Una fila de estado vigente y otra de energía por nodo.
dbSmartEgg.estado_sistema.createIndex({ node_id: 1 }, { unique: true });
dbSmartEgg.estado_energia.createIndex({ node_id: 1 }, { unique: true });

print(`Inicialización MongoDB finalizada: ${dbSmartEgg.getName()}`);
