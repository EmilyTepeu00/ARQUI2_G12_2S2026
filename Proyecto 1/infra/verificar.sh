#!/usr/bin/env bash
# Verifica que la plataforma responda por una URL base.
#
#   ./verificar.sh                                  # local, por el proxy
#   ./verificar.sh https://algo.trycloudflare.com   # a traves del tunel
#
# Solo necesita curl.

BASE="${1:-http://localhost:8080}"
BASE="${BASE%/}"
fallos=0

case "$BASE" in
  https://*) WS_ESQ="wss" ;;
  *)         WS_ESQ="ws"  ;;
esac

echo "Verificando: $BASE"
echo

probar() {   # probar <ruta> <codigo esperado> <descripcion>
  local codigo
  codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$1")
  if [ "$codigo" = "$2" ]; then
    printf '  OK     %-28s %s\n' "$1" "$3"
  else
    printf '  FALLO  %-28s esperaba %s, llego %s\n' "$1" "$2" "$codigo"
    fallos=$((fallos + 1))
  fi
}

echo "== HTTP =="
probar /health                200 "backend vivo"
probar /api/openapi.yaml      200 "especificacion OpenAPI"
probar /api/docs/             200 "Swagger UI"
probar /api/puerta/resumen    200 "consulta publica de puerta"
probar /api/perfil            401 "protegido sin token (debe rechazar)"
probar /grafana/api/health    200 "Grafana"
probar /                      200 "frontend (SPA)"
probar /lotes                 200 "ruta interna de la SPA (recarga directa)"
probar /api/historico/series  200 "serie historica (la consume Grafana)"
probar /api/historico/diario  200 "resumen diario"

echo
echo "== WebSocket de MQTT =="
# --http1.1 es obligatorio: sobre HTTP/2 el upgrade de WebSocket usa otro
# mecanismo (CONNECT extendido) y estas cabeceras dan 502 en el proxy.
respuesta=$(curl -s -i --http1.1 --max-time 10 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Protocol: mqtt" \
  "$BASE/mqtt" 2>/dev/null | head -1)
if printf '%s' "$respuesta" | grep -q "101"; then
  echo "  OK     /mqtt                        101 Switching Protocols"
  echo "         el frontend se conecta a: $WS_ESQ://${BASE#*://}/mqtt"
else
  echo "  FALLO  /mqtt                        no hubo upgrade: ${respuesta:-sin respuesta}"
  fallos=$((fallos + 1))
fi

echo
echo "== Login =="
codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"operador1","password":"operador1"}')
if [ "$codigo" = "200" ]; then
  echo "  OK     /api/auth/login              devuelve token"
else
  echo "  FALLO  /api/auth/login              llego $codigo"
  fallos=$((fallos + 1))
fi

echo
if [ "$fallos" -eq 0 ]; then
  echo "RESULTADO: todo responde correctamente."
else
  echo "RESULTADO: $fallos fallo(s)."
  exit 1
fi
