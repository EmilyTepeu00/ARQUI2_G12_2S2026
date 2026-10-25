"""Servicio ML: evalúa cada lectura de smartegg/{id}/sensores/lectura y publica smartegg/{id}/ml/anomalia."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import paho.mqtt.client as mqtt

from pipeline import ACTUADORES, FEATURES, GAP_S

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ml")

MODEL_DIR = Path(os.getenv("MODEL_DIR", Path(__file__).parent / "modelo"))
modelo = joblib.load(MODEL_DIR / "modelo_lof.joblib")
meta = json.loads((MODEL_DIR / "meta.json").read_text())
UMBRAL = float(os.getenv("ML_UMBRAL", meta["umbral"]))
CONSECUTIVAS = int(os.getenv("ML_CONSECUTIVAS", "3"))       # lecturas anómalas seguidas para alertar
PUBLICAR_CADA = float(os.getenv("ML_PUBLICAR_CADA", "5"))   # seg entre publicaciones si no cambia el estado

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")
PREFIJO = os.getenv("MQTT_TOPIC_PREFIX", "smartegg")
NODE_ID = os.getenv("NODE_ID", "+")  # "+" = cualquier incubadora

nodos = {}  # node_id -> estado: última lectura, actuadores, racha y última publicación


def _bool(v):
    return int(str(v).strip().lower() in {"1", "true", "on", "encendido"})


def _ts(v):
    try:
        if isinstance(v, (int, float)):
            return v / 1000 if v > 1e12 else float(v)
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return time.time()


def nodo(node_id):
    return nodos.setdefault(node_id, {"racha": 0, "anomalia": False, "ultima": 0,
                                      "actuadores": dict.fromkeys(ACTUADORES, 0)})


def actualizar_actuadores(n, p):
    """Toma el último estado conocido; la lectura no siempre trae los tres actuadores."""
    for a, alias in (("calefaccion", "calentador"), ("ventilacion", "ventilador"), ("rotacion", "motor")):
        if a in p or alias in p:
            n["actuadores"][a] = _bool(p.get(a, p.get(alias)))


def features(n, p):
    """Arma el vector de features con la lectura actual y la anterior del mismo nodo."""
    temp = float(p.get("temperatura", p.get("temp")))
    hum = float(p.get("humedad", p.get("hum")))
    actualizar_actuadores(n, p)
    act = n["actuadores"]
    ts = _ts(p.get("timestamp"))
    prev = n.get("prev")
    dt = ts - prev[0] if prev else 0
    d_temp = (temp - prev[1]) / dt if prev and 0 < dt <= GAP_S else 0.0
    d_hum = (hum - prev[2]) / dt if prev and 0 < dt <= GAP_S else 0.0
    n["prev"] = (ts, temp, hum)
    fila = dict(temperatura=temp, humedad=hum, d_temp=d_temp, d_hum=d_hum, **act)
    return pd.DataFrame([fila])[FEATURES]


def motivo(x):
    """Variable más alejada de lo normal (z-score del escalador del modelo)."""
    z = modelo[0].transform(x)[0]
    i = abs(z).argmax()
    return FEATURES[i], round(float(z[i]), 2)


def evaluar(client, node_id, p):
    n = nodo(node_id)
    x = features(n, p)
    puntaje = float(-modelo.score_samples(x)[0])
    atipica = puntaje >= UMBRAL
    n["racha"] = n["racha"] + 1 if atipica else 0
    anomalia = n["racha"] >= CONSECUTIVAS
    ahora = time.time()
    if anomalia == n["anomalia"] and ahora - n["ultima"] < PUBLICAR_CADA:
        return
    n["anomalia"], n["ultima"] = anomalia, ahora
    var, z = motivo(x)
    msg = {
        "anomalia": anomalia,
        "puntaje": round(puntaje, 4),
        "umbral": round(UMBRAL, 4),
        "lecturas_atipicas_seguidas": n["racha"],
        "variable_principal": var,
        "desviacion_z": z,
        "modelo": "LOF",
        "lectura": {k: round(float(v), 3) for k, v in x.iloc[0].items()},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    client.publish(f"{PREFIJO}/{node_id}/ml/anomalia", json.dumps(msg), qos=1)
    log.info("%s -> %s puntaje=%.2f (%s z=%.1f)", node_id, "ANOMALIA" if anomalia else "normal", puntaje, var, z)


def on_connect(client, userdata, flags, rc, props=None):
    log.info("Conectado al broker %s:%s (rc=%s), umbral=%.3f", MQTT_HOST, MQTT_PORT, rc, UMBRAL)
    client.subscribe([(f"{PREFIJO}/{NODE_ID}/sensores/lectura", 0), (f"{PREFIJO}/{NODE_ID}/actuadores/estado", 1)])


def on_message(client, userdata, msg):
    if msg.retain:  # snapshot viejo: no es una lectura nueva
        return
    try:
        p = json.loads(msg.payload)
        node_id = msg.topic.split("/")[1]
        if msg.topic.endswith("actuadores/estado"):
            actualizar_actuadores(nodo(node_id), p.get("actuadores", p))
        else:
            evaluar(client, node_id, p)
    except (ValueError, TypeError, KeyError) as e:
        log.warning("Mensaje ignorado en %s: %s", msg.topic, e)


def main():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ml-service-{os.getpid()}")
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.on_connect, c.on_message = on_connect, on_message
    c.reconnect_delay_set(1, 30)
    c.connect_async(MQTT_HOST, MQTT_PORT, 30)
    c.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()
