import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(env_name: str, default: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_float(env_name: str, default: float) -> float:
    value = os.getenv(env_name)
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


class Config:
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = _get_bool("FLASK_DEBUG", True)

    SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
    SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", 9600))
    SERIAL_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", 1))
    SERIAL_AUTO_DETECT = _get_bool("SERIAL_AUTO_DETECT", True)
    SERIAL_RECONNECT_DELAY = float(os.getenv("SERIAL_RECONNECT_DELAY", 5))

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartegg")

    TEMP_MIN = _get_float("TEMP_MIN", 37.0)
    TEMP_MAX = _get_float("TEMP_MAX", 38.0)
    HUM_MIN = _get_float("HUM_MIN", 50.0)
    HUM_MAX = _get_float("HUM_MAX", 65.0)

    REPORT_FACULTY_NAME = os.getenv("REPORT_FACULTY_NAME")
    REPORT_PROJECT_NAME = os.getenv("REPORT_PROJECT_NAME")


config = Config()
