"""Acceso a la colección `usuarios`.

Vive en src/auth/ y no en src/db/ a propósito: las credenciales son
responsabilidad del módulo de autenticación y no de la capa de datos general.
"""

from datetime import datetime, timezone

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.auth.security import hash_password
from src.config import config
from src.db import db
from src.logger import get_logger

log = get_logger("auth.repo")

ROL_ADMIN = "administrador"
ROL_OPERADOR_1 = "operador_1"
ROL_OPERADOR_2 = "operador_2"
ROLES_VALIDOS = {ROL_ADMIN, ROL_OPERADOR_1, ROL_OPERADOR_2}
ROLES_OPERADOR = {ROL_OPERADOR_1, ROL_OPERADOR_2}


def _ahora():
    return datetime.now(timezone.utc)


class UsuariosRepo:
    @property
    def coleccion(self):
        """None cuando la base no está disponible (modo degradado)."""
        if not db.disponible or db.db is None:
            return None
        return db.db["usuarios"]

    def asegurar_indices(self):
        col = self.coleccion
        if col is None:
            return
        try:
            col.create_index([("username", ASCENDING)], unique=True)
        except PyMongoError as exc:
            log.warning("No se pudo crear el índice de usuarios: %s", exc)

    def obtener(self, username: str):
        col = self.coleccion
        if col is None or not username:
            return None
        try:
            return col.find_one({"username": str(username).strip().lower()})
        except PyMongoError as exc:
            log.error("Error al buscar el usuario: %s", exc)
            return None

    def listar(self):
        col = self.coleccion
        if col is None:
            return []
        try:
            return list(col.find({}, {"password_hash": 0}, sort=[("username", ASCENDING)]))
        except PyMongoError as exc:
            log.error("Error al listar usuarios: %s", exc)
            return []

    def crear(self, username, password, rol, nombre="", id_operador=None):
        """Devuelve el usuario creado, o None si la base no responde.

        Lanza DuplicateKeyError si el username ya existe.
        """
        col = self.coleccion
        if col is None:
            return None

        doc = {
            "username": str(username).strip().lower(),
            "password_hash": hash_password(password),
            "rol": rol,
            "nombre": nombre or "",
            "id_operador": id_operador,
            "activo": True,
            "creado_en": _ahora(),
            "ultimo_acceso": None,
        }
        col.insert_one(doc)
        doc.pop("password_hash", None)
        doc.pop("_id", None)
        return doc

    def actualizar_password(self, username: str, password_nueva: str) -> bool:
        col = self.coleccion
        if col is None:
            return False
        try:
            r = col.update_one(
                {"username": str(username).strip().lower()},
                {"$set": {"password_hash": hash_password(password_nueva)}},
            )
            return r.matched_count > 0
        except PyMongoError as exc:
            log.error("Error al actualizar la contraseña: %s", exc)
            return False

    def registrar_acceso(self, username: str):
        col = self.coleccion
        if col is None:
            return
        try:
            col.update_one(
                {"username": str(username).strip().lower()},
                {"$set": {"ultimo_acceso": _ahora()}},
            )
        except PyMongoError as exc:
            log.debug("No se pudo registrar el último acceso: %s", exc)

    def eliminar(self, username: str) -> bool:
        col = self.coleccion
        if col is None:
            return False
        try:
            return col.delete_one(
                {"username": str(username).strip().lower()}
            ).deleted_count > 0
        except PyMongoError as exc:
            log.error("Error al eliminar el usuario: %s", exc)
            return False


usuarios_repo = UsuariosRepo()


def sembrar_usuarios_iniciales():
    """Crea admin, operador1 y operador2 si no existen todavía.

    Es idempotente: se puede llamar en cada arranque sin duplicar nada.
    """
    if not config.AUTH_SEED_USUARIOS:
        log.info("AUTH_SEED_USUARIOS=false: no se siembran usuarios.")
        return

    if usuarios_repo.coleccion is None:
        log.warning("Sin base de datos: los usuarios iniciales se sembrarán al reconectar.")
        return

    usuarios_repo.asegurar_indices()

    semillas = [
        (config.ADMIN_USERNAME, config.ADMIN_PASSWORD, ROL_ADMIN, config.ADMIN_NOMBRE, None),
        (config.OP1_USERNAME, config.OP1_PASSWORD, ROL_OPERADOR_1, "Operador 1", config.OP1_ID_OPERADOR),
        (config.OP2_USERNAME, config.OP2_PASSWORD, ROL_OPERADOR_2, "Operador 2", config.OP2_ID_OPERADOR),
    ]

    creados = []
    for username, password, rol, nombre, id_operador in semillas:
        if usuarios_repo.obtener(username):
            continue
        try:
            if usuarios_repo.crear(username, password, rol, nombre, id_operador):
                creados.append(f"{username} ({rol})")
        except DuplicateKeyError:
            pass
        except PyMongoError as exc:
            log.error("No se pudo sembrar el usuario %s: %s", username, exc)

    if creados:
        log.info("Usuarios iniciales creados: %s", ", ".join(creados))
    else:
        log.info("Los usuarios iniciales ya existían.")
