from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from src.config import config
from src.db import db
from src.logger import get_logger
from src.models import EventoPuerta, serialize_doc, serialize_list
from src.mqtt import mqtt_publisher

puerta_bp = Blueprint("puerta", __name__)
log = get_logger("api.puerta")


def _parsear_fecha(valor):
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _rango_por_defecto():
    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=7)
    return desde, hasta


@puerta_bp.get("/eventos")
def listar_eventos():
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100
    limit = max(1, min(limit, 500))

    desde = _parsear_fecha(request.args.get("desde"))
    hasta = _parsear_fecha(request.args.get("hasta"))
    id_operador = request.args.get("id_operador")

    eventos = db.listar_aperturas(
        limit=limit, id_operador=id_operador, desde=desde, hasta=hasta
    )
    return jsonify(serialize_list(eventos)), 200


@puerta_bp.get("/resumen")
def resumen_puerta():
    """Conteo de veces abierta/cerrada y saldo de huevos"""
    desde = _parsear_fecha(request.args.get("desde"))
    hasta = _parsear_fecha(request.args.get("hasta"))
    if desde is None or hasta is None:
        por_defecto = _rango_por_defecto()
        desde = desde or por_defecto[0]
        hasta = hasta or por_defecto[1]

    id_operador = request.args.get("id_operador")
    resumen = db.resumen_puerta(desde, hasta, id_operador=id_operador)
    resumen["desde"] = desde.isoformat()
    resumen["hasta"] = hasta.isoformat()
    return jsonify(resumen), 200


@puerta_bp.post("/eventos")
def registrar_evento():
    """Registro manual de un evento de puerta"""
    data = request.get_json(silent=True) or {}
    errores = EventoPuerta.validar(data)
    if errores:
        return jsonify({"errores": errores}), 400

    id_operador = str(data.get("id_operador")).strip()
    operador = db.obtener_operador(id_operador)
    autorizado = bool(operador and operador.get("activo", True))

    evento = EventoPuerta.build({**data, "autorizado": autorizado}, node_id=config.NODE_ID)
    evento["origen"] = "api"
    evento["timestamp"] = datetime.now(timezone.utc)

    guardado = db.registrar_apertura(dict(evento))
    if guardado is None:
        return jsonify({"mensaje": "Base de datos no disponible."}), 503

    mqtt_publisher.publicar_evento_puerta(
        {
            "accion": evento["accion"],
            "id_operador": evento["id_operador"],
            "metodo": evento["metodo"],
            "huevos_delta": evento["huevos_delta"],
            "autorizado": autorizado,
        }
    )
    log.info(
        "Evento de puerta registrado por API: %s / %s (autorizado=%s)",
        evento["accion"],
        evento["id_operador"],
        autorizado,
    )

    codigo = 201 if autorizado else 202
    return jsonify(serialize_doc(guardado)), codigo
