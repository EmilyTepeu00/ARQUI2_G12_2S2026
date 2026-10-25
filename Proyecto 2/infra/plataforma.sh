#!/usr/bin/env bash
# Maneja la plataforma SmartEgg (Fase 3) sin tener que recordar banderas de Docker.
#
#   ./plataforma.sh todo              arriba + puente y cámara en vivo en otras terminales
#                                     + abre en el navegador el dashboard, Grafana y la página p5.js
#   ./plataforma.sh camara            ventana con la cámara en vivo + detección de visión (vía MQTT)
#   ./plataforma.sh roi               recalibra el recuadro del disco si la cámara se movió
#   ./plataforma.sh arriba            levanta broker, Mongo, backend, ML, visión, Grafana
#                                     y la página p5.js local (puerto 8765)
#   ./plataforma.sh puente [args]     corre el puente Arduino/cámara -> broker (Ctrl+C para cortarlo)
#                                     sin args: PUENTE_SERIAL y CAMARA de .env (def. /dev/ttyACM0 y 0)
#                                     sin hardware: ./plataforma.sh puente --simulate --no-camera
#                                     contra la nube: MQTT_HOST=IP_PUBLICA ./plataforma.sh puente
#   ./plataforma.sh verificar [IP]    comprueba que todo responda (local, o la EC2 si se da la IP)
#   ./plataforma.sh estado            qué contenedores están corriendo
#   ./plataforma.sh logs [servicio]   últimos logs (ej. backend, vision, ml)
#   ./plataforma.sh nube              como todo, pero contra la EC2 (NUBE_IP de .env), sin Docker local:
#                                     puente, cámara, MQTTX, Compass (túnel SSH a Mongo) y páginas
#   ./plataforma.sh abajo             apaga todo (y cierra lo que abrió nube); el historial se conserva
#
# En la EC2 se corre con sudo: sudo ./plataforma.sh arriba

set -u
cd "$(dirname "$0")" || exit 1

uso() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

