
import cv2
import numpy as np

SIZE = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def crop_roi(bgr, roi):
    """roi = (x, y, w, h) en fracciones 0..1 del fotograma."""
    h, w = bgr.shape[:2]
    x, y, rw, rh = roi
    x0, y0 = int(x * w), int(y * h)
    x1, y1 = int((x + rw) * w), int((y + rh) * h)
    return bgr[y0:y1, x0:x1]


def preprocess_roi(bgr, roi, size=SIZE):
    """Recorta la ROI, redimensiona y devuelve RGB uint8 (size x size x 3)."""
    crop = crop_roi(bgr, roi)
    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)


def to_input(rgb):
    """Normaliza (0..1, media/desv. ImageNet) y devuelve tensor NCHW float32."""
    x = rgb.astype(np.float32) / 255.0
    x = (x - MEAN) / STD
    return np.transpose(x, (2, 0, 1))[None].astype(np.float32)
