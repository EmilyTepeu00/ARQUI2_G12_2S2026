"""Genera y ejecuta anomalias.ipynb. Uso: .venv/bin/python construir_notebook.py"""
import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
celdas = [
md("""# SmartEgg Fase 3 · Detección de anomalías (Bloque A)

Pipeline completo: histórico de la Fase 2 → exploración → limpieza y features → entrenamiento → evaluación → modelo guardado para `ml/service.py`.

**Fuente:** colección `lecturas` de MongoDB (Fase 2), exportada a `data/lecturas_fase2.csv` con:
```bash
docker exec smartegg-mongo mongoexport --db smartegg --collection lecturas --type=csv \\
  --fields timestamp,temperatura,humedad,calefaccion,ventilacion,rotacion,sistema_encendido,alarma,puerta_abierta,espacios_libres,node_id \\
  --sort '{timestamp:1}' > data/lecturas_fase2.csv
```"""),
code("""import json, joblib, numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (f1_score, precision_score, recall_score, roc_auc_score,
                             confusion_matrix, precision_recall_curve, ConfusionMatrixDisplay, classification_report)
from pipeline import FEATURES, cargar, agregar_derivadas, es_falla_sensor, simular_anomalias
sns.set_theme(style="whitegrid"); pd.set_option("display.precision", 3)"""),
md("## 1. Extracción y exploración"),
code("""d = cargar("data/lecturas_fase2.csv")
print(d.shape); d.head()"""),
code("""d.describe().T"""),
code("""print("Nulos por columna:\\n", d.isna().sum().to_string())
print("Filas duplicadas:", d.duplicated().sum(), "| marcas de tiempo repetidas:", d.timestamp.duplicated().sum())
print("Lecturas por día:\\n", d.timestamp.dt.date.value_counts().sort_index().to_string())"""),
code("""fig, ax = plt.subplots(1, 3, figsize=(16, 4))
sns.histplot(d.temperatura, bins=80, ax=ax[0]).set_title("Temperatura (°C)")
sns.histplot(d.humedad, bins=80, ax=ax[1]).set_title("Humedad (%)")
sns.scatterplot(data=d.sample(5000, random_state=0), x="temperatura", y="humedad", hue="calefaccion", s=8, ax=ax[2])
ax[2].set_title("Temperatura vs humedad (color = calefacción)"); plt.tight_layout()"""),
code("""print(pd.crosstab(pd.cut(d.temperatura, [-1, 5, 30, 35, 36.5, 38.5, 50]), [d.calefaccion, d.alarma]))"""),
md("""**Hallazgos**

- No hay nulos ni duplicados; la frecuencia típica es de 1 lectura por segundo, con huecos entre sesiones de prueba.
- Hay **dos regímenes normales**: incubación (36.5–38.5 °C, foco regulando) y **precalentamiento** (20–35 °C con la calefacción encendida y la temperatura subiendo, sin alarma). El segundo es la maqueta real a temperatura ambiente.
- Las lecturas con `alarma = 1` son las que el firmware marcó fuera de umbral. Las lecturas con temperatura < 5 °C o humedad < 5 % son fallas del DHT.

Por eso no basta con un umbral fijo: 30 °C es normal si el foco está encendido calentando, pero es anómalo si está apagado. El modelo aprende esa relación conjunta entre sensores y actuadores."""),
md("""## 2. Preprocesamiento y etiquetado

- **Features:** temperatura, humedad, estado de los 3 actuadores y la derivada por segundo de temperatura y humedad (`d_temp`, `d_hum`). Si dos lecturas están separadas más de 10 s la derivada se reinicia, para no confundir el cambio entre sesiones con un salto real.
- **Escalado:** `StandardScaler`. LOF usa distancias, así que sin escalar la humedad (rango ~50) dominaría a los actuadores (0/1).
- **Estrategia no supervisada:** se entrena **solo con lecturas normales** (`alarma = 0` y sin falla de sensor). Las etiquetas sirven únicamente para evaluar:
  - anomalías **reales**: lecturas con `alarma = 1` y fallas del sensor;
  - anomalías **simuladas** sobre lecturas reales: sobrecalentamiento con el foco pegado, enfriamiento con el foco quemado, humedad muy baja o alta, saltos bruscos y actuadores incoherentes."""),
code("""d = agregar_derivadas(d)
falla = es_falla_sensor(d)
normales = d[(d.alarma == 0) & ~falla]
reales = d[(d.alarma == 1) | falla]
print(f"normales={len(normales)}  anomalías reales={len(reales)} (fallas de sensor={falla.sum()})")

mezcla = normales.sample(frac=1, random_state=1)
n = len(mezcla)
train, val, test_n = mezcla[: int(n * .70)], mezcla[int(n * .70): int(n * .85)], mezcla[int(n * .85):]
r = reales.sample(frac=1, random_state=1)
val_r, test_r = r[: len(r) // 2], r[len(r) // 2:]
val_s, _ = simular_anomalias(train, 400, seed=1)
test_s, tipos_test = simular_anomalias(train, 400, seed=2)

def armar(norm, *anom):
    X = pd.concat([norm, *anom])[FEATURES]
    y = np.r_[np.zeros(len(norm)), np.ones(sum(len(a) for a in anom))]
    return X, y

X_val, y_val = armar(val, val_r, val_s)
X_test, y_test = armar(test_n, test_r, test_s)
print("train", train.shape, "| val", X_val.shape, int(y_val.sum()), "anómalas | test", X_test.shape, int(y_test.sum()), "anómalas")"""),
md("""## 3. Entrenamiento y evaluación

Se comparan dos algoritmos de detección de novedades de scikit-learn:

- **Isolation Forest:** aísla puntos con cortes aleatorios; es rápido, pero sus cortes son paralelos a los ejes.
- **Local Outlier Factor (`novelty=True`):** compara la densidad local de cada lectura con la de sus vecinos.

En los dos casos el umbral sobre el puntaje se elige en **validación** maximizando el F1, y las métricas finales se miden en **test**, un conjunto que el modelo no vio."""),
code("""def evaluar(nombre, modelo):
    p = make_pipeline(StandardScaler(), modelo).fit(train[FEATURES])
    s_val, s_test = -p.score_samples(X_val), -p.score_samples(X_test)   # mayor = más anómalo
    pr, rc, th = precision_recall_curve(y_val, s_val)
    f1 = 2 * pr * rc / (pr + rc + 1e-12)
    umbral = float(th[f1[:-1].argmax()])
    pred = s_test >= umbral
    return p, umbral, s_test, pred, {
        "modelo": nombre, "umbral": round(umbral, 4),
        "precision": precision_score(y_test, pred), "recall": recall_score(y_test, pred),
        "f1": f1_score(y_test, pred), "auc_roc": roc_auc_score(y_test, s_test)}

res = {
    "IsolationForest": evaluar("IsolationForest", IsolationForest(n_estimators=300, random_state=0)),
    "LOF": evaluar("LOF", LocalOutlierFactor(n_neighbors=35, novelty=True)),
}
tabla = pd.DataFrame([r[4] for r in res.values()]).set_index("modelo"); tabla"""),
code("""fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for a, (nombre, r) in zip(ax, res.items()):
    ConfusionMatrixDisplay(confusion_matrix(y_test, r[3]), display_labels=["normal", "anomalía"]).plot(ax=a, colorbar=False)
    a.set_title(f"{nombre}  F1={r[4]['f1']:.3f}")
plt.tight_layout(); plt.savefig("evidencias/matriz_confusion.png", dpi=120)"""),
code("""modelo, umbral, s_test, pred, met = res["LOF"]
print(classification_report(y_test, pred, target_names=["normal", "anomalía"], digits=3))
n_norm, n_real = len(test_n), len(test_r)
print("Recall en anomalías reales del histórico:", round(pred[n_norm:n_norm + n_real].mean(), 3))
print("Recall por tipo de anomalía simulada:")
print(pd.Series(pred[n_norm + n_real:]).groupby(tipos_test).mean().round(3).to_string())"""),
code("""plt.figure(figsize=(8, 3.5))
sns.histplot(x=s_test, hue=np.where(y_test == 1, "anomalía", "normal"), bins=80, log_scale=(True, False), element="step")
plt.axvline(umbral, color="red", ls="--", label=f"umbral={umbral:.2f}"); plt.legend(); plt.title("Puntaje LOF en test")
plt.tight_layout(); plt.savefig("evidencias/distribucion_puntaje.png", dpi=120)"""),
md("""**Elección: LOF.** Supera a Isolation Forest en F1 y AUC y detecta casi todas las anomalías reales del histórico. Isolation Forest falla sobre todo en las fallas que **combinan** variables (enfriamiento con el foco apagado, actuadores incoherentes), porque sus cortes son paralelos a los ejes. LOF, en cambio, mide la distancia al comportamiento conocido en el espacio conjunto.

**Umbral:** puntaje LOF ≥ el umbral elegido en validación. Para no alarmar por una sola lectura ruidosa, el servicio además exige **3 lecturas anómalas seguidas** antes de publicar `anomalia: true` (configurable con `ML_CONSECUTIVAS`)."""),
md("## 4. Guardado del modelo"),
code("""joblib.dump(modelo, "modelo/modelo_lof.joblib")
meta = {"algoritmo": "LocalOutlierFactor(n_neighbors=35, novelty=True) + StandardScaler",
        "features": FEATURES, "umbral": umbral,
        "metricas_test": {k: round(float(v), 4) for k, v in met.items() if k != "modelo"},
        "comparacion": tabla.round(4).reset_index().to_dict("records"),
        "n_train": len(train), "n_test": int(len(y_test)), "anomalias_test": int(y_test.sum())}
json.dump(meta, open("modelo/meta.json", "w"), indent=2, ensure_ascii=False)
meta["metricas_test"]"""),
code("""# Prueba rápida del modelo cargado desde disco: una lectura normal y dos fallas.
m = joblib.load("modelo/modelo_lof.joblib")
casos = pd.DataFrame([
    dict(temperatura=37.5, humedad=57, calefaccion=0, ventilacion=0, rotacion=0, d_temp=0.0, d_hum=0.0),
    dict(temperatura=41.0, humedad=57, calefaccion=1, ventilacion=0, rotacion=0, d_temp=0.2, d_hum=0.0),
    dict(temperatura=37.5, humedad=20, calefaccion=0, ventilacion=0, rotacion=0, d_temp=0.0, d_hum=-2.0),
], index=["normal", "foco pegado", "humedad baja"])[FEATURES]
pd.DataFrame({"puntaje": -m.score_samples(casos), "anomalia": -m.score_samples(casos) >= umbral}, index=casos.index)"""),
]

nb = nbf.v4.new_notebook(cells=celdas, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": "."}})
nbf.write(nb, "anomalias.ipynb")
print("anomalias.ipynb listo")