# Lee una variable de .env sin ejecutarlo (instalar_vm.sh guarda los valores entre comillas simples).
val() {
  local v
  v=$(grep -m1 "^$1=" .env 2>/dev/null | cut -d= -f2-)
  v=${v#\'}; v=${v%\'}; v=${v#\"}; v=${v%\"}
  printf '%s' "${v:-${2:-}}"
}

# CAMARA puede ser índice (2) o ruta estable (/dev/v4l/by-id/...): el índice cambia entre arranques.
camara() {
  local c; c=$(val CAMARA 0)
  case $c in /*)
    [ -e "$c" ] || { echo "La cámara no está conectada: $c (CAMARA de .env)" >&2; return 1; }
    c=$(readlink -f "$c"); c=${c#/dev/video} ;;
  esac
  printf '%s' "$c"
}

WEB_PID=.web.pid
NUBE=.nube   # existe mientras corre el modo nube; abajo lo usa para cerrar MQTTX y Compass
MARCA=smartegg-nube   # va en el comando de las terminales de nube para que abajo las encuentre

# Página p5.js servida en local; en la nube también va en el bucket S3 (nube/subir_web_s3.sh).
web() {
  if [ ! -f "$WEB_PID" ] || ! kill -0 "$(cat "$WEB_PID")" 2>/dev/null; then
    python3 -m http.server 8765 --directory ../web >/dev/null 2>&1 &
    echo $! > "$WEB_PID"
  fi
}

[ -f .env ] || { echo "Falta infra/.env: cp .env.example .env y defina MQTT_PASS"; exit 1; }

case "${1:-}" in

  arriba)
    servicios=$(docker compose config --services)
    # Sin modelo entrenado la imagen de visión no se puede construir (COPY models/).
    if [ ! -f ../vision/models/modelo.onnx ]; then
      echo "AVISO: falta vision/models/modelo.onnx; se levanta todo menos visión (ver vision/README.md)."
      servicios=$(echo "$servicios" | grep -vx vision)
    fi
    # shellcheck disable=SC2086
    docker compose up -d --build $servicios || exit 1

    # `up -d` vuelve apenas los contenedores ARRANCAN, no cuando están listos.
    echo -n "Esperando a que los servicios queden listos"
    for _ in $(seq 1 60); do
      docker compose ps --format '{{.Health}}' | grep -qE 'starting|unhealthy' || break
      echo -n "."
      sleep 2
    done
    echo
    docker compose ps

    web
    usuario=$(val MQTT_USER smartegg)
    echo
    echo "  Página:  http://localhost:8765/?url=ws://localhost:$(val MQTT_WS_PORT_HOST 9001)&user=$usuario&pass=$(val MQTT_PASS)&node=$(val NODE_ID incubadora-01)"
    echo "  Grafana: http://localhost:$(val GRAFANA_PORT_HOST 3000)/grafana/d/smartegg-fase3"
    echo "  Falta el puente: ./plataforma.sh puente   (o --simulate --no-camera sin hardware)"
    ;;

  puente)
    shift
    # Dos puentes publican fotogramas de cámaras distintas alternados y se pelean el serial.
    if pid=$(pgrep -f 'gateway/bridge\.py'); then
      echo "Ya hay un puente corriendo (PID $pid). Ciérrelo antes (Ctrl+C en su terminal o kill $pid)."
      exit 1
    fi
    if [ $# -eq 0 ]; then
      cam=$(camara) || exit 1
      set -- --serial-port "$(val PUENTE_SERIAL /dev/ttyACM0)" --camera "$cam"
    fi
    # Con el modo nube activo, el puente va a la EC2 aunque se relance a mano.
    if [ -z "${MQTT_HOST:-}" ] && [ -f "$NUBE" ]; then
      export MQTT_HOST="$(val NUBE_IP)" MQTT_PASS="$(val NUBE_MQTT_PASS "$(val MQTT_PASS)")"
    fi
    py=$(realpath ../gateway)/.venv/bin/python
    [ -x "$py" ] || py=python3
    # Por variables de entorno (bridge.py las lee) para que la clave no aparezca en `ps`.
    export MQTT_USER="${MQTT_USER:-$(val MQTT_USER smartegg)}" MQTT_PASS="${MQTT_PASS:-$(val MQTT_PASS)}"
    export NODE_ID="${NODE_ID:-$(val NODE_ID incubadora-01)}"
    if [ -n "${MQTT_HOST:-}" ]; then
      export MQTT_PORT="${MQTT_PORT:-1883}"
    else
      export MQTT_HOST=localhost MQTT_PORT="${MQTT_PORT:-$(val MQTT_PORT_HOST 1883)}"
    fi
    echo "Puente -> $MQTT_HOST:$MQTT_PORT ($NODE_ID)  $*"
    exec "$py" ../gateway/bridge.py "$@"
    ;;

  todo)
    "$0" arriba || exit 1
    if command -v gnome-terminal >/dev/null; then
      gnome-terminal --title="SmartEgg puente" -- bash -c "'$PWD/plataforma.sh' puente; echo; echo 'Puente detenido.'; exec bash"
      gnome-terminal --title="SmartEgg cámara" -- bash -c "'$PWD/plataforma.sh' camara; exec bash"
      echo "  Puente y cámara en vivo abiertos en otras terminales (Ctrl+C / q para cortarlos)."
    else
      echo "  Abra otras terminales y corra: ./plataforma.sh puente  y  ./plataforma.sh camara"
    fi
    # Dashboard React, Grafana y página p5.js de alarmas.
    if command -v xdg-open >/dev/null; then
      for url in \
        "http://localhost:$(val FRONTEND_PORT_HOST 5173)" \
        "http://localhost:$(val GRAFANA_PORT_HOST 3000)/grafana/d/smartegg-fase3" \
        "http://localhost:8765/?url=ws://localhost:$(val MQTT_WS_PORT_HOST 9001)&user=$(val MQTT_USER smartegg)&pass=$(val MQTT_PASS)&node=$(val NODE_ID incubadora-01)"; do
        xdg-open "$url" >/dev/null 2>&1
      done
    fi
    ;;

  nube)
    ip=$(val NUBE_IP)
    [ -n "$ip" ] || { echo "Falta NUBE_IP en .env (IP pública de la EC2)"; exit 1; }
    if ! timeout 5 bash -c "</dev/tcp/$ip/1883" 2>/dev/null; then
      echo "La EC2 $ip no responde en 1883: ¿instancia apagada, IP cambiada o grupo de seguridad sin aplicar?"
      exit 1
    fi
    # gnome-terminal pasa este entorno a las terminales nuevas: así la clave no queda en `ps`.
    export MQTT_HOST=$ip MQTT_PORT=1883 MQTT_USER="$(val MQTT_USER smartegg)"
    export MQTT_PASS="$(val NUBE_MQTT_PASS "$(val MQTT_PASS)")" NODE_ID="$(val NODE_ID incubadora-01)"
    touch "$NUBE"

    gnome-terminal --title="SmartEgg puente (nube)" -- bash -c ": $MARCA; '$PWD/plataforma.sh' puente; echo; echo 'Puente detenido.'; read -rp 'Enter para cerrar'"
    gnome-terminal --title="SmartEgg cámara (nube)" -- bash -c ": $MARCA; '$PWD/plataforma.sh' camara; read -rp 'Enter para cerrar'"

    # Mongo (27017) está cerrado en el grupo de seguridad: se entra por un túnel SSH a 27018 local.
    llave=$(val NUBE_SSH_KEY)
    if ssh ${llave:+-i "$llave"} -o BatchMode=yes -o ConnectTimeout=8 -o ExitOnForwardFailure=yes \
         -fN -L 27018:localhost:27017 "ubuntu@$ip" 2>/dev/null; then
      mongodb-compass mongodb://localhost:27018/smartegg >/dev/null 2>&1 &
    else
      echo "  AVISO: sin SSH a ubuntu@$ip no se abre Mongo (falta NUBE_SSH_KEY o su IP en el puerto 22)."
    fi
    flatpak run com.emqx.MQTTX >/dev/null 2>&1 &
    echo "  MQTTX: host $ip, puerto 1883, usuario $MQTT_USER, topic smartegg/$NODE_ID/#"

    web
    for url in \
      "$(val NUBE_FRONTEND "http://$ip:5000/api/docs/")" \
      "http://$ip:3000/grafana/d/smartegg-fase3" \
      "http://localhost:8765/?url=ws://$ip:9001&user=$MQTT_USER&pass=$MQTT_PASS&node=$NODE_ID"; do
      xdg-open "$url" >/dev/null 2>&1
    done
    echo "  Todo apunta a $ip. Para cerrarlo: ./plataforma.sh abajo"
    ;;

  camara)
    py=$(realpath ../vision)/.venv/bin/python
    [ -x "$py" ] || py=python3
    export MQTT_HOST="${MQTT_HOST:-localhost}" MQTT_PORT="${MQTT_PORT:-$(val MQTT_PORT_HOST 1883)}"
    export MQTT_USER="${MQTT_USER:-$(val MQTT_USER smartegg)}" MQTT_PASS="${MQTT_PASS:-$(val MQTT_PASS)}"
    export NODE_ID="${NODE_ID:-$(val NODE_ID incubadora-01)}"
    cd ../vision && exec "$py" ver_camara.py
    ;;

  roi)
    cam=$(camara) || exit 1  # leer .env antes del cd a ../vision
    if fuser "/dev/video$cam" >/dev/null 2>&1; then
      echo "La cámara está ocupada: cierre el puente (Ctrl+C en su terminal) y vuelva a correr esto."; exit 1
    fi
    echo "Arrastre el recuadro sobre el disco completo (ventana 'modelo' = lo que ve la red) y presione q."
    # --out temporal: si se presiona espacio por error, la foto no entra al dataset.
    (cd ../vision && .venv/bin/python capture_dataset.py --source "$cam" --sesion roi --out "$(mktemp -d)") || exit 1
    python3 -c "
import json; p = '../vision/models/config.json'; c = json.load(open(p))
c['roi'] = [float(v) for v in open('../vision/roi.txt').read().split(',')]
json.dump(c, open(p, 'w'), indent=2); print('ROI nuevo:', c['roi'])"
    docker compose up -d vision >/dev/null && docker compose restart vision >/dev/null && echo "Visión reiniciada con el ROI nuevo. Relance el puente: ./plataforma.sh puente"
    ;;

  verificar)
    ./verificar.sh "${2:-}"
    ;;

  estado)
    docker compose ps -a
    ;;

  logs)
    docker compose logs --tail=60 ${2:+"$2"}
    ;;

  abajo)
    if [ -f "$WEB_PID" ]; then
      kill "$(cat "$WEB_PID")" 2>/dev/null
      rm -f "$WEB_PID"
    fi
    if [ -f "$NUBE" ]; then
      # Cerrar la terminal también corta el puente y la cámara (SIGHUP).
      pkill -f "$MARCA"
      pkill -f '27018:localhost:27017'   # túnel SSH a Mongo
      pkill -f mongodb-compass
      flatpak kill com.emqx.MQTTX 2>/dev/null
      rm -f "$NUBE"
      echo "Modo nube cerrado (la EC2 sigue corriendo)."
    fi
    # Sin -v: los volúmenes (Mongo, Grafana, broker) NO se borran.
    docker compose down
    echo
    echo "Volúmenes conservados (el historial NO se borró):"
    docker volume ls --filter name=smartegg --format '  {{.Name}}'
    ;;

  *)
    uso
    exit 1
    ;;
esac
