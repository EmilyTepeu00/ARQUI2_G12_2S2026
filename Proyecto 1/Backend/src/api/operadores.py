from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from src.db import db
from src.models import Operador, serialize_doc, serialize_list

operadores_bp = Blueprint("operadores", __name__)


@operadores_bp.get("")
def listar_operadores():
    return jsonify(serialize_list(db.listar_operadores())), 200


@operadores_bp.post("")
def crear_operador():
    data = request.get_json(silent=True) or {}
    errores = Operador.validar(data)
    if errores:
        return jsonify({"errores": errores}), 400

    if db.obtener_operador(str(data.get("id_operador")).strip()):
        return jsonify({"mensaje": "Ya existe un operador con ese id."}), 409

    try:
        creado = db.crear_operador(Operador.build(data))
    except DuplicateKeyError:
        return jsonify({"mensaje": "Ya existe un operador con ese id."}), 409

    if creado is None:
        return jsonify({"mensaje": "Base de datos no disponible."}), 503
    return jsonify(serialize_doc(creado)), 201


@operadores_bp.get("/<id_operador>")
def obtener_operador(id_operador):
    operador = db.obtener_operador(id_operador)
    if operador is None:
        return jsonify({"mensaje": "Operador no encontrado."}), 404
    return jsonify(serialize_doc(operador)), 200


@operadores_bp.put("/<id_operador>")
def actualizar_operador(id_operador):
    existente = db.obtener_operador(id_operador)
    if existente is None:
        return jsonify({"mensaje": "Operador no encontrado."}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"mensaje": "No se enviaron campos para actualizar."}), 400

    permitidos = {"nombre", "edad", "genero", "rol", "metodo_acceso", "activo"}
    cambios = {k: v for k, v in data.items() if k in permitidos}
    if not cambios:
        return jsonify({"mensaje": "Ningún campo actualizable en la petición."}), 400

    errores = Operador.validar({**existente, **cambios})
    if errores:
        return jsonify({"errores": errores}), 400

    db.actualizar_operador(id_operador, cambios)
    return jsonify(serialize_doc(db.obtener_operador(id_operador))), 200


@operadores_bp.delete("/<id_operador>")
def eliminar_operador(id_operador):
    if db.obtener_operador(id_operador) is None:
        return jsonify({"mensaje": "Operador no encontrado."}), 404
    db.eliminar_operador(id_operador)
    return jsonify({"mensaje": "Operador eliminado correctamente."}), 200
