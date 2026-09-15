from datetime import datetime, timezone
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from src.db import db
from src.reports import generar_reporte_pdf

reports_bp = Blueprint("reports", __name__)


def _parsear_fecha(valor):
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _bool_param(nombre, defecto=False):
    valor = request.args.get(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ("1", "true", "yes", "on", "si", "sí")


def _enviar(pdf_bytes, prefijo="smartegg_reporte"):
    nombre = f"{prefijo}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nombre,
    )


@reports_bp.get("/pdf")
def descargar_reporte_pdf():
    tecnico = request.args.get("tecnico", "No especificado")
    desde = _parsear_fecha(request.args.get("desde"))
    hasta = _parsear_fecha(request.args.get("hasta"))
    detalle = _bool_param("detalle")

    pdf = generar_reporte_pdf(
        tecnico=tecnico,
        desde=desde,
        hasta=hasta,
        incluir_detalle_lecturas=detalle,
    )
    return _enviar(pdf)


@reports_bp.get("/pdf/operador/<id_operador>")
def descargar_reporte_operador(id_operador):
    if db.obtener_operador(id_operador) is None:
        return jsonify({"mensaje": "Operador no encontrado."}), 404

    tecnico = request.args.get("tecnico", "No especificado")
    desde = _parsear_fecha(request.args.get("desde"))
    hasta = _parsear_fecha(request.args.get("hasta"))
    detalle = _bool_param("detalle")

    pdf = generar_reporte_pdf(
        tecnico=tecnico,
        desde=desde,
        hasta=hasta,
        id_operador=id_operador,
        incluir_detalle_lecturas=detalle,
    )
    return _enviar(pdf, prefijo=f"smartegg_reporte_{id_operador}")
