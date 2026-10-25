import os
import json
import math

from dotenv import load_dotenv

load_dotenv()

def _get_bool(env_name: str, default: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "si", "sí")

def _get_float(env_name: str, default: float) -> float:
    value = os.getenv(env_name)
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default

def _get_int(env_name: str, default: int) -> int:
    value = os.getenv(env_name)
    try:
        return int(value) if value not in (None, "") else default
    except ValueError:
        return default

def _get_str(env_name: str, default: str) -> str:
    value = os.getenv(env_name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_json_dict(env_name: str, default: dict) -> dict:
    value = os.getenv(env_name)
    if not value:
        return default
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("se esperaba un objeto JSON")
        valores = {str(k): float(v) for k, v in parsed.items()}
        if any(not math.isfinite(v) or v < 0 for v in valores.values()):
            raise ValueError("las potencias deben ser valores finitos no negativos")
        return valores
    except (TypeError, ValueError, json.JSONDecodeError):
        return default

class Config:
    # Servidor Flask
    FLASK_HOST = _get_str("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = _get_int("FLASK_PORT", 5000)
    FLASK_DEBUG = _get_bool("FLASK_DEBUG", True)

    # Logging
    LOG_LEVEL = _get_str("LOG_LEVEL", "INFO").upper()

    # Identidad del nodo
    NODE_ID = _get_str("NODE_ID", "incubadora-01")

    # Comunicación serial con el Arduino
    SERIAL_ENABLED = _get_bool("SERIAL_ENABLED", False)
    SERIAL_PORT = _get_str("SERIAL_PORT", "/dev/ttyUSB0")
    SERIAL_BAUDRATE = _get_int("SERIAL_BAUDRATE", 9600)
    SERIAL_TIMEOUT = _get_float("SERIAL_TIMEOUT", 1)
    SERIAL_AUTO_DETECT = _get_bool("SERIAL_AUTO_DETECT", True)
    SERIAL_RECONNECT_DELAY = _get_float("SERIAL_RECONNECT_DELAY", 5)
    SERIAL_MIN_PERSIST_INTERVAL = _get_float("SERIAL_MIN_PERSIST_INTERVAL", 0)

    # Broker MQTT
    MQTT_ENABLED = _get_bool("MQTT_ENABLED", True)
    MQTT_HOST = _get_str("MQTT_HOST", "localhost")
    MQTT_PORT = _get_int("MQTT_PORT", 1883)
    MQTT_KEEPALIVE = _get_int("MQTT_KEEPALIVE", 30)
    MQTT_CLIENT_ID = _get_str("MQTT_CLIENT_ID", "smartegg-backend")
    MQTT_USERNAME = _get_str("MQTT_USERNAME", "")
    MQTT_PASSWORD = _get_str("MQTT_PASSWORD", "")
    MQTT_TOPIC_PREFIX = _get_str("MQTT_TOPIC_PREFIX", "smartegg")
    MQTT_RECONNECT_MIN_DELAY = _get_int("MQTT_RECONNECT_MIN_DELAY", 1)
    MQTT_RECONNECT_MAX_DELAY = _get_int("MQTT_RECONNECT_MAX_DELAY", 30)
    MQTT_PUBLISH_SPLIT_SENSORS = _get_bool("MQTT_PUBLISH_SPLIT_SENSORS", True)

    # Protección por visión. Los fotogramas consecutivos reducen bloqueos por falsos positivos.
    VISION_CONFIDENCE_THRESHOLD = _get_float("VISION_CONFIDENCE_THRESHOLD", 0.80)
    VISION_CONSECUTIVE_FRAMES = max(1, _get_int("VISION_CONSECUTIVE_FRAMES", 3))
    SYSTEM_UNLOCK_ROLES = tuple(
        rol.strip().lower()
        for rol in _get_str("SYSTEM_UNLOCK_ROLES", "admin,administrador").split(",")
        if rol.strip()
    )

    # Potencias iniciales en watts. Deben sustituirse por las medidas del prototipo.
    ENERGY_POWER_WATTS = _get_json_dict(
        "ENERGY_POWER_WATTS",
        {"calefaccion": 60.0, "ventilacion": 5.0, "rotacion": 3.0, "luz": 3.0},
    )
    # Huecos sin datos más largos que esto no se integran como consumo.
    ENERGY_MAX_GAP_S = _get_float("ENERGY_MAX_GAP_S", 300)
    # Compatibilidad con el nombre anterior mientras se actualizan los .env locales.
    ENERGY_LIMIT_KWH_PER_CYCLE = _get_float(
        "ENERGY_LIMIT_KWH_PER_CYCLE", _get_float("ENERGY_LIMIT_KWH", 0.0)
    )
    if not math.isfinite(ENERGY_LIMIT_KWH_PER_CYCLE) or ENERGY_LIMIT_KWH_PER_CYCLE < 0:
        ENERGY_LIMIT_KWH_PER_CYCLE = 0.0

    # Base de datos MongoDB
    MONGO_URI = _get_str("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = _get_str("MONGO_DB_NAME", "smartegg")
    MONGO_REQUIRED = _get_bool("MONGO_REQUIRED", False)
    MONGO_RECONNECT_DELAY = _get_float("MONGO_RECONNECT_DELAY", 10)

    # Umbrales del sistema
    TEMP_MIN = _get_float("TEMP_MIN", 37.0)
    TEMP_MAX = _get_float("TEMP_MAX", 38.0)
    HUM_MIN = _get_float("HUM_MIN", 50.0)
    HUM_MAX = _get_float("HUM_MAX", 65.0)

    # Autenticacion y roles
    AUTH_ENABLED = _get_bool("AUTH_ENABLED", True)
    JWT_SECRET = _get_str("JWT_SECRET", "cambiar-esta-clave-en-produccion")
    JWT_ALGORITMO = _get_str("JWT_ALGORITMO", "HS256")
    JWT_EXPIRA_HORAS = _get_int("JWT_EXPIRA_HORAS", 12)

    # Usuarios que se siembran al arrancar si la coleccion esta vacia.
    AUTH_SEED_USUARIOS = _get_bool("AUTH_SEED_USUARIOS", True)
    ADMIN_USERNAME = _get_str("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = _get_str("ADMIN_PASSWORD", "admin123")
    ADMIN_NOMBRE = _get_str("ADMIN_NOMBRE", "Administrador SmartEgg")
    OP1_USERNAME = _get_str("OP1_USERNAME", "operador1")
    OP1_PASSWORD = _get_str("OP1_PASSWORD", "operador1")
    OP1_ID_OPERADOR = _get_str("OP1_ID_OPERADOR", "OP1")
    OP2_USERNAME = _get_str("OP2_USERNAME", "operador2")
    OP2_PASSWORD = _get_str("OP2_PASSWORD", "operador2")
    OP2_ID_OPERADOR = _get_str("OP2_ID_OPERADOR", "OP2")

    # Reportes
    REPORT_FACULTY_NAME = _get_str(
        "REPORT_FACULTY_NAME",
        "Facultad de Ingeniería - Escuela de Ciencias y Sistemas - USAC",
    )
    REPORT_PROJECT_NAME = _get_str(
        "REPORT_PROJECT_NAME", "SmartEgg - Plataforma IoT Distribuida"
    )
    REPORT_TIMEZONE_LABEL = _get_str("REPORT_TIMEZONE_LABEL", "UTC")

config = Config()
