"""
Envoltura de la capa de datos para el lector serial.

Existe para que un fallo de la base nunca tumbe el hilo que lee el Arduino:
cada metodo atrapa la excepcion, la loguea y devuelve None. El lector sigue
leyendo y publicando por MQTT aunque Mongo este caido.
"""

from src.db import db
from src.logger import get_logger

log = get_logger("serial.persist")


class Persistencia:
    """Envuelve la capa de datos y absorbe sus fallos"""

    @staticmethod
    def insert_lectura(lectura: dict):
        try:
            return db.guardar_lectura(lectura)
        except Exception as exc:
            log.error("Fallo al persistir lectura: %s", exc)
            return None

    @staticmethod
    def insert_evento_puerta(evento: dict):
        try:
            return db.registrar_apertura(evento)
        except Exception as exc:
            log.error("Fallo al persistir evento de puerta: %s", exc)
            return None

    @staticmethod
    def abrir_alarma(alarma: dict):
        try:
            return db.abrir_alarma(alarma)
        except Exception as exc:
            log.error("Fallo al abrir alarma: %s", exc)
            return None

    @staticmethod
    def cerrar_alarma(alarma_id, mensaje: str = None):
        try:
            return db.cerrar_alarma(alarma_id, mensaje)
        except Exception as exc:
            log.error("Fallo al cerrar alarma: %s", exc)
            return None

    @staticmethod
    def alarma_activa():
        try:
            return db.obtener_alarma_activa()
        except Exception as exc:
            log.error("Fallo al consultar alarma activa: %s", exc)
            return None

    @staticmethod
    def operador_existe(id_operador: str) -> bool:
        try:
            return db.obtener_operador(id_operador) is not None
        except Exception as exc:
            log.error("Fallo al consultar operador: %s", exc)
            return False


persistencia = Persistencia()
