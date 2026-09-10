import json
import time
from flask import Blueprint, jsonify, request, Response
from app.database import db
from app.models import serialize_doc, serialize_list
from app.serial_reader import serial_reader

sensors_bp = Blueprint("sensors", __name__)


@sensors_bp.get("/actual")
def obtener_lectura_actual():
    lectura = serial_reader.get_ultima_lectura()
    if lectura is None:
        lectura = db.obtener_ultima_lectura()
        lectura = serialize_doc(lectura)
    if lectura is None:
        return jsonify({"mensaje": "Aún no se ha recibido ninguna lectura."}), 404
    return jsonify(lectura), 200


@sensors_bp.get("/historial")
def obtener_historial():
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100
    limit = max(1, min(limit, 1000))
    lecturas = db.obtener_historial(limit=limit)
    return jsonify(serialize_list(lecturas)), 200


@sensors_bp.get("/estado")
def obtener_estado_conexion():
    estado = serial_reader.get_estado()
    ultima_lectura = serial_reader.get_ultima_lectura()
    return (
        jsonify(
            {
                "serial_conectado": estado["conectado"],
                "puerto": estado["puerto"],
                "ultimo_error": estado["ultimo_error"],
                "ultima_lectura_recibida": ultima_lectura,
                "sensores_activos": {
                    "dht_temperatura_humedad": ultima_lectura is not None,
                    "finales_de_carrera": ultima_lectura is not None,
                    "buzzer": ultima_lectura is not None,
                    "servomotor": ultima_lectura is not None,
                    "reles": ultima_lectura is not None,
                },
            }
        ),
        200,
    )


@sensors_bp.get("/alarmas")
def obtener_alarmas():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 500))
    alarmas = db.obtener_alarmas_recientes(limit=limit)
    return jsonify(serialize_list(alarmas)), 200


@sensors_bp.get("/stream")
def stream_lecturas():
    def event_generator():
        ultimo_enviado = None
        while True:
            lectura = serial_reader.get_ultima_lectura()
            if lectura and lectura != ultimo_enviado:
                ultimo_enviado = lectura
                payload = dict(lectura)
                payload["timestamp"] = str(payload.get("timestamp"))
                yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(1)

    return Response(event_generator(), mimetype="text/event-stream")
