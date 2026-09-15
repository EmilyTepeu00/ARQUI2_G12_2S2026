import mqtt from "mqtt";

/**
 * URL del broker por WebSocket.
 *
 * Por defecto se arma desde el origen de la pagina y apunta a /mqtt, que es la
 * ruta que el proxy (Caddy) reenvia al listener WebSocket de Mosquitto. Esto
 * resuelve dos cosas de golpe:
 *
 *   1. En una pagina https:// el esquema pasa solo a wss://. Un ws:// dentro de
 *      https lo bloquea el navegador por contenido mixto.
 *   2. La URL del tunel publico cambia cada vez que se levanta, y como esta se
 *      calcula en tiempo de ejecucion, no hay que recompilar el frontend.
 *
 * VITE_MQTT_WS_URL solo se define para apuntar a un broker en otro host.
 */
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
