import logging
import sys

from src.config import config

_FORMATO = "%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s"
_FECHA = "%Y-%m-%d %H:%M:%S"

_configurado = False


def _configurar_root():
    global _configurado
    if _configurado:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMATO, datefmt=_FECHA))

    root = logging.getLogger("smartegg")
    root.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
    _configurado = True


def get_logger(nombre: str) -> logging.Logger:
    """Devuelve un logger hijo de `smartegg`"""
    _configurar_root()
    return logging.getLogger(f"smartegg.{nombre}")
