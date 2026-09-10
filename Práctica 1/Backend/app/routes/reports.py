from datetime import datetime, timezone
from io import BytesIO
from flask import Blueprint, request, send_file
from app.reports import generar_reporte_pdf

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/pdf")
def descargar_reporte_pdf():
    tecnico = request.args.get("tecnico", "No especificado")
    pdf_bytes = generar_reporte_pdf(tecnico=tecnico)
    nombre_archivo = (
        f"smartegg_reporte_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    )

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nombre_archivo,
    )
