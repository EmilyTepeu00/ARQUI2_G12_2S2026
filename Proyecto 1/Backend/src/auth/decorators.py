"""Decoradores de autenticación y autorización por rol."""

from functools import wraps

from flask import g, jsonify, request

from src.auth.repository import ROL_ADMIN, ROLES_OPERADOR, usuarios_repo
from src.auth.security import TokenInvalido, decodificar_token, extraer_token
from src.config import config


def _sin_token():
    return (
        jsonify(
            {
                "mensaje": "Falta el token de acceso. Use la cabecera "
                "'Authorization: Bearer <token>'."
            }
        ),
        401,
    )


def autenticar_peticion():
    """Valida el token y deja el usuario en flask.g.

    Devuelve None si todo bien, o una respuesta de error lista para retornar.
    """
    if not config.AUTH_ENABLED:
        g.usuario = {
            "username": "auth-desactivada",
            "rol": ROL_ADMIN,
            "id_operador": None,
        }
        return None

    token = extraer_token(request.headers.get("Authorization"))
    if not token:
        return _sin_token()

    try:
        payload = decodificar_token(token)
    except TokenInvalido as exc:
        return jsonify({"mensaje": str(exc)}), 401

    g.usuario = {
        "username": payload.get("sub"),
        "rol": payload.get("rol"),
        "id_operador": payload.get("id_operador"),
        "nombre": payload.get("nombre", ""),
    }

    # Un usuario desactivado o borrado no debe seguir entrando con un token viejo.
    registro = usuarios_repo.obtener(g.usuario["username"])
    if registro is not None:
        if not registro.get("activo", True):
            return jsonify({"mensaje": "La cuenta está desactivada."}), 403
        g.usuario["rol"] = registro.get("rol", g.usuario["rol"])
        g.usuario["id_operador"] = registro.get("id_operador", g.usuario["id_operador"])

    return None


def requiere_auth(fn):
    """Exige un token válido."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = autenticar_peticion()
        if error is not None:
            return error
        return fn(*args, **kwargs)

    return wrapper


def requiere_rol(*roles):
    """Exige un token válido y que el rol esté entre los indicados."""

    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = autenticar_peticion()
            if error is not None:
                return error
            if g.usuario["rol"] not in roles:
                return (
                    jsonify(
                        {
                            "mensaje": "No tiene permisos para esta operación.",
                            "rol_actual": g.usuario["rol"],
                            "roles_requeridos": list(roles),
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorador


def requiere_admin(fn):
    return requiere_rol(ROL_ADMIN)(fn)


def usuario_actual() -> dict:
    return getattr(g, "usuario", None) or {}


def es_admin() -> bool:
    return usuario_actual().get("rol") == ROL_ADMIN


def id_operador_actual():
    return usuario_actual().get("id_operador")


def puede_ver_operador(id_operador: str) -> bool:
    """El administrador ve a cualquiera; un operador solo se ve a sí mismo."""
    if es_admin():
        return True
    if usuario_actual().get("rol") not in ROLES_OPERADOR:
        return False
    propio = id_operador_actual()
    return bool(propio) and str(id_operador) == str(propio)


def resolver_id_operador(solicitado=None):
    """Decide sobre qué operador se consulta.

    - Administrador: el que pida (o None = todos).
    - Operador: siempre el suyo, se ignora lo que pida.
    """
    if es_admin():
        return solicitado
    return id_operador_actual()
