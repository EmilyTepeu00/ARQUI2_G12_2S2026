import io
import os
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import config
from src.db import db
from src.logger import get_logger

log = get_logger("reports")

LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "logo.png")

# Paleta
AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#E8F0F8")
AZUL_MEDIO = colors.HexColor("#3A78B5")
ROJO = colors.HexColor("#C0392B")
ROJO_CLARO = colors.HexColor("#FBEAE7")
VERDE = colors.HexColor("#1E8449")
AMBAR = colors.HexColor("#B9770E")
GRIS = colors.HexColor("#6B7280")
GRIS_CLARO = colors.HexColor("#F4F6F8")
GRIS_LINEA = colors.HexColor("#D5DBE1")

# Limite de caracteres por celda
MAX_CARACTERES_CELDA = 600


# Utilidades de texto
def _escapar(texto) -> str:
    """Escapa el mini-HTML que interpreta Paragraph."""
    if texto is None:
        return "-"
    texto = str(texto)
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _texto_celda(valor, largo_max: int = MAX_CARACTERES_CELDA) -> str:
    """Prepara el contenido de una celda."""
    texto = _escapar(valor)
    if len(texto) > largo_max:
        texto = texto[: largo_max - 1].rstrip() + "…"
    return texto


def _fmt_fecha(valor, formato="%d/%m/%Y %H:%M"):
    if isinstance(valor, datetime):
        return valor.strftime(formato)
    return "-"


def _fmt_num(valor, decimales=2, sufijo=""):
    if valor is None:
        return "-"
    try:
        return f"{float(valor):.{decimales}f}{sufijo}"
    except (TypeError, ValueError):
        return str(valor)


def _fmt_duracion(segundos):
    if segundos is None:
        return "En curso"
    try:
        segundos = float(segundos)
    except (TypeError, ValueError):
        return "-"
    if segundos < 60:
        return f"{segundos:.0f} s"
    minutos, seg = divmod(int(segundos), 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas} h {minutos} min"
    return f"{minutos} min {seg} s"


# Estilos
def _construir_estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloSmartEgg",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "subtitulo_portada": ParagraphStyle(
            "SubtituloPortada",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#D6E4F0"),
            alignment=TA_LEFT,
        ),
        "seccion": ParagraphStyle(
            "SeccionSmartEgg",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=AZUL,
            spaceBefore=16,
            spaceAfter=2,
        ),
        "normal": ParagraphStyle(
            "NormalSmartEgg",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
        ),
        "nota": ParagraphStyle(
            "NotaSmartEgg",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=GRIS,
        ),
        "th": ParagraphStyle(
            "CeldaCabecera",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
            alignment=TA_LEFT,
            splitLongWords=1,
        ),
        "td": ParagraphStyle(
            "CeldaCuerpo",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1F2933"),
            alignment=TA_LEFT,
            splitLongWords=1,
        ),
        "td_num": ParagraphStyle(
            "CeldaNumero",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1F2933"),
            alignment=TA_RIGHT,
            splitLongWords=1,
        ),
        "kpi_valor": ParagraphStyle(
            "KpiValor",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=AZUL,
            alignment=TA_CENTER,
        ),
        "kpi_etiqueta": ParagraphStyle(
            "KpiEtiqueta",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=GRIS,
            alignment=TA_CENTER,
        ),
    }

def _anchos_columna(encabezados, proporciones, ancho_disponible, fuente="Helvetica-Bold", tam=8.5, padding=14):
    minimos = [stringWidth(h, fuente, tam) + padding for h in encabezados]
    total_prop = sum(proporciones) or 1
    anchos = [ancho_disponible * (p / total_prop) for p in proporciones]

    faltante = 0
    ajustables = []
    for i, (a, m) in enumerate(zip(anchos, minimos)):
        if a < m:
            faltante += m - a
            anchos[i] = m
        else:
            ajustables.append(i)

    if faltante and ajustables:
        total_ajustable = sum(anchos[i] for i in ajustables)
        for i in ajustables:
            anchos[i] -= faltante * (anchos[i] / total_ajustable)

    return anchos

