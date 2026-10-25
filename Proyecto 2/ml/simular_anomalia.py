"""Publica lecturas normales y luego una falla, para ver al servicio ML emitir la alerta.

Uso: python simular_anomalia.py [--falla sobrecalentamiento|humedad_baja|foco_quemado] [--host localhost]
"""
import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
ap.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
ap.add_argument("--node", default=os.getenv("NODE_ID", "incubadora-01"))
ap.add_argument("--falla", default="sobrecalentamiento", choices=["sobrecalentamiento", "humedad_baja", "foco_quemado"])
ap.add_argument("--normales", type=int, default=10)
ap.add_argument("--anomalas", type=int, default=10)
a = ap.parse_args()

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"simulador-ml-{os.getpid()}")
if os.getenv("MQTT_USER"):
    c.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASS"))
c.connect(a.host, a.port, 30)
c.loop_start()
topic = f"smartegg/{a.node}/sensores/lectura"
temp, hum = 37.5, 57.0

for i in range(a.normales + a.anomalas):
    calef, vent = int(temp < 37.4), 0
    if i >= a.normales:
        if a.falla == "sobrecalentamiento":   # foco pegado encendido
            temp += 0.35; calef = 1
        elif a.falla == "humedad_baja":
            hum -= 3.5
        else:                                 # foco quemado: enfría y la calefacción no prende
            temp -= 0.4; calef = 0
    lectura = {"temperatura": round(temp + random.uniform(-.05, .05), 2), "humedad": round(hum, 2),
               "calefaccion": calef, "ventilacion": vent, "rotacion": 0,
               "timestamp": datetime.now(timezone.utc).isoformat()}
    c.publish(topic, json.dumps(lectura), qos=0)
    print("normal " if i < a.normales else "FALLA  ", lectura)
    time.sleep(1)

c.loop_stop()
