import atexit

from flask import Flask, jsonify
from flask_cors import CORS

from src import auth
from src.api import register_routes
from src.api.docs import registrar_documentacion
from src.config import config
from src.logger import get_logger
from src.mqtt import init as mqtt_init
from src.mqtt import stop as mqtt_stop
from src.serial import init as serial_init
from src.serial import stop as serial_stop

log = get_logger("app")


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_routes(app)
    auth.init(app)
    registrar_documentacion(app)

    @app.get("/")
    def index():
        return jsonify(
            {
                "proyecto": config.REPORT_PROJECT_NAME,
                "mensaje": "API de SmartEgg activa.",
                "node_id": config.NODE_ID,
                "documentacion": "/api/docs",
                "openapi": "/api/openapi.yaml",
                "endpoints": [
                    "/api/auth/login",
                    "/api/auth/yo",
                    "/api/auth/usuarios",
                    "/api/perfil",
                    "/api/perfil/diagnosticos",
                    "/api/perfil/informes",
                    "/api/perfil/reporte.pdf",
                    "/api/sensores/actual",
                    "/api/sensores/historial",
                    "/api/sensores/estadisticas",
                    "/api/sensores/estado",
                    "/api/sensores/alarmas",
                    "/api/sensores/stream",
                    "/api/lotes",
                    "/api/operadores",
                    "/api/puerta/eventos",
                    "/api/puerta/resumen",
                    "/api/reportes/pdf",
                    "/api/reportes/pdf/operador/<id_operador>",
                    "/api/diagnostico",
                    "/api/diagnostico/mqtt/topics",
                ],
            }
        )

    @app.get("/health")
    def health():
        from src.db import db
        from src.mqtt import mqtt_publisher
        from src.serial.reader import serial_reader

        estado = {
            "backend": "ok",
            "serial": serial_reader.get_estado()["conectado"],
            "mqtt": mqtt_publisher.estado()["conectado"],
            "base_datos": db.disponible,
        }
        return jsonify(estado), 200

    @app.errorhandler(401)
    def no_autenticado(_error):
        return jsonify({"mensaje": "No autenticado."}), 401

    @app.errorhandler(403)
    def sin_permisos(_error):
        return jsonify({"mensaje": "No tiene permisos para esta operación."}), 403

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"mensaje": "Recurso no encontrado."}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"mensaje": "Error interno del servidor."}), 500

    # Componentes de fondo
    mqtt_init()
    serial_init()

    atexit.register(_apagar)
    log.info("Backend SmartEgg listo (nodo %s).", config.NODE_ID)
    return app


def _apagar():
    log.info("Apagando componentes de fondo...")
    serial_stop()
    mqtt_stop()