# Tablas
def _tabla(
    encabezados,
    filas,
    ancho_disponible,
    proporciones,
    estilos,
    color_cabecera=AZUL,
    columnas_numericas=(),
):
    """Construye una tabla"""
    col_widths = _anchos_columna(encabezados, proporciones, ancho_disponible)
    
    data = [[Paragraph(_texto_celda(h), estilos["th"]) for h in encabezados]]
    for fila in filas:
        celda_fila = []
        for indice, valor in enumerate(fila):
            estilo = (
                estilos["td_num"] if indice in columnas_numericas else estilos["td"]
            )
            celda_fila.append(Paragraph(_texto_celda(valor), estilo))
        data.append(celda_fila)

    tabla = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), color_cabecera),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, GRIS_LINEA),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_LINEA),
                ("LINEAFTER", (0, 0), (-2, -1), 0.4, GRIS_LINEA),
            ]
        )
    )
    return tabla


def _tarjetas_kpi(items, ancho_disponible, estilos):
    """Fila de indicadores tipo tarjeta."""
    if not items:
        return Spacer(1, 0)

    celdas = []
    for etiqueta, valor in items:
        celdas.append(
            [
                Paragraph(_texto_celda(valor, 40), estilos["kpi_valor"]),
                Paragraph(_texto_celda(etiqueta, 60), estilos["kpi_etiqueta"]),
            ]
        )

    ancho_col = ancho_disponible / len(items)
    interiores = []
    for contenido in celdas:
        t = Table([[contenido[0]], [contenido[1]]], colWidths=[ancho_col - 0.25 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), AZUL_CLARO),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C3D6E8")),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        interiores.append(t)

    contenedor = Table([interiores], colWidths=[ancho_col] * len(items), hAlign="LEFT")
    contenedor.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return contenedor


def _titulo_seccion(texto, ancho, estilos):
    """Título con regla de color debajo, en un solo bloque inseparable."""
    regla = Table([[""]], colWidths=[ancho], rowHeights=[2])
    regla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL_MEDIO),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return KeepTogether(
        [Paragraph(_escapar(texto), estilos["seccion"]), regla, Spacer(1, 0.25 * cm)]
    )


# Numeración
class _CanvasNumerado(pdfcanvas.Canvas):
    """Guarda el estado de cada página para poder escribir 'Página X de Y'"""

    def __init__(self, *args, **kwargs):
        self._pie_texto = kwargs.pop("pie_texto", "")
        super().__init__(*args, **kwargs)
        self._paginas_guardadas = []

    def showPage(self):
        self._paginas_guardadas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas_guardadas)
        pie = self._pie_texto
        for numero, estado in enumerate(self._paginas_guardadas, start=1):
            self.__dict__.update(estado)
            self._pie_texto = pie
            self._dibujar_pie(numero, total)
            super().showPage()
        super().save()

    def _dibujar_pie(self, numero, total):
        ancho, _ = self._pagesize
        self.saveState()
        self.setStrokeColor(GRIS_LINEA)
        self.setLineWidth(0.5)
        self.line(1.8 * cm, 1.15 * cm, ancho - 1.8 * cm, 1.15 * cm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRIS)
        self.drawString(1.8 * cm, 0.78 * cm, self._pie_texto[:120])
        self.drawRightString(ancho - 1.8 * cm, 0.78 * cm, f"Página {numero} de {total}")
        self.restoreState()


# Encabezado
def _bloque_portada(ancho, estilos, titulo, subtitulo, meta_lineas):
    izquierda = [
        Paragraph(_escapar(titulo), estilos["titulo"]),
        Paragraph(_escapar(subtitulo), estilos["subtitulo_portada"]),
        Spacer(1, 0.15 * cm),
    ]
    for linea in meta_lineas:
        izquierda.append(Paragraph(_escapar(linea), estilos["subtitulo_portada"]))

    columna_izq = Table([[c] for c in izquierda], colWidths=[ancho * 0.78])
    columna_izq.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    logo = ""
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image(LOGO_PATH, width=2.1 * cm, height=2.1 * cm)
        except Exception as exc:
            log.warning("No se pudo cargar el logo del reporte: %s", exc)
            logo = ""

    banda = Table([[columna_izq, logo]], colWidths=[ancho * 0.78, ancho * 0.22])
    banda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL),
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return banda


