"""Prueba el modelo en vivo con la cámara (sin MQTT): muestra clase y probabilidades.

Uso: python probar_camara.py --source 2 [--model models]   (q = salir, espacio = guardar captura)
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from common import preprocess_roi, to_input

COLORES = {"huevo": (0, 200, 0), "objeto": (0, 0, 255), "vacio": (200, 200, 200)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--model", default="models")
    a = ap.parse_args()
    cfg = json.loads((Path(a.model) / "config.json").read_text())
    sess = ort.InferenceSession(str(Path(a.model) / "modelo.onnx"), providers=["CPUExecutionProvider"])
    clases, roi, umbral = cfg["classes"], tuple(cfg["roi"]), cfg["threshold"]

    cap = cv2.VideoCapture(int(a.source) if a.source.isdigit() else a.source)
    if not cap.isOpened():
        raise SystemExit("No se pudo abrir la cámara/fuente")
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.5)
            continue
        h, w = frame.shape[:2]
        frame = cv2.resize(frame, (320, max(1, round(h * 320 / w))))  # igual que bridge.py
        h, w = frame.shape[:2]

        z = sess.run(None, {"input": to_input(preprocess_roi(frame, roi, cfg["size"]))})[0][0]
        p = np.exp(z - z.max())
        p /= p.sum()
        i = int(p.argmax())
        bloqueo = clases[i] == "objeto" and p[i] >= umbral

        vista = cv2.resize(frame, (w * 2, h * 2))
        x, y, rw, rh = roi
        cv2.rectangle(vista, (int(x * w * 2), int(y * h * 2)),
                      (int((x + rw) * w * 2), int((y + rh) * h * 2)), COLORES[clases[i]], 3)
        cv2.putText(vista, f"{clases[i]} {p[i]:.2f}" + ("  BLOQUEO" if bloqueo else ""),
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORES[clases[i]], 2)
        for j, c in enumerate(clases):
            cv2.putText(vista, f"{c}: {p[j]:.2f}", (10, 60 + 25 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("prueba modelo", vista)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord(" "):
            Path("evidencias").mkdir(exist_ok=True)
            cv2.imwrite(f"evidencias/vivo_{time.strftime('%Y%m%d_%H%M%S')}_{clases[i]}.jpg", vista)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
