"""Guardia global de autorizacion.

Aplica las reglas de acceso desde un unico before_request en vez de decorar
cada endpoint. Asi no hay que tocar los blueprints de src/api/ y todas las
reglas quedan visibles en un solo lugar.

Regla: lo que alimenta dashboards y visualizaciones (telemetria de solo
lectura) queda publico para que Grafana, p5.js y Chart.js consuman datos
reales sin fricción; todo lo que ESCRIBE o expone datos por operador exige
token.
"""

import re

from flask import jsonify, request

from src.auth.decorators import autenticar_peticion, puede_ver_operador, usuario_actual
from src.auth.repository import ROL_ADMIN
from src.config import config
from src.logger import get_logger

log = get_logger("auth.guard")

ESCRITURAS = {"POST", "PUT", "PATCH", "DELETE"}

# Rutas siempre abiertas, sin token.
PUBLICOS_EXACTOS = {
    "/",
    "/health",
    "/api/auth/login",
    "/api/openapi.json",
    "/api/openapi.yaml",
    "/api/diagnostico/mqtt/topics",
}

PUBLICOS_PREFIJOS = (
    "/api/docs",       # Swagger UI y sus estaticos
    "/static",
    "/favicon",
)

# (patron, metodos, requisito). Gana la primera que coincida.
#   auth   -> cualquier usuario autenticado
#   admin  -> solo rol administrador
#   propio -> administrador, o el operador dueño del id_operador de la ruta
REGLAS = (
    (re.compile(r"^/api/operadores(/.*)?$"), ESCRITURAS, "admin"),
    (re.compile(r"^/api/operadores(/.*)?$"), {"GET"}, "auth"),
    (re.compile(r"^/api/lotes(/.*)?$"), ESCRITURAS, "auth"),
    (re.compile(r"^/api/puerta(/.*)?$"), ESCRITURAS, "auth"),
    (
        re.compile(r"^/api/reportes/pdf/operador/(?P<id_operador>[^/]+)$"),
        {"GET"},
        "propio",
    ),
    (re.compile(r"^/api/diagnostico(/.*)?$"), {"GET"}, "auth"),
)


def _es_publico(path: str) -> bool:
    if path in PUBLICOS_EXACTOS:
        return True
    return path.startswith(PUBLICOS_PREFIJOS)


def _aplicar(requisito: str, coincidencia):
    error = autenticar_peticion()
    if error is not None:
        return error

    if requisito == "admin" and usuario_actual().get("rol") != ROL_ADMIN:
        return (
            jsonify(
                {
                    "mensaje": "Solo el administrador puede realizar esta operación.",
                    "rol_actual": usuario_actual().get("rol"),
                }
            ),
            403,
        )

    if requisito == "propio":
        objetivo = coincidencia.groupdict().get("id_operador")
        if objetivo and not puede_ver_operador(objetivo):
            log.warning(
                "'%s' intentó ver datos del operador %s.",
                usuario_actual().get("username"),
                objetivo,
            )
            return (
                jsonify(
                    {
                        "mensaje": "Solo puede consultar sus propios informes.",
                        "id_operador_solicitado": objetivo,
                        "id_operador_propio": usuario_actual().get("id_operador"),
                    }
                ),
                403,
            )

    return None


def proteger_app(app):
    @app.before_request
    def _guardia():
        if not config.AUTH_ENABLED:
            return None
        if request.method == "OPTIONS":   # preflight de CORS
            return None

        path = request.path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        if _es_publico(path):
            return None

        for patron, metodos, requisito in REGLAS:
            coincidencia = patron.match(path)
            if coincidencia and request.method in metodos:
                return _aplicar(requisito, coincidencia)

        return None

    if config.AUTH_ENABLED:
        log.info("Guardia de autorización activo (%d reglas).", len(REGLAS))
    else:
        log.warning("AUTH_ENABLED=false: la API está completamente abierta.")

    return app
