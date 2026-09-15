import { useEffect, useState } from "react";
import { getMqttClient, topic } from "./mqttClient";

const ALARM_TOPIC = topic("alarmas/critica");
const STATUS_TOPIC = topic("status");

export function useAlarmStream(){
    const [alarma, setAlarma] = useState(null);
    const [nodeStatus, setNodeStatus] = useState(null);
    const [mqttConnected, setMqttConnected] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const client = getMqttClient();

        const onConnect = () => {
            if (cancelled) return;
            setMqttConnected(true);
            client.subscribe([ALARM_TOPIC, STATUS_TOPIC], {qos: 1});
        };
        const onReconnect = () => !cancelled && setMqttConnected(false);
        const onClose = () => !cancelled && setMqttConnected(false);
        const onMessage = (topicRecibido, payload) => {
            if (cancelled) return;
            try{
                const data = JSON.parse(payload.toString());
                if (topicRecibido.endsWith("/alarmas/critica")){
                    setAlarma(data);
                }
                else if (topicRecibido.endsWith("status")) {
                    setNodeStatus(data);
                }
            }
            catch {
                //payload inválido, se ignora
            }
        };

        client.on("connect", onConnect);
        client.on("reconnect", onReconnect);
        client.on("close", onClose);
        client.on("message", onMessage);

        return () => {
            cancelled = true;
            client.unsubscribe([ALARM_TOPIC, STATUS_TOPIC]);
            client.off("connect", onConnect);
            client.off("reconnect", onReconnect);
            client.off("close", onClose);
            client.off("message", onMessage);
        }
    }, []);

    return {alarma, nodeStatus, mqttConnected};
}