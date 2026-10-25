"""Vista en vivo de lo que llega por MQTT: fotograma (camara/frame) + ROI + último vision/resultado.

No abre la cámara (la usa el puente). Uso:
  MQTT_HOST=localhost MQTT_PORT=11883 MQTT_USER=smartegg MQTT_PASS=... python ver_camara.py
q = salir, espacio = guardar captura en evidencias/,
g = guía para reposicionar la cámara (superpone referencia.jpg, foto de cómo estaba al entrenar)
"""
import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
import paho.mqtt.client as mqtt

NODO = os.getenv("NODE_ID", "incubadora-01")
ROI = json.loads((Path(__file__).parent / "models" / "config.json").read_text())["roi"]
REFERENCIA = cv2.imread(str(Path(__file__).parent / "referencia.jpg"))
COLORES = {"huevo": (0, 200, 0), "objeto_extrano": (0, 0, 255), "vacio": (200, 200, 200)}
guia = False
ultimo = {"frame": None, "res": None, "estado": "?", "conexion": "conectando al broker..."}


def on_connect(cli, _, flags, rc, props=None):
    ultimo["conexion"] = "Esperando fotogramas (esta corriendo el puente?)" if rc == 0 else f"Broker rechazo la conexion: {rc}"


def on_message(cli, _, msg):
    if msg.topic.endswith("camara/frame"):
        ultimo["frame"] = cv2.imdecode(np.frombuffer(msg.payload, np.uint8), cv2.IMREAD_COLOR)
    elif msg.topic.endswith("vision/resultado"):
        ultimo["res"] = json.loads(msg.payload)
    elif msg.topic.endswith("sistema/estado"):
        ultimo["estado"] = json.loads(msg.payload).get("estado", "?")


cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ver-camara-{os.getpid()}")
if os.getenv("MQTT_USER"):
    cli.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASS"))
cli.on_connect = on_connect
cli.on_message = on_message
cli.connect(os.getenv("MQTT_HOST", "localhost"), int(os.getenv("MQTT_PORT", "1883")), 60)
base = f"smartegg/{NODO}/"
cli.subscribe([(base + "camara/frame", 0), (base + "vision/resultado", 0), (base + "sistema/estado", 0)])
cli.loop_start()

while True:
    f = ultimo["frame"]
    if f is None:
        vista = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(vista, ultimo["conexion"], (20, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    else:
        h, w = f.shape[:2]
        vista = cv2.resize(f, (w * 2, h * 2))
        if guia and REFERENCIA is not None:
            vista = cv2.addWeighted(vista, 0.5, cv2.resize(REFERENCIA, (w * 2, h * 2)), 0.5, 0)
            cv2.putText(vista, "GUIA: mueve la camara hasta que el disco no se vea doble", (10, h * 2 - 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        r = ultimo["res"] or {}
        color = COLORES.get(r.get("clase"), (255, 255, 255))
        x, y, rw, rh = ROI
        cv2.rectangle(vista, (int(x * w * 2), int(y * h * 2)), (int((x + rw) * w * 2), int((y + rh) * h * 2)), color, 3)
        if r:
            cv2.putText(vista, f"{r['clase']} {r['confianza']:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            for j, (c, p) in enumerate(r.get("probabilidades", {}).items()):
                cv2.putText(vista, f"{c}: {p:.2f}", (10, 60 + 25 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        est = ultimo["estado"]
        cv2.putText(vista, f"sistema: {est}", (10, h * 2 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255) if est == "bloqueado" else (0, 200, 0), 2)
    cv2.imshow("camara en vivo (MQTT)", vista)
    k = cv2.waitKey(50) & 0xFF
    if k == ord("q"):
        break
    if k == ord("g"):
        guia = not guia
    if k == ord(" ") and f is not None:
        Path("evidencias").mkdir(exist_ok=True)
        cv2.imwrite(f"evidencias/vivo_{time.strftime('%Y%m%d_%H%M%S')}.jpg", vista)
cli.loop_stop()
cv2.destroyAllWindows()
