"""Servicio de visión: smartegg/{id}/camara/frame (JPEG) -> smartegg/{id}/vision/resultado (JSON)."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt

from common import crop_roi, preprocess_roi, to_input

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("vision")

MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
cfg = json.loads((MODEL_DIR / "config.json").read_text())
LABELS = cfg["classes"]
# Nombre del contrato MQTT (backend y web esperan "objeto_extrano"); en disco la clase se llama "objeto".
PUBLICO = {"objeto": "objeto_extrano"}
ROI = tuple(cfg["roi"])
SIZE = cfg["size"]
UMBRAL = float(os.getenv("UMBRAL", cfg["threshold"]))

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")
DEVICE_ID = os.getenv("DEVICE_ID", "+")  # "+" = cualquier incubadora
EVID_DIR = Path(os.getenv("EVIDENCE_DIR", "evidencias"))
EVID_EVERY = float(os.getenv("EVIDENCE_EVERY", "15"))  # seg entre evidencias por clase

sess = ort.InferenceSession(str(MODEL_DIR / "modelo.onnx"), providers=["CPUExecutionProvider"])
last_saved = {}


def softmax(z):
    e = np.exp(z - z.max())
    return e / e.sum()


def guardar_evidencia(frame, rgb, clase, conf):
    ahora = time.time()
    if ahora - last_saved.get(clase, 0) < EVID_EVERY:
        return
    last_saved[clase] = ahora
    EVID_DIR.mkdir(parents=True, exist_ok=True)
    vis = frame.copy()
    h, w = vis.shape[:2]
    x, y, rw, rh = ROI
    cv2.rectangle(vis, (int(x * w), int(y * h)), (int((x + rw) * w), int((y + rh) * h)), (0, 255, 0), 2)
    cv2.putText(vis, f"{clase} {conf:.2f}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    base = f"{datetime.now():%Y%m%d_%H%M%S}_{clase}_{conf:.2f}"
    cv2.imwrite(str(EVID_DIR / f"{base}_frame.jpg"), vis)
    cv2.imwrite(str(EVID_DIR / f"{base}_roi.jpg"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def on_connect(client, userdata, flags, rc, props=None):
    log.info("Conectado al broker (rc=%s)", rc)
    client.subscribe(f"smartegg/{DEVICE_ID}/camara/frame", qos=0)


def on_message(client, userdata, msg):
    t0 = time.time()
    frame = cv2.imdecode(np.frombuffer(msg.payload, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        log.warning("Fotograma inválido (%d bytes)", len(msg.payload))
        return
    rgb = preprocess_roi(frame, ROI, SIZE)
    logits = sess.run(None, {"input": to_input(rgb)})[0][0]
    probs = softmax(logits)
    i = int(probs.argmax())
    clase, conf = LABELS[i], float(probs[i])

    resultado = {
        "clase": PUBLICO.get(clase, clase),
        "confianza": round(conf, 4),
        "probabilidades": {PUBLICO.get(l, l): round(float(p), 4) for l, p in zip(LABELS, probs)},
        "umbral": UMBRAL,
        "objeto_detectado": clase == "objeto" and conf >= UMBRAL,
        "latencia_ms": round((time.time() - t0) * 1000, 1),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    dev_id = msg.topic.split("/")[1]
    client.publish(f"smartegg/{dev_id}/vision/resultado", json.dumps(resultado), qos=0)
    log.info("%s -> %s %.2f%s", dev_id, clase, conf, "  [OBJETO]" if resultado["objeto_detectado"] else "")
    guardar_evidencia(frame, rgb, clase, conf)


def main():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vision-service")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(MQTT_HOST, MQTT_PORT, 60)
    c.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
