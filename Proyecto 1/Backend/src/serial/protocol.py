import json
import re

TIPO_LECTURA = "lectura"
TIPO_PUERTA = "puerta"
# Tarjeta leída por el RFID que no corresponde a ningún operador registrado.
# Es un intento de acceso fallido, no una apertura: se registra aparte para que
# quede rastro de quién intentó entrar sin autorización.
TIPO_ACCESO_DENEGADO = "acceso_denegado"

# Rangos de sentido
TEMP_RANGO_VALIDO = (-40.0, 100.0)
HUM_RANGO_VALIDO = (0.0, 100.0)
ESPACIOS_MAXIMOS = 6


class ErrorProtocolo(ValueError):
    """La línea llegó, pero no cumple"""


def _a_bool(valor, defecto=False) -> bool:
    if valor is None:
        return defecto
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in ("1", "true", "on", "si", "sí", "activo"):
        return True
    if texto in ("0", "false", "off", "no", "inactivo"):
        return False
    return defecto


def _a_float(valor, campo: str) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorProtocolo(f"'{campo}' no es numérico: {valor!r}")
    if numero != numero:  # NaN
        raise ErrorProtocolo(f"'{campo}' es NaN")
    return numero


def _a_int(valor, campo: str, defecto: int = 0) -> int:
    if valor is None:
        return defecto
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        raise ErrorProtocolo(f"'{campo}' no es entero: {valor!r}")


def _validar_lectura(datos: dict) -> dict:
    temp = datos["temperatura"]
    hum = datos["humedad"]

    if not TEMP_RANGO_VALIDO[0] <= temp <= TEMP_RANGO_VALIDO[1]:
        raise ErrorProtocolo(f"temperatura fuera de rango físico: {temp}")
    if not HUM_RANGO_VALIDO[0] <= hum <= HUM_RANGO_VALIDO[1]:
        raise ErrorProtocolo(f"humedad fuera de rango físico: {hum}")

    espacios = datos["espacios_libres"]
    if espacios < 0 or espacios > ESPACIOS_MAXIMOS:
        raise ErrorProtocolo(
            f"espacios_libres fuera de rango (0-{ESPACIOS_MAXIMOS}): {espacios}"
        )

    return datos


def _parsear_json(linea: str):
    try:
        crudo = json.loads(linea)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(crudo, dict):
        return None

    tipo = str(crudo.get("tipo") or crudo.get("evento") or TIPO_LECTURA).lower()

    if tipo in ("tarjeta_no_registrada", "acceso_denegado"):
        return {
            "tipo": TIPO_ACCESO_DENEGADO,
            "datos": {
                "uid": str(crudo.get("uid") or "").upper() or "desconocido",
                "autorizado": False,
                "origen": "serial",
            },
        }

    if tipo in ("puerta", "acceso", "evento_puerta"):
        accion = str(crudo.get("accion", "")).lower()
        if accion not in ("abrir", "cerrar"):
            raise ErrorProtocolo(f"accion de puerta inválida: {crudo.get('accion')!r}")
        datos = {
            "accion": accion,
            "id_operador": str(
                crudo.get("id_operador") or crudo.get("operador") or "desconocido"
            ),
            "metodo": str(
                crudo.get("metodo") or crudo.get("método") or "manual"
            ).lower(),
            "huevos_delta": _a_int(crudo.get("huevos_delta", 0), "huevos_delta"),
            "autorizado": _a_bool(crudo.get("autorizado"), True),
            "origen": "serial",
        }
        return {"tipo": TIPO_PUERTA, "datos": datos}

    datos = {
        "temperatura": _a_float(
            crudo.get("temperatura", crudo.get("temp")), "temperatura"
        ),
        "humedad": _a_float(crudo.get("humedad", crudo.get("hum")), "humedad"),
        "sistema_encendido": _a_bool(crudo.get("sistema_encendido")),
        "alarma": _a_bool(crudo.get("alarma")),
        "espacios_libres": _a_int(crudo.get("espacios_libres", 0), "espacios_libres"),
        "calefaccion": _a_bool(crudo.get("calefaccion")),
        "ventilacion": _a_bool(crudo.get("ventilacion")),
        "rotacion": _a_bool(crudo.get("rotacion")),
        "puerta_abierta": _a_bool(crudo.get("puerta_abierta")),
    }
    return {"tipo": TIPO_LECTURA, "datos": _validar_lectura(datos)}


def derivar_actuadores(datos: dict, temp_min: float, temp_max: float) -> dict:
    """Infiere calefacción/ventilación cuando el firmware no las reporta."""
    if not datos.get("sistema_encendido"):
        return datos
    temp = datos.get("temperatura")
    if temp is None:
        return datos
    datos["calefaccion"] = temp < temp_min
    datos["ventilacion"] = temp > temp_max
    return datos


def parsear_linea(linea: str):
    """Convierte una línea del serial en un mensaje normalizado."""
    if not linea:
        return None
    linea = linea.strip()
    if not linea:
        return None

    if linea[0] in "{[":
        return _parsear_json(linea)

    return None
