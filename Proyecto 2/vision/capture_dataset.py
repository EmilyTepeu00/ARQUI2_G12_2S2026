"""Captura el dataset con vista previa de la cámara, el ROI y lo que ve el modelo.

Teclas: 1 huevo | 2 objeto | 3 vacio | espacio foto | a auto on/off | n sesion siguiente | q salir
ROI: arrastra con el mouse sobre la ventana "captura" (en vivo).
"""
import argparse
import time
from pathlib import Path

import cv2

from common import preprocess_roi

CLASES = {ord("1"): "huevo", ord("2"): "objeto", ord("3"): "vacio"}
ANCHO = 320  # igual que gateway/bridge.py: el modelo entrena con los mismos fotogramas que recibe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0")
    ap.add_argument("--sesion", required=True, help="ej. s01 (sin guion bajo)")
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--cada", type=float, default=0.7, help="segundos entre fotos en auto")
    ap.add_argument("--roi", default=None, help="x,y,w,h en fracciones 0..1 (def. roi.txt o 0,0,1,1)")
    a = ap.parse_args()
    if "_" in a.sesion:
        raise SystemExit("La sesión no puede tener '_' (usa s01, luzfria, etc.)")
    archivo_roi = Path("roi.txt")
    texto = a.roi or (archivo_roi.read_text().strip() if archivo_roi.exists() else "0,0,1,1")
    roi = tuple(float(v) for v in texto.split(","))
    print("ROI actual: --roi " + texto, flush=True)

    src = int(a.source) if a.source.isdigit() else a.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit("No se pudo abrir la cámara/fuente")

    arrastre = {}

    def mouse(ev, mx, my, *_):
        if ev == cv2.EVENT_LBUTTONDOWN:
            arrastre.update(ini=(mx, my), fin=(mx, my))
        elif ev == cv2.EVENT_MOUSEMOVE and "ini" in arrastre:
            arrastre["fin"] = (mx, my)
        elif ev == cv2.EVENT_LBUTTONUP and "ini" in arrastre:
            arrastre["listo"] = (*arrastre.pop("ini"), mx, my)

    cv2.namedWindow("captura")
    cv2.setMouseCallback("captura", mouse)

    clase, auto, last = "huevo", False, 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Sin fotograma, reintentando...")
            time.sleep(0.5)
            continue
        h, w = frame.shape[:2]
        frame = cv2.resize(frame, (ANCHO, max(1, round(h * ANCHO / w))))
        h, w = frame.shape[:2]

        carpeta = Path(a.out) / clase
        carpeta.mkdir(parents=True, exist_ok=True)
        fotos = sorted(carpeta.glob(f"{clase}_{a.sesion}_*.jpg"))
        n = len(fotos)
        sig = int(fotos[-1].stem.split("_")[-1]) + 1 if fotos else 0  # no pisa fotos si se borraron algunas
        totales = {c: len(list((Path(a.out) / c).glob("*.jpg"))) for c in CLASES.values()}

        vista = cv2.resize(frame, (w * 2, h * 2))
        x, y, rw, rh = roi
        cv2.rectangle(vista, (int(x * w * 2), int(y * h * 2)),
                      (int((x + rw) * w * 2), int((y + rh) * h * 2)), (0, 200, 255), 2)
        if "ini" in arrastre:
            cv2.rectangle(vista, arrastre["ini"], arrastre["fin"], (255, 0, 255), 1)
        if "listo" in arrastre:
            x0, y0, x1, y1 = arrastre.pop("listo")
            x0, x1 = sorted((max(0, min(x0, w * 2)), max(0, min(x1, w * 2))))
            y0, y1 = sorted((max(0, min(y0, h * 2)), max(0, min(y1, h * 2))))
            if x1 - x0 > 10 and y1 - y0 > 10:
                roi = (x0 / (w * 2), y0 / (h * 2), (x1 - x0) / (w * 2), (y1 - y0) / (h * 2))
                texto = ",".join(f"{v:.3f}" for v in roi)
                archivo_roi.write_text(texto + "\n")
                print("ROI guardado en roi.txt -> usa en train.py: --roi " + texto, flush=True)
        color = (0, 0, 255) if auto else (0, 255, 0)
        cv2.putText(vista, f"{clase} | sesion {a.sesion} | fotos: {n} | auto: {auto}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(vista, " ".join(f"{c}:{t}" for c, t in totales.items()),
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("captura", vista)
        cv2.imshow("modelo (ROI 224x224)", cv2.cvtColor(preprocess_roi(frame, roi), cv2.COLOR_RGB2BGR))
        k = cv2.waitKey(1) & 0xFF

        guardar = False
        if k == ord("q"):
            break
        elif k in CLASES:
            clase = CLASES[k]
        elif k == ord("a"):
            auto = not auto
        elif k == ord("n") and a.sesion[1:].isdigit():
            a.sesion, auto = f"s{int(a.sesion[1:]) + 1:02d}", False
            print("Sesion ->", a.sesion, flush=True)
        elif k == ord(" "):
            guardar = True
        if auto and time.time() - last >= a.cada:
            guardar = True

        if guardar:
            ruta = carpeta / f"{clase}_{a.sesion}_{sig:04d}.jpg"
            cv2.imwrite(str(ruta), frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            last = time.time()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
