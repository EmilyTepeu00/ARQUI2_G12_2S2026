"""Publicacion de la especificacion OpenAPI + Swagger UI.

  GET /api/openapi.yaml  -> la especificacion tal cual, para Postman/Insomnia
  GET /api/openapi.json  -> la misma especificacion en JSON
  GET /api/docs          -> Swagger UI navegable

Swagger UI se sirve con los archivos que trae flask-swagger-ui, no desde un CDN:
la demo tiene que funcionar sin internet.
"""

import os

import yaml
from flask import Blueprint, Response, jsonify

from src.config import config
from src.logger import get_logger

log = get_logger("api.docs")

RUTA_SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openapi.yaml")
URL_DOCS = "/api/docs"
URL_SPEC_JSON = "/api/openapi.json"

docs_bp = Blueprint("docs", __name__)

_cache = {"spec": None, "mtime": None}


def cargar_spec() -> dict:
    """Lee el YAML y lo recarga solo si cambio en disco."""
    try:
        mtime = os.path.getmtime(RUTA_SPEC)
    except OSError as exc:
        log.error("No se encontró openapi.yaml: %s", exc)
        return {}

    if _cache["spec"] is None or _cache["mtime"] != mtime:
        try:
            with open(RUTA_SPEC, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        except (OSError, yaml.YAMLError) as exc:
            log.error("openapi.yaml no se pudo leer: %s", exc)
            return {}

        # El servidor por defecto sigue el puerto real del backend, sin
        # duplicar el que ya viniera declarado en el YAML.
        spec.setdefault("servers", [])
        url_actual = f"http://localhost:{config.FLASK_PORT}"
        if not any(s.get("url") == url_actual for s in spec["servers"]):
            spec["servers"].insert(
                0,
                {"url": url_actual, "description": "Instancia en ejecución"},
            )
        _cache["spec"] = spec
        _cache["mtime"] = mtime

    return _cache["spec"]


@docs_bp.get("/openapi.json")
def spec_json():
    spec = cargar_spec()
    if not spec:
        return jsonify({"mensaje": "La especificación OpenAPI no está disponible."}), 500
    return jsonify(spec), 200


@docs_bp.get("/openapi.yaml")
def spec_yaml():
    try:
        with open(RUTA_SPEC, encoding="utf-8") as f:
            contenido = f.read()
    except OSError:
        return jsonify({"mensaje": "La especificación OpenAPI no está disponible."}), 500
    return Response(contenido, mimetype="application/yaml")


def registrar_documentacion(app):
    """Monta /api/openapi.* y, si la librería está instalada, /api/docs."""
    app.register_blueprint(docs_bp, url_prefix="/api")

    try:
        from flask_swagger_ui import get_swaggerui_blueprint
    except ImportError:
        log.warning(
            "flask-swagger-ui no está instalado: %s queda sin interfaz. "
            "La especificación sigue disponible en %s",
            URL_DOCS,
            URL_SPEC_JSON,
        )
        return app

    swagger_bp = get_swaggerui_blueprint(
        URL_DOCS,
        URL_SPEC_JSON,
        config={
            "app_name": "SmartEgg API",
            "docExpansion": "none",
            "persistAuthorization": True,
            "displayRequestDuration": True,
        },
    )
    app.register_blueprint(swagger_bp, url_prefix=URL_DOCS)
    log.info("Documentación Swagger publicada en %s", URL_DOCS)
    return app
