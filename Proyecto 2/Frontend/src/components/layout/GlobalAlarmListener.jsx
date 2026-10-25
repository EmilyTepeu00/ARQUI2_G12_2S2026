import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { useAlarmStream } from "../../realtime/useAlarmStream";

export function GlobalAlarmListener() {
  const { alarma } = useAlarmStream();
  const lastAlarmRef = useRef(null);

  useEffect(() => {
    if (!alarma) return;

    const firma = alarma.timestamp || JSON.stringify(alarma);
    if (firma === lastAlarmRef.current) return;
    lastAlarmRef.current = firma;

    toast.error(alarma.mensaje || "Alarma crítica en la incubadora", {
      duration: 8000,
      style: { background: "rgba(120,20,30,0.85)", color: "#fff", border: "1px solid rgba(255,107,107,0.5)" },
      iconTheme: { primary: "#fff", secondary: "#b8322a" },
    });
  }, [alarma]);

  return null;
}