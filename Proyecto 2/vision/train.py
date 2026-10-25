"""Entrena el clasificador huevo / objeto / vacio (transfer learning MobileNetV3-small),
evalúa (exactitud + matriz de confusión + tabla de umbrales) y exporta a ONNX.

Uso:
  python train.py --roi 0,0,1,1 --epochs 15
Requiere dataset/{huevo,objeto,vacio}/{clase}_{sesion}_{n}.jpg (ver capture_dataset.py).
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import matplotlib
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from torch.utils.data import DataLoader, Dataset
from torchvision import models
from torchvision import transforms as T

from common import MEAN, SIZE, STD, preprocess_roi

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CLASSES = ["huevo", "objeto", "vacio"]
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def listar(dataset_dir):
    items = []
    for i, c in enumerate(CLASSES):
        for p in sorted((Path(dataset_dir) / c).glob("*.jpg")):
            items.append((str(p), i))
    return items


def split_por_sesion(items, seed=42):
    """70/15/15 separando por sesión (evita fotos casi idénticas en train y test)."""
    rng = random.Random(seed)
    out = {"train": [], "val": [], "test": []}
    for ci, c in enumerate(CLASSES):
        grupos = {}
        for p, l in items:
            if l == ci:
                grupos.setdefault(Path(p).stem.split("_")[1], []).append((p, l))
        claves = sorted(grupos)
        rng.shuffle(claves)
        n = len(claves)
        if n < 3:
            raise SystemExit(f"Clase '{c}': necesitas >=3 sesiones distintas (tienes {n}).")
        nt = max(1, round(n * 0.15))
        nv = max(1, round(n * 0.15))
        for i, k in enumerate(claves):
            dest = "test" if i < nt else "val" if i < nt + nv else "train"
            out[dest] += grupos[k]
    return out


class DS(Dataset):
    def __init__(self, items, roi, train):
        self.items, self.roi = items, roi
        t = [T.ToPILImage()]
        if train:
            t += [T.ColorJitter(0.4, 0.4, 0.4, 0.05), T.RandomRotation(10), T.RandomHorizontalFlip()]
        t += [T.ToTensor(), T.Normalize(MEAN.tolist(), STD.tolist())]
        self.t = T.Compose(t)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, l = self.items[i]
        img = cv2.imread(p)
        return self.t(preprocess_roi(img, self.roi)), l


def run_epoch(model, dl, crit, opt=None):
    train = opt is not None
    model.train(train)
    tot = corr = 0
    loss_sum = 0.0
    with torch.set_grad_enabled(train):
        for x, y in dl:
            x, y = x.to(dev), y.to(dev)
            out = model(x)
            loss = crit(out, y)
            if train:
                opt.zero_grad()
                loss.backward()
                opt.step()
            loss_sum += loss.item() * len(y)
            corr += (out.argmax(1) == y).sum().item()
            tot += len(y)
    return loss_sum / tot, corr / tot


def predecir(model, dl):
    model.eval()
    probs, ys = [], []
    with torch.no_grad():
        for x, y in dl:
            probs.append(torch.softmax(model(x.to(dev)), 1).cpu().numpy())
            ys.append(y.numpy())
    return np.concatenate(probs), np.concatenate(ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset")
    ap.add_argument("--roi", default="0,0,1,1", help="x,y,w,h en fracciones 0..1")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--freeze-epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--out", default="models")
    a = ap.parse_args()
    roi = tuple(float(v) for v in a.roi.split(","))
    out = Path(a.out)
    out.mkdir(exist_ok=True)

    items = listar(a.dataset)
    sp = split_por_sesion(items)
    for k, v in sp.items():
        print(k, len(v), "imágenes")

    dls = {k: DataLoader(DS(v, roi, k == "train"), batch_size=a.bs, shuffle=(k == "train"))
           for k, v in sp.items()}

    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(CLASSES))
    model.to(dev)

    cont = np.bincount([l for _, l in sp["train"]], minlength=len(CLASSES))
    pesos = torch.tensor(cont.sum() / (len(CLASSES) * np.maximum(cont, 1)), dtype=torch.float32).to(dev)
    crit = nn.CrossEntropyLoss(weight=pesos)

    mejor, estado = 0.0, None
    for ep in range(a.epochs):
        if ep == 0:
            for p in model.features.parameters():
                p.requires_grad = False
            opt = torch.optim.Adam(model.classifier.parameters(), lr=1e-3)
        if ep == a.freeze_epochs:
            for p in model.parameters():
                p.requires_grad = True
            opt = torch.optim.Adam(model.parameters(), lr=1e-4)
        tl, ta = run_epoch(model, dls["train"], crit, opt)
        vl, va = run_epoch(model, dls["val"], crit)
        print(f"ep {ep+1:02d} train {ta:.3f} (loss {tl:.3f}) | val {va:.3f} (loss {vl:.3f})")
        if va >= mejor:
            mejor = va
            estado = {k: v.clone() for k, v in model.state_dict().items()}
    model.load_state_dict(estado)

    # Evaluación en test
    probs, y = predecir(model, dls["test"])
    pred = probs.argmax(1)
    conf = probs.max(1)
    acc = accuracy_score(y, pred)
    cm = confusion_matrix(y, pred, labels=range(len(CLASSES)))
    print(f"\nExactitud test: {acc:.4f}")
    print(classification_report(y, pred, target_names=CLASSES, digits=3))
    print(cm)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3), CLASSES)
    ax.set_yticks(range(3), CLASSES)
    ax.set_xlabel("Predicho")
    ax.set_ylabel("Real")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center")
    fig.tight_layout()
    fig.savefig(out / "matriz_confusion.png", dpi=150)

    # Umbrales: falsos bloqueos vs. objetos detectados
    oi = CLASSES.index("objeto")
    tabla, recomendado = [], 0.9
    for t in np.arange(0.5, 0.96, 0.05):
        det = (pred == oi) & (conf >= t)
        fp = int((det & (y != oi)).sum())
        rec = float((det & (y == oi)).sum() / max(1, (y == oi).sum()))
        tabla.append({"umbral": round(float(t), 2), "falsos_bloqueos": fp, "recall_objeto": round(rec, 3)})
    for fila in tabla:
        if fila["falsos_bloqueos"] == 0:
            recomendado = fila["umbral"]
            break
    print("\nUmbral -> falsos bloqueos / recall objeto")
    for f in tabla:
        print(f)
    print("Umbral recomendado:", recomendado)

    (out / "metrics.json").write_text(json.dumps({
        "exactitud_test": acc,
        "matriz_confusion": cm.tolist(),
        "clases": CLASSES,
        "reporte": classification_report(y, pred, target_names=CLASSES, output_dict=True),
        "umbrales": tabla,
        "umbral_recomendado": recomendado,
    }, indent=2))
    (out / "config.json").write_text(json.dumps({
        "classes": CLASSES, "roi": list(roi), "size": SIZE, "threshold": recomendado}, indent=2))

    # Exportar a ONNX
    model.eval().cpu()
    dummy = torch.randn(1, 3, SIZE, SIZE)
    kw = dict(input_names=["input"], output_names=["logits"],
              dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    try:
        torch.onnx.export(model, dummy, str(out / "modelo.onnx"), dynamo=False, **kw)
    except TypeError:
        torch.onnx.export(model, dummy, str(out / "modelo.onnx"), **kw)
    print("Guardado:", out / "modelo.onnx")


if __name__ == "__main__":
    main()
