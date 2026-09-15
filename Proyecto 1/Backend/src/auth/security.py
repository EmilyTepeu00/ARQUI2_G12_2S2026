"""Hash de contraseñas y firma de tokens JWT."""

from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from src.config import config


class TokenInvalido(Exception):
    """El token no se pudo verificar (firma, formato o expiración)."""


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verificar_password(password_hash: str, password: str) -> bool:
    if not password_hash or password is None:
        return False
    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def generar_token(usuario: dict):
    """Devuelve (token, expira_en_iso) para el usuario dado."""
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=config.JWT_EXPIRA_HORAS)

    payload = {
        "sub": usuario["username"],
        "rol": usuario["rol"],
        "id_operador": usuario.get("id_operador"),
        "nombre": usuario.get("nombre", ""),
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITMO)
    # PyJWT 1.x devolvía bytes; 2.x devuelve str.
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token, expira.isoformat()


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise TokenInvalido("El token expiró. Inicie sesión de nuevo.")
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido(f"Token inválido: {exc}")


def extraer_token(cabecera_authorization: str):
    """Saca el token de una cabecera 'Authorization: Bearer <token>'."""
    if not cabecera_authorization:
        return None
    partes = cabecera_authorization.split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    if len(partes) == 1:
        return partes[0]
    return None
