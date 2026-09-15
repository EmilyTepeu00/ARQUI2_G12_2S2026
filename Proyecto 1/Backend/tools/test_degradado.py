"""Comprueba que el backend funcione SIN base de datos.

Apunta a un puerto muerto a proposito. Verifica que la app arranque igual, que
cada metodo devuelva su valor neutro en vez de lanzar excepcion, y que la API
siga respondiendo. No necesita Mongo.

    python tools/test_degradado.py      # en Proyecto_1/Backend
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, sys
os.environ.update(MONGO_URI="mongodb://localhost:59999", MONGO_DB_NAME="smartegg_nope",
                  MONGO_REQUIRED="false", MONGO_RECONNECT_DELAY="2",
                  SERIAL_ENABLED="false", MQTT_ENABLED="false",
                  JWT_SECRET="s", ADMIN_PASSWORD="x")
from src import create_app
from src.db import db
app = create_app(); c = app.test_client()
ok = fallos = 0
def check(n, cond, extra=""):
    global ok, fallos
    if cond: ok += 1; print(f"  OK   {n}")
    else: fallos += 1; print(f"  FALLA {n} {extra}")

print("\n== arranca sin base (no revienta) ==")
check("app construida", app is not None)
check("db.disponible = False", db.disponible is False)
check("estado() lo reporta", db.estado()["conectado"] is False)
check("hilo de reconexion activo", db._reintento_activo is True)

print("\n== valores neutros, sin excepciones ==")
check("guardar_lectura -> None", db.guardar_lectura({"temperatura": 1}) is None)
check("obtener_historial -> []", db.obtener_historial() == [])
check("obtener_ultima_lectura -> None", db.obtener_ultima_lectura() is None)
check("listar_lotes -> []", db.listar_lotes() == [])
check("contar_lotes_activos -> 0", db.contar_lotes_activos() == 0)
check("listar_operadores -> []", db.listar_operadores() == [])
check("serie_temporal -> []", db.serie_temporal(None, None) == [])
check("resumen_diario -> []", db.resumen_diario(7) == [])
check("conteo_alarmas_por_tipo -> []", db.conteo_alarmas_por_tipo(None, None) == [])
check("estadisticas_por_lote -> None", db.estadisticas_por_lote("x") is None)
r = db.resumen_puerta(None, None)
check("resumen_puerta -> dict en cero", r["veces_abierta"] == 0 and r["por_operador"] == [])
check("actividad_por_operador -> []", db.actividad_por_operador(None, None) == [])

print("\n== la API responde igual ==")
h = c.get("/health")
check("GET /health = 200", h.status_code == 200, h.status_code)
check("health marca la base caida", h.get_json()["base_datos"] is False,
      h.get_json())
check("GET /api/sensores/historial = 200", c.get("/api/sensores/historial").status_code == 200)
check("GET /api/historico/series = 200", c.get("/api/historico/series").status_code == 200)
check("GET /api/historico/diario = 200", c.get("/api/historico/diario").status_code == 200)
check("POST /api/lotes -> 503", c.post("/api/lotes",
      json={"codigo":"A","nombre_lote":"B","cantidad_huevos":5}).status_code in (401, 503))
print(f"\n=== {ok} OK, {fallos} fallos ===")
sys.exit(1 if fallos else 0)
