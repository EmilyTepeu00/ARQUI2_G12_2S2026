from dataclasses import dataclass

from src.config import config

@dataclass(frozen=True)
class TopicSpec:
    sufijo: str
    qos: int
    retained: bool
    descripcion: str

SENSORES_LECTURA = "sensores_lectura"
SENSORES_TEMPERATURA = "sensores_temperatura"
SENSORES_HUMEDAD = "sensores_humedad"
ACTUADORES_ESTADO = "actuadores_estado"
ALARMAS_CRITICA = "alarmas_critica"
PUERTA_EVENTO = "puerta_evento"
STATUS = "status"
ACTUADORES_CMD = "actuadores_cmd"
ML_ANOMALIA = "ml_anomalia"
VISION_RESULTADO = "vision_resultado"
CAMARA_FRAME = "camara_frame"
SISTEMA_CMD = "sistema_cmd"
SISTEMA_ESTADO = "sistema_estado"
ENERGIA_CONSUMO = "energia_consumo"

CATALOGO = {
    SENSORES_LECTURA: TopicSpec(
        "sensores/lectura", 0, True, "Telemetría completa del nodo en formato JSON."
    ),
    SENSORES_TEMPERATURA: TopicSpec(
        "sensores/temperatura", 0, True, "Última temperatura leída (°C)."
    ),
    SENSORES_HUMEDAD: TopicSpec(
        "sensores/humedad", 0, True, "Última humedad relativa leída (%)."
    ),
    ACTUADORES_ESTADO: TopicSpec(
        "actuadores/estado",
        1,
        True,
        "Estado actual de calefacción, ventilación y rotación.",
    ),
    ALARMAS_CRITICA: TopicSpec(
        "alarmas/critica",
        1,
        True,
        "Evento de alarma ante condición fuera de rango (activa/resuelta).",
    ),
    PUERTA_EVENTO: TopicSpec(
        "puerta/evento",
        1,
        False,
        "Apertura o cierre de la incubadora con id de operador y método de acceso.",
    ),
    STATUS: TopicSpec(
        "status",
        1,
        True,
        "Disponibilidad del nodo (online/offline) publicada por LWT.",
    ),
    ACTUADORES_CMD: TopicSpec(
        "actuadores/cmd", 1, False, "Comando solicitado para un actuador."
    ),
    ML_ANOMALIA: TopicSpec(
        "ml/anomalia", 1, False, "Resultado del detector de anomalías."
    ),
    VISION_RESULTADO: TopicSpec(
        "vision/resultado", 1, False, "Clase y confianza detectadas en un fotograma."
    ),
    CAMARA_FRAME: TopicSpec(
        "camara/frame", 0, False, "Fotograma JPEG; el backend no lo persiste."
    ),
    SISTEMA_CMD: TopicSpec(
        "sistema/cmd", 1, False, "Comando para iniciar, detener o desbloquear el ciclo."
    ),
    SISTEMA_ESTADO: TopicSpec(
        "sistema/estado", 1, True, "Estado vigente normal/bloqueado del sistema."
    ),
    ENERGIA_CONSUMO: TopicSpec(
        "energia/consumo", 1, True, "Potencia actual y consumo acumulado en kWh."
    ),
}

def construir(clave: str, node_id: str = None) -> str:
    """Devuelve el topic completo para una clave lógica del catálogo."""
    spec = CATALOGO[clave]
    nodo = node_id or config.NODE_ID
    return f"{config.MQTT_TOPIC_PREFIX}/{nodo}/{spec.sufijo}"

def spec(clave: str) -> TopicSpec:
    return CATALOGO[clave]

def documentar(node_id: str = None) -> list:
    """Catálogo serializable, expuesto por la API para la documentación."""
    return [
        {
            "clave": clave,
            "topic": construir(clave, node_id),
            "qos": s.qos,
            "retained": s.retained,
            "descripcion": s.descripcion,
        }
        for clave, s in CATALOGO.items()
    ]
