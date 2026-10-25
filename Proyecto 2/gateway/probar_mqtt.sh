#!/usr/bin/env bash
# Broker aislado: no usa ni detiene servicios existentes.
set -euo pipefail
cd "$(dirname "$0")"
python=${PYTHON:-python3}
puerto=${TEST_MQTT_PORT:-28883}
"$python" - "$puerto" <<'PY'
import socket, sys
with socket.socket() as s:
    s.bind(('127.0.0.1', int(sys.argv[1])))
print('Puerto de prueba disponible')
PY
"$python" -c 'import paho.mqtt.client, serial'
tmp=$(mktemp -d)
broker_pid= puente_pid= sub_pid=
limpiar() {
    [[ -z "$sub_pid" ]] || kill "$sub_pid" 2>/dev/null || true
    [[ -z "$sub_pid" ]] || wait "$sub_pid" 2>/dev/null || true
    [[ -z "$puente_pid" ]] || kill "$puente_pid" 2>/dev/null || true
    [[ -z "$puente_pid" ]] || wait "$puente_pid" 2>/dev/null || true
    [[ -z "$broker_pid" ]] || kill "$broker_pid" 2>/dev/null || true
    [[ -z "$broker_pid" ]] || wait "$broker_pid" 2>/dev/null || true
    rm -rf "$tmp"
}
trap limpiar EXIT
mosquitto_passwd -b -c "$tmp/passwd" prueba clave-prueba
cat > "$tmp/mosquitto.conf" <<EOF
listener $puerto 127.0.0.1
allow_anonymous false
password_file $tmp/passwd
EOF
mosquitto -c "$tmp/mosquitto.conf" > "$tmp/broker.log" 2>&1 &
broker_pid=$!
sleep 1
kill -0 "$broker_pid" || { cat "$tmp/broker.log"; exit 1; }
if mosquitto_pub -h 127.0.0.1 -p "$puerto" -t prueba -m no 2>/dev/null; then
    echo 'ERROR: aceptó conexión anónima'; exit 1
fi
"$python" bridge.py --simulate --no-camera --node-id incubadora-01 --mqtt-host 127.0.0.1 --mqtt-port "$puerto" --mqtt-user prueba --mqtt-pass clave-prueba > "$tmp/puente.log" 2>&1 &
puente_pid=$!
sub=(mosquitto_sub -h 127.0.0.1 -p "$puerto" -u prueba -P clave-prueba -W 10)
pub=(mosquitto_pub -h 127.0.0.1 -p "$puerto" -u prueba -P clave-prueba -q 1)
base=smartegg/incubadora-01
"${sub[@]}" -t "$base/sensores/lectura" -C 1 > "$tmp/lectura.json"
"${sub[@]}" -t "$base/actuadores/estado" -C 1 > "$tmp/antes.json"
"${sub[@]}" -t "$base/actuadores/estado" -R -C 1 > "$tmp/despues.json" &
sub_pid=$!
sleep 1
"${pub[@]}" -t "$base/actuadores/cmd" -m '{"actuador":"ventilacion","accion":"on"}'
wait "$sub_pid"
sub_pid=
"$python" - "$tmp" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
lectura, antes, despues = [json.loads((p / n).read_text()) for n in ('lectura.json', 'antes.json', 'despues.json')]
assert 37 <= lectura['temperatura'] <= 38 and 55 <= lectura['humedad'] <= 59
assert antes['ventilacion'] is False
assert despues['ventilacion'] is True
print('OK: sensores/lectura recibido; ventilacion false -> true; autenticación obligatoria')
print(json.dumps(lectura)); print(json.dumps(antes)); print(json.dumps(despues))
PY
kill "$puente_pid"
wait "$puente_pid"
puente_pid=
[[ $("${sub[@]}" -t "$base/status" -C 1) == '{"estado": "offline"}' ]]
echo 'OK: status offline retenido; limpieza automática'
