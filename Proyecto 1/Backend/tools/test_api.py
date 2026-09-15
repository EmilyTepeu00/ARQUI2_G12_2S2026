"""Pruebas de la API: rutas historicas, telemetria publica y guardia de auth.

Levanta la app con su test_client contra un MongoDB real, en una base aparte
(smartegg_test_api) que borra al terminar.

    docker compose up -d mongo          # en Proyecto_1/infra
    python tools/test_api.py            # en Proyecto_1/Backend
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, sys, json, random
from datetime import datetime, timedelta, timezone
# La URI se hereda del entorno si ya viene definida, para que el mismo archivo
# corra en los dos lados: en el anfitrion apunta a localhost, y dentro del
# contenedor del backend la variable ya trae mongodb://mongo:27017.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.update(MONGO_DB_NAME="smartegg_test_api",
                  MONGO_REQUIRED="false", SERIAL_ENABLED="false", MQTT_ENABLED="false",
                  JWT_SECRET="test-secret-para-pruebas", ADMIN_PASSWORD="admin-prueba")
from src import create_app
from src.db import db

app = create_app()
c = app.test_client()
ok = fallos = 0
def check(n, cond, extra=""):
    global ok, fallos
    if cond: ok += 1; print(f"  OK   {n}")
    else: fallos += 1; print(f"  FALLA {n} {extra}")

ahora = datetime.now(timezone.utc)
db.db.drop_collection("lecturas"); db.db.drop_collection("aperturas_puerta"); db.db.drop_collection("alarmas")
for i in range(180):
    db.guardar_lectura({"temperatura": 37.5+random.uniform(-1,1), "humedad": 57+random.uniform(-5,5),
        "sistema_encendido": True, "alarma": i % 30 == 0, "espacios_libres": 2,
        "node_id": "incubadora-01", "timestamp": ahora - timedelta(minutes=180-i)})
for op, d, a in [("OP1",0,"abrir"),("OP1",4,"cerrar"),("OP2",0,"abrir"),("OP2",-1,"cerrar")]:
    db.registrar_apertura({"id_operador":op,"accion":a,"huevos_delta":d,"metodo":"rfid",
                           "timestamp": ahora - timedelta(minutes=20)})
db.abrir_alarma({"tipo":"temperatura_alta","severidad":"critica","mensaje":"39.1C"})

print("\n== rutas registradas ==")
rutas = {str(r.rule) for r in app.url_map.iter_rules()}
for r in ["/api/historico/series","/api/historico/diario","/api/historico/alarmas",
          "/api/historico/operadores","/api/historico/lote/<lote_id>"]:
    check(f"existe {r}", r in rutas)

print("\n== endpoints historicos SIN token (los usa Grafana) ==")
r = c.get("/api/historico/series?intervalo=15")
check("GET /series = 200", r.status_code == 200, r.status_code)
d = r.get_json()
check("trae series", len(d["series"]) > 0, d.get("puntos"))
check("suma 180 lecturas", sum(p["lecturas"] for p in d["series"]) == 180)
check("timestamp en ISO", isinstance(d["series"][0]["timestamp"], str), d["series"][0]["timestamp"])
check("intervalo respetado", d["intervalo_minutos"] == 15, d["intervalo_minutos"])

r = c.get("/api/historico/series?intervalo=1&desde=" + (ahora-timedelta(days=30)).isoformat())
check("tope de puntos aplicado", r.get_json()["intervalo_minutos"] > 1, r.get_json()["intervalo_minutos"])

r = c.get("/api/historico/diario?dias=7")
check("GET /diario = 200", r.status_code == 200)
check("diario trae filas", len(r.get_json()["resumen"]) > 0)

r = c.get("/api/historico/alarmas")
check("GET /alarmas = 200", r.status_code == 200)
check("alarmas por tipo", r.get_json()["total"] == 1, r.get_json())

r = c.get("/api/historico/operadores")
check("GET /operadores = 200", r.status_code == 200)
check("2 operadores", len(r.get_json()["operadores"]) == 2, r.get_json())

r = c.get("/api/historico/lote/000000000000000000000000")
check("lote inexistente = 404", r.status_code == 404, r.status_code)

print("\n== no rompi lo que ya andaba ==")
for ruta in ["/health", "/", "/api/sensores/actual", "/api/sensores/historial?limit=5",
             "/api/lotes", "/api/openapi.json", "/api/puerta/resumen"]:
    r = c.get(ruta)
    check(f"GET {ruta}", r.status_code == 200, r.status_code)

r = c.post("/api/auth/login", json={"username":"admin","password":"admin-prueba"})
check("login admin = 200", r.status_code == 200, r.data[:120])
token = r.get_json().get("token") if r.status_code == 200 else None
check("devuelve token", bool(token))
if token:
    h = {"Authorization": f"Bearer {token}"}
    check("GET /api/perfil con token", c.get("/api/perfil", headers=h).status_code == 200)
    check("GET /api/operadores con token", c.get("/api/operadores", headers=h).status_code == 200)
    check("auth llega a usuarios via db.db", db.db["usuarios"].count_documents({}) >= 1)
check("GET /api/operadores sin token = 401", c.get("/api/operadores").status_code == 401)
check("POST /api/lotes sin token = 401",
      c.post("/api/lotes", json={"codigo":"X","nombre_lote":"Y","cantidad_huevos":1}).status_code == 401)

db.client.drop_database("smartegg_test_api")
print(f"\n=== {ok} OK, {fallos} fallos ===")
sys.exit(1 if fallos else 0)
