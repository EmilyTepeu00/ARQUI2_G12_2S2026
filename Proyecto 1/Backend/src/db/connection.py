"""Conexion a MongoDB: cliente, colecciones, indices y modo degradado."""

import sys
import threading
import time

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import AutoReconnect, PyMongoError, ServerSelectionTimeoutError

from src.config import config
from src.logger import get_logger

log = get_logger("db")

# Indices que se crean al conectar.
INDICES = {
    "lecturas": [
        ([("timestamp", DESCENDING)], {}),
    ],
    "alarmas": [
        ([("inicio", DESCENDING)], {}),
        ([("timestamp", DESCENDING)], {}),
        ([("activa", ASCENDING)], {}),
    ],
    "aperturas_puerta": [
        ([("timestamp", DESCENDING)], {}),
        ([("id_operador", ASCENDING)], {}),
        # Compuesto: el reporte por operador filtra por los dos campos a la vez.
        ([("id_operador", ASCENDING), ("timestamp", DESCENDING)], {}),
    ],
    "operadores": [
        ([("id_operador", ASCENDING)], {"unique": True}),
    ],
    "lotes": [
        ([("fecha_ingreso", DESCENDING)], {}),
        ([("estado", ASCENDING)], {}),
    ],
    "usuarios": [
        ([("username", ASCENDING)], {"unique": True}),
    ],
}

class ConexionMongo:
    """Mantiene viva la conexion y expone las colecciones como atributos."""

    def __init__(self):
        self.client = None
        self.db = None
        self.lecturas = None
        self.lotes = None
        self.alarmas = None
        self.operadores = None
        self.aperturas = None
        self.usuarios = None
        self._disponible = False
        self._lock = threading.Lock()
        self._reintento_activo = False

        if not self._conectar():
            if config.MONGO_REQUIRED:
                log.critical(
                    "MONGO_REQUIRED=true y no hay base de datos disponible. Se aborta."
                )
                sys.exit(1)
            log.warning(
                "Backend en modo degradado: sin persistencia. "
                "Se reintentará la conexión cada %.0f s.",
                config.MONGO_RECONNECT_DELAY,
            )
            self._lanzar_reintento()

    # Conexion
    def _conectar(self) -> bool:
        try:
            client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
            # MongoClient no conecta al construirse: es perezoso.
            client.admin.command("ping")
        except PyMongoError as exc:
            log.error("No se pudo conectar a MongoDB: %s", exc)
            return False

        self.client = client
        self.db = client[config.MONGO_DB_NAME]
        self.lecturas = self.db["lecturas"]
        self.lotes = self.db["lotes"]
        self.alarmas = self.db["alarmas"]
        self.operadores = self.db["operadores"]
        self.aperturas = self.db["aperturas_puerta"]
        self.usuarios = self.db["usuarios"]

        self._crear_indices()

        self._disponible = True
        log.info("Conexión a MongoDB establecida (%s)", config.MONGO_DB_NAME)
        return True

    def _crear_indices(self):
        """Crea los indices declarados."""
        for nombre, definiciones in INDICES.items():
            coleccion = self.db[nombre]
            for llaves, opciones in definiciones:
                try:
                    coleccion.create_index(llaves, **opciones)
                except PyMongoError as exc:
                    # Un indice unico falla si ya hay duplicados.
                    log.warning(
                        "No se pudo crear el índice %s sobre '%s': %s",
                        llaves,
                        nombre,
                        exc,
                    )

    def _lanzar_reintento(self):
        if self._reintento_activo:
            return
        self._reintento_activo = True

        def _loop():
            while not self._disponible:
                time.sleep(config.MONGO_RECONNECT_DELAY)
                log.info("Reintentando conexión a MongoDB...")
                if self._conectar():
                    log.info("Persistencia restablecida.")
                    break
            self._reintento_activo = False

        threading.Thread(target=_loop, name="MongoReconnect", daemon=True).start()

    # Estado
    @property
    def disponible(self) -> bool:
        return self._disponible

    def estado(self) -> dict:
        return {
            "conectado": self._disponible,
            # split("@") recorta usuario y contraseña si la URI los trae.
            "uri": config.MONGO_URI.split("@")[-1],
            "base": config.MONGO_DB_NAME,
        }

    def _guard(self, valor_por_defecto=None):
        """Devuelve True si hay base; si no, loguea una vez y devuelve False."""
        if not self._disponible:
            log.debug("Operación de base omitida: sin conexión.")
            return False
        return True

    def _marcar_caida(self, exc):
        """Si la base se cae en ejecucion, vuelve a modo degradado y reintenta."""
        if isinstance(exc, (AutoReconnect, ServerSelectionTimeoutError)):
            self._disponible = False
            log.warning("Se perdió la conexión con MongoDB. Modo degradado activo.")
            self._lanzar_reintento()
