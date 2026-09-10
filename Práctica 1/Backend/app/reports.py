import io
import os
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from app.config import config
from app.database import db

LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "logo.png")


def _calcular_temp_hum_extremos(lecturas: list):
    if not lecturas:
        return None
    temps = [l["temperatura"] for l in lecturas if "temperatura" in l]
    hums = [l["humedad"] for l in lecturas if "humedad" in l]
    if not temps or not hums:
        return None
    return {
        "temp_max": max(temps),
        "temp_min": min(temps),
        "hum_max": max(hums),
        "hum_min": min(hums),
        "lecturas_totales": len(lecturas),
    }


def generar_reporte_pdf(tecnico: str = "No especificado") -> bytes:
    hoy = datetime.now(timezone.utc)
    lecturas_del_dia = db.obtener_lecturas_del_dia(hoy)
    alarmas_del_dia = db.obtener_alarmas_del_dia(hoy)
    lotes = db.listar_lotes()
    extremos = _calcular_temp_hum_extremos(lecturas_del_dia)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleSmartEgg", parent=styles["Title"], fontSize=18, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey
    )
    heading_style = ParagraphStyle(
        "HeadingSmartEgg",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#1F4E79"),
    )
    normal_style = styles["Normal"]

    elementos = []

    if os.path.exists(LOGO_PATH):
        try:
            elementos.append(Image(LOGO_PATH, width=3 * cm, height=3 * cm))
            elementos.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass

    elementos.append(Paragraph(config.REPORT_PROJECT_NAME, title_style))
    elementos.append(Paragraph(config.REPORT_FACULTY_NAME, subtitle_style))
    elementos.append(
        Paragraph(
            f"Reporte generado el {hoy.strftime('%d/%m/%Y %H:%M UTC')}", subtitle_style
        )
    )
    elementos.append(Spacer(1, 0.4 * cm))

    elementos.append(Paragraph("Técnico responsable", heading_style))
    elementos.append(Paragraph(f"Nombre: {tecnico}", normal_style))
    elementos.append(
        Paragraph(f"Fecha del reporte: {hoy.strftime('%d/%m/%Y')}", normal_style)
    )

    elementos.append(Paragraph("Resumen de lotes actuales", heading_style))
    if lotes:
        data = [["Código", "Nombre del lote", "Huevos", "Estado", "Fecha ingreso"]]
        for lote in lotes:
            fecha = lote.get("fecha_ingreso")
            fecha_str = (
                fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else "-"
            )
            data.append(
                [
                    str(lote.get("codigo", "-")),
                    str(lote.get("nombre_lote", "-")),
                    str(lote.get("cantidad_huevos", "-")),
                    str(lote.get("estado", "-")),
                    fecha_str,
                ]
            )

        tabla = Table(
            data, hAlign="LEFT", colWidths=[3 * cm, 5 * cm, 2 * cm, 3 * cm, 3.2 * cm]
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.white],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elementos.append(tabla)
    else:
        elementos.append(Paragraph("No hay lotes registrados.", normal_style))

    elementos.append(
        Paragraph("Historial de temperatura y humedad del día", heading_style)
    )
    if extremos:
        data = [
            ["Métrica", "Máximo", "Mínimo"],
            [
                "Temperatura (°C)",
                f"{extremos['temp_max']:.2f}",
                f"{extremos['temp_min']:.2f}",
            ],
            ["Humedad (%)", f"{extremos['hum_max']:.2f}", f"{extremos['hum_min']:.2f}"],
        ]
        tabla = Table(data, hAlign="LEFT", colWidths=[6 * cm, 4 * cm, 4 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elementos.append(tabla)
        elementos.append(
            Paragraph(
                f"Total de lecturas registradas hoy: {extremos['lecturas_totales']}",
                normal_style,
            )
        )
    else:
        elementos.append(
            Paragraph(
                "Aún no se han registrado lecturas de sensores hoy.", normal_style
            )
        )

    elementos.append(Paragraph("Registro de alarmas del día", heading_style))
    if alarmas_del_dia:
        data = [["Hora", "Mensaje"]]
        for alarma in alarmas_del_dia:
            ts = alarma.get("timestamp")
            hora = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else "-"
            data.append([hora, alarma.get("mensaje", "Alarma activada")])

        tabla = Table(data, hAlign="LEFT", colWidths=[3 * cm, 11 * cm])
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C0392B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.whitesmoke, colors.white],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elementos.append(tabla)
    else:
        elementos.append(
            Paragraph("No se registraron alarmas durante el día.", normal_style)
        )

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
