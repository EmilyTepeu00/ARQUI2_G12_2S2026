# Puente del PC

Desde `Proyecto_2/gateway` (Python 3.10+):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export MQTT_HOST=127.0.0.1 MQTT_PORT=1883 MQTT_USER=smartegg NODE_ID=incubadora-01
read -rsp 'Contraseña MQTT: ' MQTT_PASS; echo; export MQTT_PASS
python bridge.py --serial-port /dev/ttyACM0 --camera 0
# Sin hardware:
python bridge.py --simulate --no-camera
```

También acepta `SERIAL_PORT` y opciones `--mqtt-host`, `--mqtt-port`, `--mqtt-user`, `--mqtt-pass`, `--node-id`. Serial a 9600 baudios; cierre el monitor serial del IDE. En Linux el usuario necesita acceso al dispositivo (grupo `dialout`). Ctrl+C cierra los recursos y publica `offline`; una caída abrupta usa LWT retenido.

Lecturas cada segundo en simulación; estados al cambiar o cada `--estado-intervalo 10` segundos, retenidos. Los eventos seriales se publican en `puerta/evento`, sin inventar lecturas. Cámara: JPEG binario a 320 px, calidad 70, cada 1.5 s. No ejecute simultáneamente `vision/publish_frames.py` para el mismo nodo.

El panel manda `{"actuador":"ventilacion","accion":"on"}`; el puente escribe `{"cmd":"actuador","nombre":"ventilador","accion":"on"}`. El firmware solo admite calefacción y ventilador (override de 30 s). Rotación manual solo está disponible en simulación; con hardware se registra como no soportada. La simulación mantiene los valores hasta otra orden y respeta el bloqueo. `sistema/estado` retenido se traduce a `{"cmd":"sistema","estado":"bloqueado"}` o `normal`. Los comandos de actuadores retenidos se ignoran.

Si el Arduino se reinicia o se desconecta, el puente reabre el puerto cada 2 s y le reenvía el último estado de bloqueo; no hace falta reiniciarlo. La reconexión MQTT es automática. `status` publica `{"estado":"online"}` u `{"estado":"offline"}` (JSON, retenido); el backend lo guarda en `mqtt_eventos`.

Pruebas: `python -m unittest discover -s gateway -p 'test_*.py'` desde `Proyecto_2`.

Prueba real aislada (requiere `mosquitto` y `mosquitto-clients`): `bash gateway/probar_mqtt.sh`. Usa el puerto 28883 (`TEST_MQTT_PORT` para cambiarlo), rechaza anónimos, comprueba lecturas/estado/cambio de ventilación y estado offline; elimina sus procesos y archivos al terminar. Active el venv antes o indique `PYTHON=/ruta/al/venv/bin/python`.
