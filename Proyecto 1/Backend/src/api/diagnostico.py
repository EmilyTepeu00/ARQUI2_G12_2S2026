from flask import Blueprint, jsonify, request

from src.config import config
from src.db import db
from src.mqtt import mqtt_publisher, topics
from src.serial.reader import serial_reader

diagnostico_bp = Blueprint("diagnostico", __name__)


@diagnostico_bp.get("")
def resumen():
    return (
        jsonify(
            {
                "node_id": config.NODE_ID,
                "serial": serial_reader.get_estado(),
                "mqtt": {
                    k: v for k, v in mqtt_publisher.estado().items() if k != "topics"
                },
                "base_datos": db.estado(),
            }
        ),
        200,
    )


@diagnostico_bp.get("/serial")
def estado_serial():
    return (
        jsonify(
            {
                **serial_reader.get_estado(),
                "puertos_disponibles": serial_reader.puertos_disponibles(),
                "ultima_lectura": serial_reader.get_ultima_lectura(),
                "ultimo_evento_puerta": serial_reader.get_ultimo_evento_puerta(),
            }
        ),
        200,
    )


@diagnostico_bp.get("/serial/lineas")
def lineas_crudas():
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    return jsonify(serial_reader.get_lineas_crudas(max(1, min(limit, 30)))), 200


@diagnostico_bp.get("/mqtt")
def estado_mqtt():
    return jsonify(mqtt_publisher.estado()), 200


@diagnostico_bp.get("/mqtt/topics")
def catalogo_topics():
    """Informacion topicos (util para saber cuales son)."""
    return (
        jsonify(
            {
                "prefijo": config.MQTT_TOPIC_PREFIX,
                "node_id": config.NODE_ID,
                "broker_websocket": f"ws://{config.MQTT_HOST}:9001",
                "topics": topics.documentar(),
            }
        ),
        200,
    )