# Recolección de datos
def _resolver_rango(desde=None, hasta=None):
    ahora = datetime.now(timezone.utc)
    if hasta is None:
        hasta = ahora
    if desde is None:
        desde = hasta.replace(hour=0, minute=0, second=0, microsecond=0)
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def recolectar_datos(desde=None, hasta=None, id_operador=None):
    """Reúne todo lo que necesita el PDF"""
    desde, hasta = _resolver_rango(desde, hasta)

    lecturas = db.obtener_lecturas_rango(desde, hasta)
    alarmas = db.obtener_alarmas_rango(desde, hasta)
    lotes = db.listar_lotes()
    operadores = db.listar_operadores()
    aperturas = db.listar_aperturas(
        limit=500, id_operador=id_operador, desde=desde, hasta=hasta
    )
    resumen_puerta = db.resumen_puerta(desde, hasta, id_operador=id_operador)
    stats = db.estadisticas_rango(desde, hasta)

    if stats is None and lecturas:
        temps = [l["temperatura"] for l in lecturas if l.get("temperatura") is not None]
        hums = [l["humedad"] for l in lecturas if l.get("humedad") is not None]
        if temps and hums:
            stats = {
                "temp_min": min(temps),
                "temp_max": max(temps),
                "temp_prom": sum(temps) / len(temps),
                "hum_min": min(hums),
                "hum_max": max(hums),
                "hum_prom": sum(hums) / len(hums),
                "lecturas_totales": len(lecturas),
            }

    return {
        "desde": desde,
        "hasta": hasta,
        "lecturas": lecturas,
        "alarmas": alarmas,
        "lotes": lotes,
        "operadores": operadores,
        "aperturas": aperturas,
        "resumen_puerta": resumen_puerta,
        "estadisticas": stats,
        "id_operador": id_operador,
    }


