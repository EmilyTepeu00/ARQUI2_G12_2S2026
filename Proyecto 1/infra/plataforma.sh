#!/usr/bin/env bash
# Maneja la plataforma SmartEgg sin tener que recordar banderas de Docker.
#
#   ./plataforma.sh arriba      levanta todo en local
#   ./plataforma.sh verificar   comprueba que responda
#   ./plataforma.sh publico     abre el tunel de Cloudflare y muestra la URL
#   ./plataforma.sh url         vuelve a mostrar la URL del tunel
#   ./plataforma.sh estado      que esta corriendo
#   ./plataforma.sh abajo       apaga TODO de forma segura
#
# El motivo de este script: el tunel vive en el perfil `publico`, y un
# `docker compose down` sin ese perfil borra la red pero NO borra el
# contenedor del tunel. El contenedor queda apuntando a una red que ya no
# existe y al levantarlo otra vez falla con "network not found".
# Aca siempre se usa el perfil, asi que eso no puede pasar.

set -u
cd "$(dirname "$0")" || exit 1

PERFIL=(--profile publico)

uso() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

case "${1:-}" in

  arriba)
    # --build reconstruye las imagenes si cambio el codigo.
    # -d las deja en segundo plano (detached).
    docker compose up -d --build
    echo

    # `up -d` vuelve apenas los contenedores ARRANCAN, no cuando estan listos.
    # Sin esta espera, un "verificar" inmediato da 502 con todo bien: el proxy
    # ya responde pero gunicorn todavia no. Se espera al healthcheck real.
    echo -n "Esperando a que los servicios queden listos"
    for _ in $(seq 1 60); do
      pendientes=0
      for servicio in backend frontend caddy mongo mosquitto; do
        estado=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-sonda{{end}}' \
                 "smartegg-$servicio" 2>/dev/null || echo "ausente")
        case "$estado" in
          healthy|sin-sonda) ;;
          *) pendientes=$((pendientes + 1)) ;;
        esac
      done
      [ "$pendientes" -eq 0 ] && break
      echo -n "."
      sleep 2
    done
    echo
    echo

    docker compose ps
    ;;

  verificar)
    ./verificar.sh "${2:-}"
    ;;

  publico)
    # Se borra primero cualquier contenedor viejo del tunel, que es lo que
    # arrastra la red muerta. `|| true` para que no falle si no existe.
    docker rm -f smartegg-tunel >/dev/null 2>&1 || true

    docker compose "${PERFIL[@]}" up -d
    echo "Esperando la URL del tunel..."

    # El tunel tarda unos segundos en registrarse contra Cloudflare.
    url=""
    for _ in $(seq 1 20); do
      url=$(docker compose "${PERFIL[@]}" logs cloudflared 2>/dev/null \
            | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
      [ -n "$url" ] && break
      sleep 2
    done

    if [ -z "$url" ]; then
      echo "No aparecio la URL. Revisa: docker compose ${PERFIL[*]} logs cloudflared"
      exit 1
    fi

    echo
    echo "  URL publica: $url"
    echo "  Swagger:     $url/api/docs"
    echo "  Grafana:     $url/grafana/"
    echo "  WebSocket:   ${url/https:/wss:}/mqtt"
    echo
    echo "  Para que Grafana se vea bien desde afuera, en .env:"
    echo "    GRAFANA_ROOT_URL=$url/grafana/"
    echo "  y luego: docker compose up -d grafana"
    echo
    echo "  OJO: la plataforma esta abierta a internet. Apagala al terminar."
    ;;

  url)
    docker compose "${PERFIL[@]}" logs cloudflared 2>/dev/null \
      | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 \
      || echo "El tunel no esta arriba."
    ;;

  estado)
    docker compose "${PERFIL[@]}" ps -a
    ;;

  abajo)
    # Con el perfil: baja el tunel Y borra su contenedor, en el orden correcto.
    # Sin -v, asi que los volumenes (Mongo, Grafana, Mosquitto) se conservan.
    docker compose "${PERFIL[@]}" down
    echo
    echo "Volumenes conservados (el historial NO se borro):"
    docker volume ls --filter name=smartegg --format '  %{{.Name}}' 2>/dev/null \
      | sed 's/%//' || true
    ;;

  *)
    uso
    exit 1
    ;;
esac
