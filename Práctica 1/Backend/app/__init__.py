from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config
from app.routes import register_routes
from app.serial_reader import serial_reader


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_routes(app)

    @app.get("/")
    def index():
        return jsonify(
            {
                "proyecto": config.REPORT_PROJECT_NAME,
                "mensaje": "API de SmartEgg activa.",
                "endpoints": [
                    "/api/sensores/actual",
                    "/api/sensores/historial",
                    "/api/sensores/estado",
                    "/api/sensores/alarmas",
                    "/api/sensores/stream",
                    "/api/lotes",
                    "/api/reportes/pdf",
                ],
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"mensaje": "Recurso no encontrado."}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"mensaje": "Error interno del servidor."}), 500

    serial_reader.start()
    return app
