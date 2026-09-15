import json
import time
from datetime import datetime, timedelta, timezone

from flask import Blueprint, Response, jsonify, request

from src.db import db
from src.models import serialize_doc, serialize_list
from src.mqtt import mqtt_publisher
from src.serial.reader import serial_reader

sensors_bp = Blueprint("sensors", __name__)

# Cada cuanto mandar un latido en el stream SSE si el nodo no publica nada.
HEARTBEAT_SEGUNDOS = 15


def _parsear_fecha(valor):
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha


@sensors_bp.get("/actual")
def obtener_lectura_actual():
    lectura = serial_reader.get_ultima_lectura()
    if lectura is None:
        lectura = serialize_doc(db.obtener_ultima_lectura())
    if lectura is None:
        return jsonify({"mensaje": "Aún no se ha recibido ninguna lectura."}), 404
    if isinstance(lectura.get("timestamp"), datetime):
        lectura["timestamp"] = lectura["timestamp"].isoformat()
    return jsonify(lectura), 200


@sensors_bp.get("/historial")
def obtener_historial():
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100
    limit = max(1, min(limit, 1000))

    desde = _parsear_fecha(request.args.get("desde"))
    hasta = _parsear_fecha(request.args.get("hasta"))

    lecturas = db.obtener_historial(limit=limit, desde=desde, hasta=hasta)
    return jsonify(serialize_list(lecturas)), 200


@sensors_bp.get("/estadisticas")
def obtener_estadisticas():
    """Mínimo, máximo y promedio por rango"""
    hasta = _parsear_fecha(request.args.get("hasta")) or datetime.now(timezone.utc)
    desde = _parsear_fecha(request.args.get("desde"))
    if desde is None:
        horas = request.args.get("horas", "24")
        try:
            horas = max(1, min(int(horas), 24 * 30))
        except ValueError:
            horas = 24
        desde = hasta - timedelta(hours=horas)

    stats = db.estadisticas_rango(desde, hasta)
    return (
        jsonify(
            {
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "estadisticas": stats,
            }
        ),
        200,
    )


@sensors_bp.get("/estado")
def obtener_estado_conexion():
    estado = serial_reader.get_estado()
    ultima_lectura = serial_reader.get_ultima_lectura()
    if ultima_lectura and isinstance(ultima_lectura.get("timestamp"), datetime):
        ultima_lectura["timestamp"] = ultima_lectura["timestamp"].isoformat()

    return (
        jsonify(
            {
                "serial_conectado": estado["conectado"],
                "puerto": estado["puerto"],
                "ultimo_error": estado["ultimo_error"],
                "mqtt_conectado": mqtt_publisher.estado()["conectado"],
                "base_datos_conectada": db.disponible,
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
    """Se conserva únicamente como respaldo de depuración del backend."""

    def event_generator():
        # Un comentario SSE (linea que empieza con ":") de entrada. Sin esto, si
        # todavia no hay ninguna lectura el cliente se queda sin recibir ni las
        # cabeceras: el navegador nunca dispara onopen y parece que el endpoint
        # esta colgado, cuando en realidad solo no hay datos que mandar.
        yield ": conectado\n\n"

        ultimo_enviado = None
        ultimo_latido = time.monotonic()

        while True:
            lectura = serial_reader.get_ultima_lectura()
            if lectura and lectura != ultimo_enviado:
                ultimo_enviado = lectura
                payload = dict(lectura)
                payload["timestamp"] = str(payload.get("timestamp"))
                yield f"data: {json.dumps(payload)}\n\n"
                ultimo_latido = time.monotonic()
            elif time.monotonic() - ultimo_latido >= HEARTBEAT_SEGUNDOS:
                # Latido periodico: mantiene viva la conexion cuando el nodo
                # esta callado y permite detectar el corte del otro lado.
                yield ": latido\n\n"
                ultimo_latido = time.monotonic()
            time.sleep(1)

    respuesta = Response(event_generator(), mimetype="text/event-stream")
    # Sin esto, un proxy intermedio puede acumular el cuerpo y el streaming
    # deja de ser streaming.
    respuesta.headers["Cache-Control"] = "no-cache"
    respuesta.headers["X-Accel-Buffering"] = "no"
    return respuesta
