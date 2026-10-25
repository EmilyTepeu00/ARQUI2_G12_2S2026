"""Funciones compartidas por el notebook y el servicio: limpieza, features y anomalías simuladas."""
import numpy as np
import pandas as pd

FEATURES = ["temperatura", "humedad", "calefaccion", "ventilacion", "rotacion", "d_temp", "d_hum"]
ACTUADORES = ["calefaccion", "ventilacion", "rotacion"]
GAP_S = 10  # dos lecturas separadas más de esto son sesiones distintas: la derivada se reinicia


def cargar(ruta):
    d = pd.read_csv(ruta, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    for c in ACTUADORES + ["alarma", "sistema_encendido", "puerta_abierta"]:
        d[c] = d[c].astype(str).str.lower().isin(["true", "1"]).astype(int)
    return d


def agregar_derivadas(d):
    """Cambio de temperatura y humedad respecto a la lectura anterior, en unidades por segundo."""
    dt = d["timestamp"].diff().dt.total_seconds()
    nueva_sesion = dt.isna() | (dt > GAP_S)
    dt = dt.where(~nueva_sesion, 1.0)
    d["d_temp"] = (d["temperatura"].diff() / dt).where(~nueva_sesion, 0.0)
    d["d_hum"] = (d["humedad"].diff() / dt).where(~nueva_sesion, 0.0)
    return d


def es_falla_sensor(d):
    """Lecturas físicamente imposibles dentro de la incubadora (DHT desconectado o en error)."""
    return (d["temperatura"] < 5) | (d["humedad"] < 5)


def simular_anomalias(normales, n, seed=7):
    """Fallas inyectadas sobre lecturas normales reales. Devuelve (DataFrame, tipo por fila)."""
    rng = np.random.default_rng(seed)
    base = normales.sample(n, random_state=seed, replace=True).reset_index(drop=True).copy()
    tipos = rng.choice(["sobrecalentamiento", "enfriamiento", "humedad_baja", "humedad_alta",
                        "salto_brusco", "actuador_incoherente"], size=n)
    for i, t in enumerate(tipos):
        r = base.loc[i]
        if t == "sobrecalentamiento":      # foco pegado: sube la temperatura con la calefacción encendida
            r["temperatura"] = rng.uniform(39.0, 42.0); r["calefaccion"] = 1; r["ventilacion"] = 0
            r["d_temp"] = rng.uniform(0.05, 0.4)
        elif t == "enfriamiento":           # foco quemado: baja la temperatura y la calefacción no responde
            r["temperatura"] = rng.uniform(30.0, 35.5); r["calefaccion"] = 0
            r["d_temp"] = rng.uniform(-0.4, -0.05)
        elif t == "humedad_baja":
            r["humedad"] = rng.uniform(15, 38); r["d_hum"] = rng.uniform(-3, -0.5)
        elif t == "humedad_alta":
            r["humedad"] = rng.uniform(78, 98); r["d_hum"] = rng.uniform(0.5, 3)
        elif t == "salto_brusco":           # puerta abierta o sensor inestable
            r["d_temp"] = rng.choice([-1, 1]) * rng.uniform(1.0, 3.0)
            r["d_hum"] = rng.choice([-1, 1]) * rng.uniform(5, 15)
        else:                               # ventilador y calefacción a la vez con temperatura alta
            r["calefaccion"] = 1; r["ventilacion"] = 1; r["temperatura"] = rng.uniform(38.6, 40.0)
        base.loc[i] = r
    return base, tipos
