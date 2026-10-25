import argparse
import os
import time

import cv2
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--source", default="0")
ap.add_argument("--id", default=os.getenv("DEVICE_ID", "incubadora-01"))
ap.add_argument("--interval", type=float, default=1.5)
ap.add_argument("--width", type=int, default=320)
a = ap.parse_args()

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="frames-test")
if os.getenv("MQTT_USER"):
    c.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASS"))
c.connect(os.getenv("MQTT_HOST", "localhost"), int(os.getenv("MQTT_PORT", "1883")), 60)
c.loop_start()

es_imagen = os.path.isfile(a.source)
fija = cv2.imread(a.source) if es_imagen else None
cap = None if es_imagen else cv2.VideoCapture(int(a.source) if a.source.isdigit() else a.source)
topic = f"smartegg/{a.id}/camara/frame"

while True:
    if es_imagen:
        frame = fija
    else:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.5)
            continue
    h, w = frame.shape[:2]
    frame = cv2.resize(frame, (a.width, int(h * a.width / w)))
    ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    c.publish(topic, jpg.tobytes(), qos=0)
    print("frame", len(jpg), "bytes ->", topic)
    time.sleep(a.interval)
