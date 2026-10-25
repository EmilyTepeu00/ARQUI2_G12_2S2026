# AWS: Fase 3

## 1. EC2

Cree Ubuntu 24.04 x86_64, mínimo `t3.small` (2 GB; el instalador agrega 2 GB de swap), recomendado `t3.medium`, con 20 GB de disco. Configure [los puertos](puertos_aws.md) con `bash infra/nube/crear_puertos_aws.sh ID_INSTANCIA`. El repositorio remoto debe contener estos cambios y los Dockerfiles/modelos de `ml/` y `vision/` antes de desplegar.

Desde su PC:

```bash
ssh -i clave.pem ubuntu@IP_PUBLICA
```

En EC2:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/jordonez-usac/AYC2_G12.git
bash AYC2_G12/Proyecto_2/infra/nube/instalar_vm.sh
```

Solo pregunta contraseña MQTT, contraseña Grafana e IP pública. Guarda `.env` privado; al repetir conserva sus valores y actualiza con `git pull --ff-only`. Si ya clonó, omita `git clone`. `REPO_URL` y `REPO_DIR` permiten otra copia. No borra volúmenes. Las cuentas heredadas y JWT reciben claves aleatorias en `.env`.

Abra `http://IP_PUBLICA:3000/grafana/` con el usuario `admin` y la contraseña que eligió. Para revisar:

```bash
cd ~/AYC2_G12/Proyecto_2/infra
sudo docker compose ps
sudo docker compose logs --tail=60 mosquitto backend ml vision
```

Para cambiar claves, edite `.env` y ejecute `sudo docker compose up -d --force-recreate`; Grafana con volumen existente cambia su contraseña desde su interfaz. Mosquitto regenera `passwd` al arrancar. No ejecute `. .env`: contiene valores de Compose que no son sintaxis shell.

## 2. Panel S3

En una computadora con AWS CLI instalado, credenciales configuradas (`aws configure`) y este repo:

```bash
cd AYC2_G12/Proyecto_2
export AWS_REGION=us-east-1 MQTT_USER=smartegg NODE_ID=incubadora-01
read -rsp 'Contraseña MQTT elegida en EC2: ' MQTT_PASS; echo; export MQTT_PASS
bash infra/nube/subir_web_s3.sh mi-bucket-smartegg-unico IP_PUBLICA
```

El bucket debe ser suyo y exclusivo del panel: el script publica todos sus objetos para lectura, sin permitir escritura pública. Puede repetirse sin borrar archivos. Necesita permisos S3 para crear/configurar el bucket y subir objetos. Si la cuenta u organización bloquea políticas públicas, el script falla: el administrador debe permitir hosting público para este bucket; no desactiva bloqueos de toda la cuenta. Abra la URL HTTP impresa (incluye las credenciales codificadas y el nodo). No suba `.env` a S3. El panel usa exactamente `url`, `user`, `pass`, `node` de `web/app.js`.

## 3. PC con Arduino y webcam

```bash
cd AYC2_G12/Proyecto_2/gateway
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export MQTT_HOST=IP_PUBLICA MQTT_PORT=1883 MQTT_USER=smartegg NODE_ID=incubadora-01
read -rsp 'Contraseña MQTT: ' MQTT_PASS; echo; export MQTT_PASS
python bridge.py --serial-port /dev/ttyACM0 --camera 0
```

En Windows use `COM3` y active `.venv\Scripts\activate`. Sin hardware: `python bridge.py --simulate --no-camera`. El puente corre en el PC, nunca dentro de EC2. Consulte [límites del firmware y del puente](../../gateway/README.md). El frontend de Fase 2 permanece, pero use el panel S3 para los controles MQTT de Fase 3.

Para detener EC2 sin borrar datos: `sudo docker compose stop` desde `infra/`. No use `down -v` si desea conservar historial.
