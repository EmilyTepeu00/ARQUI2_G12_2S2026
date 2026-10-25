"""Consultas historicas agregadas."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from src.db import db

historico_bp = Blueprint("historico", __name__)

MAX_PUNTOS = 5000

def _parsear_fecha(valor):
    if not valor:
        return None
    texto = str(valor).strip().replace("Z", "+00:00")

    intentos = [texto]
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
    """Lee desde/hasta de la query."""
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
