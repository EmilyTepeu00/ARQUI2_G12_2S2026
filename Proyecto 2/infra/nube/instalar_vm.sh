#!/usr/bin/env bash
set -euo pipefail
REPO_URL=${REPO_URL:-https://github.com/jordonez-usac/AYC2_G12.git}
REPO_DIR=${REPO_DIR:-$HOME/AYC2_G12}
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$(dpkg --print-architecture)" "$VERSION_CODENAME" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
# Swap de 2 GB: una VM de 1-2 GB se queda sin memoria al compilar las imágenes.
if ! swapon --show | grep -q /swapfile; then
    sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
    grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR/Proyecto_2/infra"
umask 077
if [[ ! -f .env ]]; then
    read -rsp 'Contraseña MQTT: ' MQTT_PASS; echo
    read -rsp 'Contraseña Grafana: ' GRAFANA_ADMIN_PASSWORD; echo
    read -rp 'IP pública de EC2: ' PUBLIC_IP
    export MQTT_PASS GRAFANA_ADMIN_PASSWORD PUBLIC_IP
    python3 - <<'PY'
import ipaddress
import os
import secrets
from pathlib import Path
ipaddress.IPv4Address(os.environ['PUBLIC_IP'])
cambios = {k: os.environ[k] for k in ('MQTT_PASS', 'GRAFANA_ADMIN_PASSWORD', 'PUBLIC_IP')}
for valor in cambios.values():
    if not valor or any(c in valor for c in "'\n\r"):
        raise SystemExit("Use valores no vacíos, sin comilla simple ni saltos de línea")
cambios['GRAFANA_ROOT_URL'] = f"http://{cambios['PUBLIC_IP']}:8080/grafana/"
for clave in ('JWT_SECRET', 'ADMIN_PASSWORD', 'OP1_PASSWORD', 'OP2_PASSWORD'):
    cambios[clave] = secrets.token_hex(24)
lineas = Path('.env.example').read_text().splitlines()
Path('.env').write_text('\n'.join(f"{k}='{cambios[k]}'" if (k := linea.partition('=')[0]) in cambios else linea for linea in lineas) + '\n')
PY
fi
chmod 600 .env
sudo docker compose config -q
sudo docker compose up -d --build
sudo docker compose ps
python3 - <<'PY'
from pathlib import Path
ip = next(l.split('=', 1)[1].strip("'\"") for l in Path('.env').read_text().splitlines() if l.startswith('PUBLIC_IP='))
print(f'Grafana: http://{ip}:8080/grafana/\nMQTT: {ip}:1883\nWebSocket: ws://{ip}:9001')
PY
