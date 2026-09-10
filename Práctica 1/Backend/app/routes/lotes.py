from flask import Blueprint, jsonify, request
from app.database import db
from app.models import LoteHuevo, serialize_doc, serialize_list, to_object_id

lotes_bp = Blueprint("lotes", __name__)


@lotes_bp.post("")
def crear_lote():
    data = request.get_json(silent=True) or {}
    errores = LoteHuevo.validar(data)
    if errores:
        return jsonify({"errores": errores}), 400
    lote = LoteHuevo.build(data)
    lote_creado = db.crear_lote(lote)
    return jsonify(serialize_doc(lote_creado)), 201


@lotes_bp.get("")
def listar_lotes():
    lotes = db.listar_lotes()
    return jsonify(serialize_list(lotes)), 200


@lotes_bp.get("/<lote_id>")
def obtener_lote(lote_id):
    oid = to_object_id(lote_id)
    lote = db.obtener_lote(oid)
    if lote is None:
        return jsonify({"mensaje": "Lote no encontrado."}), 404
    return jsonify(serialize_doc(lote)), 200


@lotes_bp.put("/<lote_id>")
def actualizar_lote(lote_id):
    oid = to_object_id(lote_id)
    lote_existente = db.obtener_lote(oid)
    if lote_existente is None:
        return jsonify({"mensaje": "Lote no encontrado."}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"mensaje": "No se enviaron campos para actualizar."}), 400

    campos_permitidos = {
        "nombre_lote",
        "cantidad_huevos",
        "raza",
        "responsable",
        "observaciones",
        "estado",
    }
    cambios = {k: v for k, v in data.items() if k in campos_permitidos}

    errores = LoteHuevo.validar({**lote_existente, **cambios})
    if errores:
        return jsonify({"errores": errores}), 400

    db.actualizar_lote(oid, cambios)
    lote_actualizado = db.obtener_lote(oid)
    return jsonify(serialize_doc(lote_actualizado)), 200


@lotes_bp.delete("/<lote_id>")
def eliminar_lote(lote_id):
    oid = to_object_id(lote_id)
    lote_existente = db.obtener_lote(oid)
    if lote_existente is None:
        return jsonify({"mensaje": "Lote no encontrado."}), 404

    db.eliminar_lote(oid)
    return jsonify({"mensaje": "Lote eliminado correctamente."}), 200
