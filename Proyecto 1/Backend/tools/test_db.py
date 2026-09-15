"""Pruebas de la capa de datos (src/db/) contra un MongoDB real.

Usa una base aparte (smartegg_test_db) y la borra al terminar: no toca los
datos de smartegg.

    docker compose up -d mongo          # en Proyecto_1/infra
    python tools/test_db.py             # en Proyecto_1/Backend
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, sys, random
from datetime import datetime, timedelta, timezone

# La URI se hereda del entorno si ya viene definida, para que el mismo archivo
# corra en los dos lados: en el anfitrion apunta a localhost, y dentro del
# contenedor del backend la variable ya trae mongodb://mongo:27017.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ["MONGO_DB_NAME"] = "smartegg_test_db"
os.environ["MONGO_REQUIRED"] = "false"
os.environ["SERIAL_ENABLED"] = "false"
os.environ["MQTT_ENABLED"] = "false"

from src.db import db

ok = fallos = 0
def check(nombre, cond, extra=""):
    global ok, fallos
    if cond:
        ok += 1; print(f"  OK   {nombre}")
    else:
        fallos += 1; print(f"  FALLA {nombre} {extra}")

print("\n== conexion ==")
check("conectado", db.disponible)
check("estado() trae las llaves", set(db.estado()) == {"conectado", "uri", "base"}, db.estado())
check("expone .db (lo usa auth)", db.db is not None)
check("expone .usuarios", db.usuarios is not None)

# Limpieza previa
db.db.drop_collection("lecturas"); db.db.drop_collection("alarmas")
db.db.drop_collection("aperturas_puerta"); db.db.drop_collection("lotes")
db.db.drop_collection("operadores")
db._crear_indices()

print("\n== lecturas ==")
ahora = datetime.now(timezone.utc)
for i in range(240):   # 4 horas, una por minuto
    db.guardar_lectura({
        "temperatura": 37.5 + random.uniform(-1.5, 1.5),
        "humedad": 57 + random.uniform(-8, 8),
        "sistema_encendido": True,
        "alarma": i % 40 == 0,
        "espacios_libres": 3,
        "node_id": "incubadora-01",
        "timestamp": ahora - timedelta(minutes=240 - i),
    })
check("240 lecturas guardadas", db.lecturas.count_documents({}) == 240)
check("obtener_ultima_lectura", db.obtener_ultima_lectura() is not None)
check("obtener_historial(50)", len(db.obtener_historial(50)) == 50)
check("obtener_lecturas_del_dia", isinstance(db.obtener_lecturas_del_dia(ahora), list))

st = db.estadisticas_rango(ahora - timedelta(hours=5), ahora)
check("estadisticas_rango llaves",
      set(st) == {"temp_min","temp_max","temp_prom","hum_min","hum_max","hum_prom","lecturas_totales"}, st)
check("estadisticas_rango cuenta 240", st["lecturas_totales"] == 240)
check("temp_min <= temp_prom <= temp_max", st["temp_min"] <= st["temp_prom"] <= st["temp_max"])

print("\n== series (nuevo) ==")
serie = db.serie_temporal(ahora - timedelta(hours=5), ahora, 30)
check("serie_temporal devuelve puntos", len(serie) > 0, f"len={len(serie)}")
check("un punto por bloque de 30 min", len(serie) <= 11, f"len={len(serie)}")
check("cada punto trae timestamp", all(isinstance(p["timestamp"], datetime) for p in serie))
check("suma de lecturas = 240", sum(p["lecturas"] for p in serie) == 240,
      sum(p["lecturas"] for p in serie))
check("ordenado ascendente", [p["timestamp"] for p in serie] == sorted(p["timestamp"] for p in serie))
check("cuenta alarmas por bloque", sum(p["alarmas"] for p in serie) == 6,
      sum(p["alarmas"] for p in serie))

print("\n== resumen diario (nuevo) ==")
filas = db.resumen_diario(7)
check("resumen_diario devuelve filas", len(filas) > 0)
check("trae la llave dia", all("dia" in f for f in filas))
check("suma de lecturas = 240", sum(f["lecturas"] for f in filas) == 240)

print("\n== lotes ==")
lote = db.crear_lote({"codigo": "L-001", "nombre_lote": "Prueba", "cantidad_huevos": 30,
                      "estado": "incubando", "fecha_ingreso": ahora - timedelta(hours=3)})
check("crear_lote devuelve _id", lote and lote.get("_id") is not None)
check("listar_lotes", len(db.listar_lotes()) == 1)
check("obtener_lote", db.obtener_lote(lote["_id"]) is not None)
check("contar_lotes_activos", db.contar_lotes_activos() == 1)

pl = db.estadisticas_por_lote(lote["_id"])
check("estadisticas_por_lote no es None", pl is not None)
check("estadisticas_por_lote cruza por tiempo", pl and pl["lecturas_totales"] > 0,
      pl["lecturas_totales"] if pl else None)
check("trae dias_incubando", pl and "dias_incubando" in pl)
check("estadisticas_por_lote de un id inexistente da None",
      db.estadisticas_por_lote("no-existe") is None)

print("\n== alarmas ==")
a = db.abrir_alarma({"tipo": "temperatura_alta", "severidad": "critica",
                     "mensaje": "39.2 C", "temperatura": 39.2, "humedad": 55})
check("abrir_alarma devuelve doc", a and a.get("_id"))
check("queda activa", a["activa"] is True)
check("obtener_alarma_activa", db.obtener_alarma_activa() is not None)
c = db.cerrar_alarma(a["_id"], "normalizado")
check("cerrar_alarma calcula duracion", c and c["duracion_segundos"] is not None)
check("cerrar_alarma la desactiva", c["activa"] is False)
check("cerrar_alarma de id inexistente da None", db.cerrar_alarma(None) is None)
db.abrir_alarma({"tipo": "humedad_baja", "severidad": "advertencia", "mensaje": "41%"})
check("obtener_alarmas_recientes", len(db.obtener_alarmas_recientes(10)) == 2)

tipos = db.conteo_alarmas_por_tipo(ahora - timedelta(days=1), ahora + timedelta(minutes=1))
check("conteo_alarmas_por_tipo devuelve 2 tipos", len(tipos) == 2, tipos)
check("cuenta activas", sum(t["activas"] for t in tipos) == 1, tipos)

print("\n== operadores y puerta ==")
db.crear_operador({"id_operador": "OP1", "nombre": "Operador Uno"})
db.crear_operador({"id_operador": "OP2", "nombre": "Operador Dos"})
check("listar_operadores", len(db.listar_operadores()) == 2)
check("obtener_operador", db.obtener_operador("OP1") is not None)

for op, delta, accion in [("OP1", 0, "abrir"), ("OP1", 5, "cerrar"),
                          ("OP2", 0, "abrir"), ("OP2", -2, "cerrar"),
                          ("OP1", 0, "abrir"), ("OP1", 3, "cerrar")]:
    db.registrar_apertura({"id_operador": op, "accion": accion, "huevos_delta": delta,
                           "metodo": "rfid", "timestamp": ahora - timedelta(minutes=30)})
check("listar_aperturas", len(db.listar_aperturas(100)) == 6)
check("filtra por operador", len(db.listar_aperturas(100, id_operador="OP1")) == 4)

r = db.resumen_puerta(ahora - timedelta(days=1), ahora + timedelta(minutes=1))
check("veces_abierta = 3", r["veces_abierta"] == 3, r)
check("veces_cerrada = 3", r["veces_cerrada"] == 3, r)
check("huevos_ingresados = 8", r["huevos_ingresados"] == 8, r)
check("huevos_retirados = 2", r["huevos_retirados"] == 2, r)
check("por_operador trae 2", len(r["por_operador"]) == 2, r["por_operador"])
check("forma de por_operador",
      set(r["por_operador"][0]) == {"id_operador","veces_abierta","veces_cerrada",
                                    "huevos_ingresados","huevos_retirados"})

act = db.actividad_por_operador(ahora - timedelta(days=1), ahora + timedelta(minutes=1))
check("actividad_por_operador ordena desc", act[0]["veces_abierta"] >= act[-1]["veces_abierta"], act)
check("OP1 va primero (2 aperturas)", act[0]["id_operador"] == "OP1", act)

print("\n== indices ==")
idx = {n for n in db.lecturas.index_information()}
check("indice de lecturas por timestamp", any("timestamp" in n for n in idx), idx)
check("indice compuesto en aperturas",
      any("id_operador" in n and "timestamp" in n for n in db.aperturas.index_information()),
      list(db.aperturas.index_information()))
check("usuarios.username es unico",
      any(i.get("unique") for i in db.usuarios.index_information().values()),
      db.usuarios.index_information())

db.client.drop_database("smartegg_test_db")
print(f"\n=== {ok} OK, {fallos} fallos ===")
sys.exit(1 if fallos else 0)
