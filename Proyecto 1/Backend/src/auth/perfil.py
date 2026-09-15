"""Perfil por operador: /api/perfil/*

Cada operador ve unicamente sus propios diagnosticos e informes; el
administrador puede consultar los de cualquiera con ?id_operador=.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from src.auth.decorators import (
    es_admin,
    id_operador_actual,
    requiere_auth,
    resolver_id_operador,
    usuario_actual,
)
from src.db import db
from src.models import serialize_doc, serialize_list
from src.reports import generar_reporte_pdf
from src.serial.reader import serial_reader

perfil_bp = Blueprint("perfil", __name__)


def _parsear_fecha(valor):
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _rango(defecto_dias=7):
    """Rango de consulta: ?desde/?hasta ISO-8601, o los ultimos N dias."""
    hasta = _parsear_fecha(request.args.get("hasta")) or datetime.now(timezone.utc)
    desde = _parsear_fecha(request.args.get("desde"))
    if desde is None:
        try:
            dias = max(1, min(int(request.args.get("dias", defecto_dias)), 365))
        except ValueError:
            dias = defecto_dias
        desde = hasta - timedelta(days=dias)
    return desde, hasta


@perfil_bp.get("")
@requiere_auth
def mi_perfil():
    """Usuario del token junto con su ficha de operador, si tiene."""
    actual = usuario_actual()
    id_operador = id_operador_actual()

    ficha = None
    if id_operador:
        ficha = serialize_doc(db.obtener_operador(id_operador))

    return (
        jsonify(
            {
                "usuario": {
                    "username": actual.get("username"),
                    "nombre": actual.get("nombre", ""),
                    "rol": actual.get("rol"),
                    "id_operador": id_operador,
                },
                "es_administrador": es_admin(),
                "operador": ficha,
                "permisos": {
                    "ver_todos_los_operadores": es_admin(),
                    "administrar_usuarios": es_admin(),
                    "administrar_operadores": es_admin(),
                },
            }
        ),
        200,
    )


@perfil_bp.get("/diagnosticos")
@requiere_auth
def mis_diagnosticos():
    """Aperturas/cierres del operador y estado actual del nodo."""
    id_operador = resolver_id_operador(request.args.get("id_operador"))
    desde, hasta = _rango()

    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
    except ValueError:
        limit = 100

    eventos = db.listar_aperturas(
        limit=limit, id_operador=id_operador, desde=desde, hasta=hasta
    )
    resumen = db.resumen_puerta(desde, hasta, id_operador=id_operador)

    ultima = serial_reader.get_ultima_lectura()
    if ultima and isinstance(ultima.get("timestamp"), datetime):
        ultima["timestamp"] = ultima["timestamp"].isoformat()

    return (
        jsonify(
            {
                "id_operador": id_operador,
                "alcance": "todos" if id_operador is None else "propio",
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "resumen_puerta": resumen,
                "eventos": serialize_list(eventos),
                "estado_nodo_actual": ultima,
            }
        ),
        200,
    )


@perfil_bp.get("/informes")
@requiere_auth
def mis_informes():
    """Informe en JSON: estadisticas del rango, alarmas y actividad de puerta."""
    id_operador = resolver_id_operador(request.args.get("id_operador"))
    desde, hasta = _rango()

    estadisticas = db.estadisticas_rango(desde, hasta)
    alarmas = db.obtener_alarmas_rango(desde, hasta)
    resumen = db.resumen_puerta(desde, hasta, id_operador=id_operador)

    return (
        jsonify(
            {
                "id_operador": id_operador,
                "alcance": "todos" if id_operador is None else "propio",
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "estadisticas_ambientales": estadisticas,
                "alarmas": serialize_list(alarmas),
                "total_alarmas": len(alarmas),
                "actividad_puerta": resumen,
                "descarga_pdf": "/api/perfil/reporte.pdf",
            }
        ),
        200,
    )


@perfil_bp.get("/reporte.pdf")
@requiere_auth
def mi_reporte_pdf():
    """Mismo informe en PDF, filtrado al operador del token."""
    id_operador = resolver_id_operador(request.args.get("id_operador"))
    desde, hasta = _rango()
    detalle = str(request.args.get("detalle", "")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "si",
        "sí",
    )

    actual = usuario_actual()
    pdf = generar_reporte_pdf(
        tecnico=actual.get("nombre") or actual.get("username") or "No especificado",
        desde=desde,
        hasta=hasta,
        id_operador=id_operador,
        incluir_detalle_lecturas=detalle,
    )

    etiqueta = id_operador or "general"
    nombre = (
        f"smartegg_reporte_{etiqueta}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    )
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nombre,
    )
