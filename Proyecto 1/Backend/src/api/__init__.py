from src.api.diagnostico import diagnostico_bp
from src.api.historico import historico_bp
from src.api.lotes import lotes_bp
from src.api.operadores import operadores_bp
from src.api.puerta import puerta_bp
from src.api.reports import reports_bp
from src.api.sensors import sensors_bp


def register_routes(app):
    app.register_blueprint(sensors_bp, url_prefix="/api/sensores")
    app.register_blueprint(lotes_bp, url_prefix="/api/lotes")
    app.register_blueprint(reports_bp, url_prefix="/api/reportes")
    app.register_blueprint(operadores_bp, url_prefix="/api/operadores")
    app.register_blueprint(puerta_bp, url_prefix="/api/puerta")
    app.register_blueprint(diagnostico_bp, url_prefix="/api/diagnostico")
    app.register_blueprint(historico_bp, url_prefix="/api/historico")
