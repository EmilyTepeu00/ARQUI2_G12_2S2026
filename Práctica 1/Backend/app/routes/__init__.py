from app.routes.sensors import sensors_bp
from app.routes.lotes import lotes_bp
from app.routes.reports import reports_bp


def register_routes(app):
    app.register_blueprint(sensors_bp, url_prefix="/api/sensores")
    app.register_blueprint(lotes_bp, url_prefix="/api/lotes")
    app.register_blueprint(reports_bp, url_prefix="/api/reportes")
