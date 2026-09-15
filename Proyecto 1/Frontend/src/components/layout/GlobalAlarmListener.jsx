import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { useAlarmStream } from "../../realtime/useAlarmStream";

/**
 * Escucha las alarmas críticas que llegan por MQTT (vía el broker) y las muestra como notificación en cualquier pantalla de la app
 *
 * La conexión MQTT y la suscripción a los topics están en en src/realtime/useAlarmStream.js, este componente solo consume ese hook
 *
 * No dibuja nada visible por sí mismo (return null); solo escucha en segundo plano y dispara el toast cuando llega una alarma nueva
 */

export function GlobalAlarmListener() {
  const { alarma } = useAlarmStream();
  const lastAlarmRef = useRef(null);

  useEffect(() => {
    if (!alarma) return;

    // El broker puede reenviar el mismo mensaje "retained" al reconectar, sin mostrar el mismo toast dos veces seguidas
    const firma = alarma.timestamp || JSON.stringify(alarma);
    if (firma === lastAlarmRef.current) return;
    lastAlarmRef.current = firma;

    toast.error(alarma.mensaje || "Alarma crítica en la incubadora", {
      icon: "🚨",
      duration: 8000,
      style: {
        background: "#450a0a",
        color: "#fecaca",
        border: "1px solid rgba(248,113,113,0.4)",
      },
    });
  }, [alarma]);

  return null;
}