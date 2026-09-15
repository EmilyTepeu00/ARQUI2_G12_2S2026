"""Endpoints de autenticación: /api/auth/*"""

from flask import Blueprint, g, jsonify, request
from pymongo.errors import DuplicateKeyError

from src.auth.decorators import requiere_admin, requiere_auth, usuario_actual
from src.auth.repository import ROLES_OPERADOR, ROLES_VALIDOS, usuarios_repo
from src.auth.security import generar_token, verificar_password
from src.db import db
from src.logger import get_logger
from src.models import serialize_list
from src.config import config

auth_bp = Blueprint("auth", __name__)
log = get_logger("api.auth")

PASSWORD_MIN = 6


def _publico(usuario: dict) -> dict:
    """Vista del usuario sin datos sensibles."""
    return {
        "username": usuario.get("username"),
        "nombre": usuario.get("nombre", ""),
        "rol": usuario.get("rol"),
        "id_operador": usuario.get("id_operador"),
        "activo": usuario.get("activo", True),
    }


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = data.get("password")

    if not username or not password:
        return jsonify({"errores": ["'username' y 'password' son obligatorios."]}), 400

    if not db.disponible:
        return (
            jsonify({"mensaje": "Base de datos no disponible, no se puede autenticar."}),
            503,
        )

    usuario = usuarios_repo.obtener(username)
    # Mismo mensaje para usuario inexistente y contraseña mala: no se filtra
    # si el usuario existe o no.
    if usuario is None or not verificar_password(usuario.get("password_hash"), password):
        log.warning("Intento de acceso fallido para '%s'.", username)
        return jsonify({"mensaje": "Usuario o contraseña incorrectos."}), 401

    if not usuario.get("activo", True):
        return jsonify({"mensaje": "La cuenta está desactivada."}), 403

    token, expira_en = generar_token(usuario)
    usuarios_repo.registrar_acceso(username)
    log.info("Acceso concedido a '%s' (%s).", username, usuario.get("rol"))

    return (
        jsonify(
            {
                "token": token,
                "token_tipo": "Bearer",
                "expira_en": expira_en,
                "usuario": _publico(usuario),
            }
        ),
        200,
    )


@auth_bp.get("/yo")
@requiere_auth
def yo():
    """Datos del usuario dueño del token."""
    actual = usuario_actual()
    registro = usuarios_repo.obtener(actual.get("username"))
    return jsonify(_publico(registro or actual)), 200


@auth_bp.post("/cambiar-password")
@requiere_auth
def cambiar_password():
    data = request.get_json(silent=True) or {}
    actual = data.get("password_actual")
    nueva = data.get("password_nueva")

    errores = []
    if not actual:
        errores.append("El campo 'password_actual' es obligatorio.")
    if not nueva:
        errores.append("El campo 'password_nueva' es obligatorio.")
    elif len(str(nueva)) < PASSWORD_MIN:
        errores.append(f"La contraseña nueva debe tener al menos {PASSWORD_MIN} caracteres.")
    if errores:
        return jsonify({"errores": errores}), 400

    username = usuario_actual().get("username")
    registro = usuarios_repo.obtener(username)
    if registro is None:
        return jsonify({"mensaje": "Usuario no encontrado."}), 404
    if not verificar_password(registro.get("password_hash"), actual):
        return jsonify({"mensaje": "La contraseña actual no coincide."}), 401

    if not usuarios_repo.actualizar_password(username, nueva):
        return jsonify({"mensaje": "No se pudo actualizar la contraseña."}), 503

    return jsonify({"mensaje": "Contraseña actualizada correctamente."}), 200


@auth_bp.get("/usuarios")
@requiere_admin
def listar_usuarios():
    return jsonify(serialize_list(usuarios_repo.listar())), 200


@auth_bp.post("/usuarios")
@requiere_admin
def crear_usuario():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = data.get("password")
    rol = data.get("rol")
    id_operador = data.get("id_operador")

    errores = []
    if not username:
        errores.append("El campo 'username' es obligatorio.")
    if not password:
        errores.append("El campo 'password' es obligatorio.")
    elif len(str(password)) < PASSWORD_MIN:
        errores.append(f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres.")
    if rol not in ROLES_VALIDOS:
        errores.append(f"rol debe ser uno de: {', '.join(sorted(ROLES_VALIDOS))}")
    if rol in ROLES_OPERADOR and not id_operador:
        errores.append("Los roles de operador requieren 'id_operador' (ej. OP1).")
    if errores:
        return jsonify({"errores": errores}), 400

    if not db.disponible:
        return jsonify({"mensaje": "Base de datos no disponible."}), 503

    if usuarios_repo.obtener(username):
        return jsonify({"mensaje": "Ya existe un usuario con ese username."}), 409

    try:
        creado = usuarios_repo.crear(
            username, password, rol, data.get("nombre", ""), id_operador
        )
    except DuplicateKeyError:
        return jsonify({"mensaje": "Ya existe un usuario con ese username."}), 409

    if creado is None:
        return jsonify({"mensaje": "Base de datos no disponible."}), 503

    log.info("Usuario '%s' creado con rol %s.", username, rol)
    return jsonify(_publico(creado)), 201


@auth_bp.delete("/usuarios/<username>")
@requiere_admin
def eliminar_usuario(username):
    username = str(username).strip().lower()

    if username == usuario_actual().get("username"):
        return jsonify({"mensaje": "No puede eliminar su propia cuenta."}), 409
    if username == config.ADMIN_USERNAME.strip().lower():
        return (
            jsonify({"mensaje": "No se puede eliminar la cuenta de administrador base."}),
            409,
        )
    if usuarios_repo.obtener(username) is None:
        return jsonify({"mensaje": "Usuario no encontrado."}), 404

    if not usuarios_repo.eliminar(username):
        return jsonify({"mensaje": "No se pudo eliminar el usuario."}), 503

    log.info("Usuario '%s' eliminado.", username)
    return jsonify({"mensaje": "Usuario eliminado correctamente."}), 200
