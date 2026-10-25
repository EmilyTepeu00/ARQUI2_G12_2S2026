#!/usr/bin/env bash
# Prueba el flujo de bloqueo contra el broker: ciclo -> 3 objetos extraños -> bloqueado -> desbloqueo.
# Requiere el stack arriba y el puente corriendo (gateway/bridge.py, real o --simulate).
# Uso: MQTT_HOST=localhost MQTT_PORT=11883 MQTT_USER=smartegg MQTT_PASS=... bash infra/probar_bloqueo.sh
set -u
A=(-h "${MQTT_HOST:-localhost}" -p "${MQTT_PORT:-1883}" -u "${MQTT_USER:-smartegg}" -P "${MQTT_PASS:?Falta MQTT_PASS}")
B=smartegg/${NODE_ID:-incubadora-01}
pub() { mosquitto_pub "${A[@]}" -q 1 -t "$B/$1" -m "$2"; }
sub() { mosquitto_sub "${A[@]}" -t "$B/$1" -C 1 -W 3; echo; }

pub actuadores/cmd '{"actuador":"calefaccion","accion":"on"}'; sleep 2
echo "== calefaccion on:"; sub actuadores/estado
pub sistema/cmd '{"accion":"iniciar"}'; sleep 2
for _ in 1 2 3; do pub vision/resultado '{"clase":"objeto_extrano","confianza":0.97}'; sleep 1; done
sleep 2; echo "== sistema/estado tras 3 objetos:"; sub sistema/estado
echo "== actuadores tras bloqueo:"; sub actuadores/estado
pub actuadores/cmd '{"actuador":"calefaccion","accion":"on"}'; sleep 2
echo "== comando durante el bloqueo (debe seguir apagado):"; sub actuadores/estado
pub sistema/cmd '{"accion":"desbloquear","autorizado":false}'; sleep 1
echo "== desbloqueo NO autorizado (sigue bloqueado):"; sub sistema/estado
pub sistema/cmd '{"accion":"desbloquear","autorizado":true,"rol":"admin"}'; sleep 2
echo "== desbloqueo autorizado:"; sub sistema/estado
