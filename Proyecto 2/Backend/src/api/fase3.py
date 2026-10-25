"""Consultas de solo lectura de la Fase 3 (ML, vision, estado y consumo).

Las usa Grafana (datasource Infinity) para graficar. No controlan nada:
sensores y actuadores se siguen manejando solo por MQTT.
"""

import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from src.api.historico import _entero, _rango
from src.config import config
from src.db import db

fase3_bp = Blueprint("fase3", __name__)


# UTILIDADES

def _nodo():
    return request.args.get("node") or config.NODE_ID


def _iso(valor):
    """Fecha en ISO con zona UTC (Mongo devuelve fechas sin zona)"""
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.isoformat()
    return valor


def _buscar(doc, claves):
    """Busca el primer campo existente: arriba, o dentro del payload original"""
    fuentes = [doc]
    for anidado in ("resultado_detector", "campos_originales", "detalle"):
        if isinstance(doc.get(anidado), dict):
            fuentes.append(doc[anidado])
    for fuente in fuentes:
        for clave in claves:
            if fuente.get(clave) is not None:
                return fuente[clave]
    return None


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _texto(valor):
    if isinstance(valor, dict):
        return str(
            valor.get("descripcion")
            or valor.get("mensaje")
            or valor.get("tipo")
            or json.dumps(valor, ensure_ascii=False, default=str)
        )
    return "" if valor is None else str(valor)


def _es_anomalia(doc):
    for clave in ("anomalia", "es_anomalia", "anomaly", "is_anomaly"):
        valor = _buscar(doc, [clave])
        if valor is not None:
            return str(valor).lower() in ("1", "true", "on", "si", "yes")
    resultado = str(_buscar(doc, ["resultado", "clase", "label"]) or "").lower()
    return resultado in ("anomalia", "anomaly", "anomalous", "atipico", "atípico")


def _descripcion_evento(doc):
    """Texto corto y legible para la tabla de bloqueos y alarmas"""
    if doc.get("tipo") == "anomalia_ml":
        return "El modelo ML marcó la lectura como anómala"
    return _texto(doc.get("motivo") or doc.get("detalle") or doc.get("accion"))


def _listar(coleccion, convertir, orden_ascendente=True, limite_defecto=500):
    """Documentos del nodo en el rango desde/hasta (por defecto, ultimas 24 h)."""
    if not db._guard():
        return jsonify({"error": "base de datos no disponible"}), 503
    desde, hasta = _rango()
    limite = _entero("limit", limite_defecto, 1, 2000)
    filtro = {"node_id": _nodo(), "timestamp": {"$gte": desde, "$lte": hasta}}
    # Se toman los mas recientes y luego se ordenan para la grafica.
    docs = list(db.db[coleccion].find(filtro).sort("timestamp", -1).limit(limite))
    if orden_ascendente:
        docs.reverse()
    filas = [convertir(d) for d in docs]
    return jsonify({"nodo": _nodo(), "total": len(filas), "datos": filas}), 200


# ENDPOINTS

@fase3_bp.get("/estado")
def estado():
    """Estado vigente: bloqueo, ciclo, ultima vision, ultimo ML y consumo"""
    if not db._guard():
        return jsonify({"error": "base de datos no disponible"}), 503
    nodo = _nodo()
    sistema = db.db["estado_sistema"].find_one({"node_id": nodo}) or {}
    energia = db.db["estado_energia"].find_one({"node_id": nodo}) or {}
    vision = db.db["vision_resultados"].find_one({"node_id": nodo}, sort=[("timestamp", -1)]) or {}
    ml = db.db["ml_anomalias"].find_one({"node_id": nodo}, sort=[("timestamp", -1)]) or {}

    bloqueado = bool(sistema.get("bloqueado")) or sistema.get("estado") == "bloqueado"
    ciclo = bool(sistema.get("ciclo_activo"))
    return (
        jsonify(
            {
                "nodo": nodo,
                "estado_texto": "BLOQUEADO" if bloqueado else "NORMAL",
                "bloqueado": 1 if bloqueado else 0,
                "motivo": _texto(sistema.get("motivo")),
                "ciclo_texto": "EN MARCHA" if ciclo else "DETENIDO",
                "ciclo_activo": 1 if ciclo else 0,
                "vision_clase": _buscar(vision, ["clase"]) or "sin datos",
                "vision_confianza": _numero(_buscar(vision, ["confianza"])),
                "ml_texto": ("ANOMALÍA" if _es_anomalia(ml) else "NORMAL") if ml else "SIN DATOS",
                "ml_anomalia": 1 if (ml and _es_anomalia(ml)) else 0,
                "potencia_actual_w": _numero(energia.get("potencia_actual_w")),
                "energia_kwh": _numero(energia.get("energia_kwh")),
                "energia_ciclo_kwh": _numero(energia.get("energia_ciclo_kwh")),
                "limite_ciclo_kwh": _numero(energia.get("limite_ciclo_kwh")),
                "timestamp": _iso(sistema.get("timestamp")),
            }
        ),
        200,
    )


@fase3_bp.get("/energia")
def energia():
    """Serie de consumo electrico (snapshots publicados por el backend)"""
    return _listar(
        "energia_consumo",
        lambda d: {
            "timestamp": _iso(d.get("timestamp")),
            "potencia_actual_w": _numero(d.get("potencia_actual_w")),
            "energia_kwh": _numero(d.get("energia_kwh")),
            "energia_ciclo_kwh": _numero(d.get("energia_ciclo_kwh")),
            "limite_ciclo_kwh": _numero(d.get("limite_ciclo_kwh")),
        },
    )


@fase3_bp.get("/vision")
def vision():
    """Clasificaciones de la camara: clase y confianza"""

    def fila(d):
        conf = _numero(_buscar(d, ["confianza"]))
        pct = None if conf is None else round(conf * 100 if conf <= 1 else conf, 1)
        return {
            "timestamp": _iso(d.get("timestamp")),
            "clase": _buscar(d, ["clase"]) or "sin datos",
            "confianza": conf,
            "confianza_pct": pct,
        }

    return _listar("vision_resultados", fila)


@fase3_bp.get("/ml")
def ml():
    """Resultados del modelo de anomalias (anomalia = 1 si es anomala)"""
    return _listar(
        "ml_anomalias",
        lambda d: {
            "timestamp": _iso(d.get("timestamp")),
            "anomalia": 1 if _es_anomalia(d) else 0,
            "resultado": "ANOMALÍA" if _es_anomalia(d) else "NORMAL",
            "puntaje": _numero(_buscar(d, ["puntaje", "score", "anomaly_score"])),
        },
    )


@fase3_bp.get("/eventos")
def eventos():
    """Bloqueos, desbloqueos y alarmas del sistema (mas recientes primero)"""
    return _listar(
        "sistema_eventos",
        lambda d: {
            "timestamp": _iso(d.get("timestamp")),
            "tipo": d.get("tipo"),
            "categoria": d.get("tipo_evento") or "evento",
            "descripcion": _descripcion_evento(d),
        },
        orden_ascendente=False,
        limite_defecto=50,
    )