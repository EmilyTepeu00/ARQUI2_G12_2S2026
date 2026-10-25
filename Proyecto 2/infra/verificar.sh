#!/usr/bin/env bash
# Verifica la plataforma de la Fase 3.
#   ./verificar.sh              local (contenedores + puertos de infra/.env)
#   ./verificar.sh IP_PUBLICA   la EC2 desde afuera (puertos del grupo de seguridad: 1883, 9001, 8080)

cd "$(dirname "$0")" || exit 1

val() {
  local v
  v=$(grep -m1 "^$1=" .env 2>/dev/null | cut -d= -f2-)
  v=${v#\'}; v=${v%\'}; v=${v#\"}; v=${v%\"}
  printf '%s' "${v:-${2:-}}"
}

HOST="${1:-localhost}"
USUARIO=$(val MQTT_USER smartegg)
CLAVE="${MQTT_PASS:-$(val MQTT_PASS)}"
NODO=$(val NODE_ID incubadora-01)
if [ "$HOST" = localhost ]; then
  MQTT=$(val MQTT_PORT_HOST 1883); WS=$(val MQTT_WS_PORT_HOST 9001)
  GRAFANA="http://localhost:$(val GRAFANA_PORT_HOST 3000)/grafana/api/health"
else
  MQTT=1883; WS=9001; GRAFANA="http://$HOST:8080/grafana/api/health"
fi
fallos=0

ok()    { printf '  OK     %-30s %s\n' "$1" "$2"; }
fallo() { printf '  FALLO  %-30s %s\n' "$1" "$2"; fallos=$((fallos + 1)); }
aviso() { printf '  AVISO  %-30s %s\n' "$1" "$2"; }

if ! command -v mosquitto_sub >/dev/null; then
  echo "Falta mosquitto_sub: sudo apt install mosquitto-clients"
  exit 1
fi
sub() { mosquitto_sub -h "$HOST" -p "$MQTT" -u "$USUARIO" -P "$2" -t "$1" -C 1 -W 4 2>/dev/null; }

echo "Verificando: $HOST (MQTT $MQTT, WebSocket $WS)"

if [ "$HOST" = localhost ]; then
  echo
  echo "== Contenedores =="
  corriendo=$(docker compose ps --status running --services 2>/dev/null)
  for s in mosquitto mongo backend ml vision grafana; do
    if echo "$corriendo" | grep -qx "$s"; then ok "$s" "corriendo"; else fallo "$s" "no está corriendo"; fi
  done
fi

echo
echo "== Broker MQTT =="
if sub '$SYS/broker/version' "$CLAVE" >/dev/null; then ok "login $USUARIO" "acepta usuario y clave"
else fallo "login $USUARIO" "no conecta en $HOST:$MQTT"; fi
if sub '$SYS/broker/version' "clave-incorrecta" >/dev/null; then fallo "clave incorrecta" "el broker la acepta"
else ok "clave incorrecta" "rechazada"; fi

codigo=$(curl -s -i --http1.1 --max-time 10 -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Protocol: mqtt" "http://$HOST:$WS/" 2>/dev/null | head -1)
if printf '%s' "$codigo" | grep -q 101; then ok "WebSocket :$WS" "la página p5.js puede conectarse"
else fallo "WebSocket :$WS" "sin upgrade: ${codigo:-sin respuesta}"; fi

echo
echo "== Servicios por MQTT =="
estado=$(sub "smartegg/$NODO/sistema/estado" "$CLAVE")
if [ -n "$estado" ]; then ok "sistema/estado" "$(printf '%s' "$estado" | grep -oE '"estado": *"[a-z]+"')"
else fallo "sistema/estado" "el backend no publicó el estado retenido"; fi
if printf '%s' "$(sub "smartegg/$NODO/status" "$CLAVE")" | grep -q online; then ok "puente ($NODO)" "en línea"
else aviso "puente ($NODO)" "fuera de línea: ./plataforma.sh puente"; fi

echo
echo "== Grafana =="
codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$GRAFANA")
if [ "$codigo" = 200 ]; then ok "/grafana/api/health" "responde"; else fallo "/grafana/api/health" "llegó $codigo"; fi

echo
if [ "$fallos" -eq 0 ]; then
  echo "RESULTADO: todo responde correctamente."
else
  echo "RESULTADO: $fallos fallo(s)."
  exit 1
fi
