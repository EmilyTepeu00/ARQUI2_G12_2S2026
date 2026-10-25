import mqtt from "mqtt";

// URL del broker por WebSocket.
function urlPorDefecto() {
  if (typeof window === "undefined") return "ws://localhost:9001";
  const esquema = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${esquema}//${window.location.host}/mqtt`;
}

export const MQTT_WS_URL = import.meta.env.VITE_MQTT_WS_URL || urlPorDefecto();
export const MQTT_TOPIC_PREFIX = import.meta.env.VITE_MQTT_TOPIC_PREFIX || "smartegg";
export const MQTT_NODE_ID = import.meta.env.VITE_MQTT_NODE_ID || "incubadora-01";

let client = null;

export function getMqttClient() {
  if (!client) {
    client = mqtt.connect(MQTT_WS_URL, {
      reconnectPeriod: 3000,
      clientId: `smartegg-frontend-${Math.random().toString(16).slice(2, 8)}`,
    });
  }

  return client;
}

export function topic(sufijo) {
  return `${MQTT_TOPIC_PREFIX}/${MQTT_NODE_ID}/${sufijo}`;
}