# Generación reportse
def generar_reporte_pdf(
    tecnico: str = "No especificado",
    desde: datetime = None,
    hasta: datetime = None,
    id_operador: str = None,
    incluir_detalle_lecturas: bool = False,
) -> bytes:
    """Reporte general o por operador"""
    datos = recolectar_datos(desde, hasta, id_operador)
    estilos = _construir_estilos()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.4 * cm,
        bottomMargin=1.7 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title="Reporte SmartEgg",
        author=config.REPORT_PROJECT_NAME,
    )
    ancho = doc.width

    operador_doc = None
    if id_operador:
        operador_doc = next(
            (o for o in datos["operadores"] if o.get("id_operador") == id_operador),
            None,
        )

    titulo = "Reporte de operación"
    if id_operador:
        nombre = operador_doc.get("nombre") if operador_doc else id_operador
        titulo = f"Reporte por operador · {nombre}"

    meta = [
        f"Periodo: {_fmt_fecha(datos['desde'])} — {_fmt_fecha(datos['hasta'])} "
        f"({config.REPORT_TIMEZONE_LABEL})",
        f"Técnico responsable: {tecnico}",
        f"Nodo: {config.NODE_ID}",
    ]

    elementos = [
        _bloque_portada(
            ancho,
            estilos,
            config.REPORT_PROJECT_NAME,
            config.REPORT_FACULTY_NAME,
            [titulo] + meta,
        ),
        Spacer(1, 0.55 * cm),
    ]

    # Indicadores
    stats = datos["estadisticas"]
    resumen = datos["resumen_puerta"]
    kpis = [
        ("Lecturas registradas", stats["lecturas_totales"] if stats else 0),
        (
            "Temp. promedio",
            _fmt_num(stats["temp_prom"], 1, " °C") if stats else "-",
        ),
        ("Hum. promedio", _fmt_num(stats["hum_prom"], 1, " %") if stats else "-"),
        ("Alarmas del periodo", len(datos["alarmas"])),
        ("Aperturas de puerta", resumen["veces_abierta"]),
    ]
    elementos.append(_tarjetas_kpi(kpis, ancho, estilos))

    # Estadísticas de temperatura y humedad
    elementos.append(
        _titulo_seccion("Temperatura y humedad del periodo", ancho, estilos)
    )
    if stats:
        filas = [
            [
                "Temperatura (°C)",
                _fmt_num(stats["temp_min"]),
                _fmt_num(stats["temp_prom"]),
                _fmt_num(stats["temp_max"]),
                f"{_fmt_num(config.TEMP_MIN, 1)} – {_fmt_num(config.TEMP_MAX, 1)}",
            ],
            [
                "Humedad (%)",
                _fmt_num(stats["hum_min"]),
                _fmt_num(stats["hum_prom"]),
                _fmt_num(stats["hum_max"]),
                f"{_fmt_num(config.HUM_MIN, 1)} – {_fmt_num(config.HUM_MAX, 1)}",
            ],
        ]
        elementos.append(
            _tabla(
                ["Métrica", "Mínimo", "Promedio", "Máximo", "Umbral configurado"],
                filas,
                ancho,
                [0.30, 0.15, 0.15, 0.15, 0.25],
                estilos,
                columnas_numericas=(1, 2, 3),
            )
        )
        elementos.append(Spacer(1, 0.2 * cm))
        elementos.append(
            Paragraph(
                f"Total de lecturas en el periodo: {stats['lecturas_totales']}.",
                estilos["nota"],
            )
        )
    else:
        elementos.append(
            Paragraph("No hay lecturas de sensores en el periodo.", estilos["normal"])
        )

    # Lotes
    elementos.append(_titulo_seccion("Lotes registrados", ancho, estilos))
    if datos["lotes"]:
        filas = [
            [
                lote.get("codigo", "-"),
                lote.get("nombre_lote", "-"),
                lote.get("cantidad_huevos", "-"),
                lote.get("raza", "-") or "-",
                lote.get("estado", "-"),
                _fmt_fecha(lote.get("fecha_ingreso"), "%d/%m/%Y"),
                lote.get("observaciones", "") or "-",
            ]
            for lote in datos["lotes"]
        ]
        elementos.append(
            _tabla(
                [
                    "Código",
                    "Nombre del lote",
                    "Huevos",
                    "Raza",
                    "Estado",
                    "Ingreso",
                    "Observaciones",
                ],
                filas,
                ancho,
                [0.13, 0.17, 0.10, 0.12, 0.11, 0.11, 0.26],
                estilos,
                columnas_numericas=(2,),
            )
        )
    else:
        elementos.append(Paragraph("No hay lotes registrados.", estilos["normal"]))

    # Control de acceso resumen
    elementos.append(
        _titulo_seccion("Control de acceso a la incubadora", ancho, estilos)
    )
    elementos.append(
        _tarjetas_kpi(
            [
                ("Veces abierta", resumen["veces_abierta"]),
                ("Veces cerrada", resumen["veces_cerrada"]),
                ("Huevos ingresados", resumen["huevos_ingresados"]),
                ("Huevos retirados", resumen["huevos_retirados"]),
            ],
            ancho,
            estilos,
        )
    )
    elementos.append(Spacer(1, 0.35 * cm))

    if resumen["por_operador"]:
        nombres = {
            o.get("id_operador"): o.get("nombre", "") for o in datos["operadores"]
        }
        filas = [
            [
                item["id_operador"],
                nombres.get(item["id_operador"], "No registrado"),
                item["veces_abierta"],
                item["veces_cerrada"],
                item["huevos_ingresados"],
                item["huevos_retirados"],
            ]
            for item in resumen["por_operador"]
        ]
        elementos.append(
            _tabla(
                [
                    "ID operador",
                    "Nombre",
                    "Aperturas",
                    "Cierres",
                    "Huevos ingresados",
                    "Huevos retirados",
                ],
                filas,
                ancho,
                [0.14, 0.28, 0.13, 0.13, 0.16, 0.16],
                estilos,
                columnas_numericas=(2, 3, 4, 5),
            )
        )
    else:
        elementos.append(
            Paragraph(
                "No se registraron eventos de puerta en el periodo.", estilos["normal"]
            )
        )

    # Control de acceso detalle
    if datos["aperturas"]:
        elementos.append(
            _titulo_seccion("Detalle de eventos de puerta", ancho, estilos)
        )
        filas = [
            [
                _fmt_fecha(ev.get("timestamp"), "%d/%m/%Y"),
                _fmt_fecha(ev.get("timestamp"), "%H:%M:%S"),
                ev.get("id_operador", "-"),
                (ev.get("accion", "-") or "-").capitalize(),
                (ev.get("metodo", "-") or "-").upper(),
                ev.get("huevos_delta", 0),
                "Sí" if ev.get("autorizado", True) else "No",
                ev.get("observaciones", "") or "-",
            ]
            for ev in datos["aperturas"][:200]
        ]
        elementos.append(
            _tabla(
                [
                    "Fecha",
                    "Hora",
                    "Operador",
                    "Acción",
                    "Método",
                    "Huevos",
                    "Autoriz.",
                    "Observaciones",
                ],
                filas,
                ancho,
                [0.12, 0.09, 0.10, 0.09, 0.09, 0.09, 0.10, 0.32],
                estilos,
                columnas_numericas=(5,),
            )
        )
        elementos.append(Spacer(1, 0.15 * cm))
        elementos.append(
            Paragraph(
                "En la columna «Huevos», los valores positivos indican huevos "
                "ingresados y los negativos, huevos retirados.",
                estilos["nota"],
            )
        )
        if len(datos["aperturas"]) > 200:
            elementos.append(Spacer(1, 0.15 * cm))
            elementos.append(
                Paragraph(
                    f"Se muestran los 200 eventos más recientes de "
                    f"{len(datos['aperturas'])} registrados en el periodo.",
                    estilos["nota"],
                )
            )

    # Alarmas
    elementos.append(_titulo_seccion("Historial de alarmas", ancho, estilos))
    if datos["alarmas"]:
        filas = []
        for alarma in datos["alarmas"][:200]:
            inicio = alarma.get("inicio") or alarma.get("timestamp")
            filas.append(
                [
                    _fmt_fecha(inicio, "%d/%m/%Y %H:%M:%S"),
                    (
                        _fmt_fecha(alarma.get("fin"), "%H:%M:%S")
                        if alarma.get("fin")
                        else "En curso"
                    ),
                    _fmt_duracion(alarma.get("duracion_segundos")),
                    (alarma.get("severidad", "-") or "-").capitalize(),
                    _fmt_num(alarma.get("temperatura"), 1, " °C"),
                    _fmt_num(alarma.get("humedad"), 1, " %"),
                    alarma.get("mensaje", "Alarma activada"),
                ]
            )
        elementos.append(
            _tabla(
                [
                    "Inicio",
                    "Fin",
                    "Duración",
                    "Severidad",
                    "Temp.",
                    "Hum.",
                    "Descripción",
                ],
                filas,
                ancho,
                [0.15, 0.09, 0.10, 0.13, 0.08, 0.08, 0.37],
                estilos,
                color_cabecera=ROJO,
                columnas_numericas=(4, 5),
            )
        )
    else:
        elementos.append(
            Paragraph(
                "No se registraron alarmas durante el periodo.", estilos["normal"]
            )
        )

    # Detalle opcional de lecturas
    if incluir_detalle_lecturas and datos["lecturas"]:
        elementos.append(PageBreak())
        elementos.append(_titulo_seccion("Detalle de lecturas", ancho, estilos))
        filas = [
            [
                _fmt_fecha(l.get("timestamp"), "%d/%m/%Y %H:%M:%S"),
                _fmt_num(l.get("temperatura"), 2),
                _fmt_num(l.get("humedad"), 2),
                l.get("espacios_libres", "-"),
                "Sí" if l.get("sistema_encendido") else "No",
                "Sí" if l.get("alarma") else "No",
            ]
            for l in datos["lecturas"][:400]
        ]
        elementos.append(
            _tabla(
                [
                    "Marca de tiempo",
                    "Temp. (°C)",
                    "Hum. (%)",
                    "Espacios",
                    "Encendido",
                    "Alarma",
                ],
                filas,
                ancho,
                [0.28, 0.15, 0.15, 0.14, 0.14, 0.14],
                estilos,
                columnas_numericas=(1, 2, 3),
            )
        )

    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(
        Paragraph(
            "Documento generado automáticamente por el backend de SmartEgg. "
            "Los datos provienen del nodo físico a través del puerto serial y se "
            "distribuyen por MQTT hacia Grafana y el frontend.",
            estilos["nota"],
        )
    )

    pie = (
        f"{config.REPORT_PROJECT_NAME} · Generado el "
        f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} "
        f"{config.REPORT_TIMEZONE_LABEL}"
    )

    def _canvas(*args, **kwargs):
        kwargs["pie_texto"] = pie
        return _CanvasNumerado(*args, **kwargs)

    doc.build(elementos, canvasmaker=_canvas)
    buffer.seek(0)
    return buffer.getvalue()
