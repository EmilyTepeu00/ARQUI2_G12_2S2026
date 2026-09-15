"""
Consultas historicas agregadas.

Estos endpoints existen para alimentar dashboards: devuelven datos YA agrupados
por el motor de base de datos en lugar de listas crudas. La diferencia importa
porque un dia de telemetria son miles de lecturas, y mandarlas todas al
navegador para promediarlas ahi es tirar ancho de banda y trabajo al cliente.

Son de solo lectura y publicos, igual que el resto de la telemetria, para que
Grafana pueda consultarlos sin manejar tokens. Nada aca expone datos por
usuario: los informes por operador siguen protegidos en /api/perfil.
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from src.db import db

historico_bp = Blueprint("historico", __name__)

# Tope de seguridad: sin el, un `intervalo=1` sobre un mes devolveria decenas de
# miles de puntos y el panel se cuelga.
MAX_PUNTOS = 5000


def _parsear_fecha(valor):
    if not valor:
        return None
    texto = str(valor).strip().replace("Z", "+00:00")

    intentos = [texto]
    # En una query string el "+" del desfase horario se decodifica como espacio
    # ("...T00:00:00+00:00" llega como "...T00:00:00 00:00"), asi que la fecha
    # se rechazaria sin este segundo intento.
    if " " in texto:
        cabeza, _, cola = texto.rpartition(" ")
        intentos.append(f"{cabeza}+{cola}")

    for intento in intentos:
        try:
            fecha = datetime.fromisoformat(intento)
        except ValueError:
            continue
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha
    return None


def _rango(horas_por_defecto: int = 24):
    """Lee desde/hasta de la query. Por defecto, las ultimas N horas."""
    hasta = _parsear_fecha(request.args.get("hasta")) or datetime.now(timezone.utc)
    desde = _parsear_fecha(request.args.get("desde")) or hasta - timedelta(
        hours=horas_por_defecto
    )
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _iso(valor):
    return valor.isoformat() if isinstance(valor, datetime) else valor


def _entero(nombre, por_defecto, minimo, maximo):
    try:
        valor = int(request.args.get(nombre, por_defecto))
    except (TypeError, ValueError):
        return por_defecto
    return max(minimo, min(maximo, valor))


@historico_bp.get("/series")
def series():
    """Serie temporal de temperatura y humedad, agrupada por intervalos."""
    desde, hasta = _rango()
    intervalo = _entero("intervalo", 5, 1, 1440)

    # Si el rango pedido con ese intervalo excede el tope, se ensancha el
    # intervalo en vez de recortar el rango: el usuario ve todo el periodo que
    # pidio, solo que con menos resolucion.
    minutos_totales = (hasta - desde).total_seconds() / 60
    if minutos_totales / intervalo > MAX_PUNTOS:
        intervalo = max(1, int(minutos_totales / MAX_PUNTOS) + 1)

    puntos = db.serie_temporal(desde, hasta, intervalo)
    for punto in puntos:
        punto["timestamp"] = _iso(punto["timestamp"])

    return (
        jsonify(
            {
                "desde": _iso(desde),
                "hasta": _iso(hasta),
                "intervalo_minutos": intervalo,
                "puntos": len(puntos),
                "series": puntos,
            }
        ),
        200,
    )


@historico_bp.get("/diario")
def diario():
    """Una fila por dia con promedios, extremos, alarmas y aperturas."""
    dias = _entero("dias", 7, 1, 365)
    filas = db.resumen_diario(dias)
    return jsonify({"dias": dias, "filas": len(filas), "resumen": filas}), 200


@historico_bp.get("/alarmas")
def alarmas():
    """Cuantas alarmas hubo de cada tipo y cuanto duraron."""
    desde, hasta = _rango(horas_por_defecto=24 * 7)
    filas = db.conteo_alarmas_por_tipo(desde, hasta)
    return (
        jsonify(
            {
                "desde": _iso(desde),
                "hasta": _iso(hasta),
                "total": sum(f["cantidad"] for f in filas),
                "por_tipo": filas,
            }
        ),
        200,
    )


@historico_bp.get("/operadores")
def operadores():
    """Ranking de operadores por actividad en la puerta."""
    desde, hasta = _rango(horas_por_defecto=24 * 7)
    filas = db.actividad_por_operador(desde, hasta)
    return (
        jsonify(
            {
                "desde": _iso(desde),
                "hasta": _iso(hasta),
                "operadores": filas,
            }
        ),
        200,
    )


@historico_bp.get("/lote/<lote_id>")
def por_lote(lote_id):
    """Condiciones ambientales durante la incubacion de un lote."""
    from src.models import to_object_id

    oid = to_object_id(lote_id)
    stats = db.estadisticas_por_lote(oid)
    if stats is None:
        return jsonify({"mensaje": "Lote no encontrado o sin datos."}), 404
    stats["desde"] = _iso(stats.get("desde"))
    stats["hasta"] = _iso(stats.get("hasta"))
    return jsonify(stats), 200
