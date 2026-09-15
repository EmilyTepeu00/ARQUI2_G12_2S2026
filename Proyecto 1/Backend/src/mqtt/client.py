import json
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from src.config import config
from src.logger import get_logger
from src.mqtt import topics

log = get_logger("mqtt")


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(valor):
    if isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


class MqttPublisher:
    def __init__(self):
        self._client = None
        self._lock = threading.Lock()
        self._conectado = False
        self._iniciado = False
        self._ultimo_error = None
        self._node_id = config.NODE_ID
        self._stats = {
            "publicados": 0,
            "fallidos": 0,
            "reconexiones": 0,
            "ultimo_publicado_en": None,
            "ultimo_topic": None,
        }

    # Ciclo de vida
    def init(self):
        """Arranca el cliente. Llamarla dos veces no duplica hilos."""
        if self._iniciado:
            log.debug("El cliente MQTT ya estaba iniciado.")
            return
        if not config.MQTT_ENABLED:
            log.warning("MQTT_ENABLED=false: el backend no publicará telemetría.")
            return

        client_id = f"{config.MQTT_CLIENT_ID}-{self._node_id}"
        try:
            self._client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
                protocol=mqtt.MQTTv311,
                clean_session=True,
            )
            self._api_v2 = True
        except AttributeError:
            self._client = mqtt.Client(
                client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True
            )
            self._api_v2 = False

        if config.MQTT_USERNAME:
            self._client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

        topic_status = topics.construir(topics.STATUS, self._node_id)
        lwt = json.dumps(
            {
                "node_id": self._node_id,
                "estado": "offline",
                "origen": "lwt",
                "conectado_desde": _ahora_iso(),
            }
        )
        self._client.will_set(
            topic_status,
            payload=lwt,
            qos=topics.spec(topics.STATUS).qos,
            retain=True,
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(
            min_delay=config.MQTT_RECONNECT_MIN_DELAY,
            max_delay=config.MQTT_RECONNECT_MAX_DELAY,
        )

        try:
            self._client.connect_async(
                config.MQTT_HOST, config.MQTT_PORT, config.MQTT_KEEPALIVE
            )
        except Exception as exc:
            self._ultimo_error = str(exc)
            log.error("No se pudo iniciar la conexión al broker: %s", exc)

        self._client.loop_start()
        self._iniciado = True
        log.info(
            "Cliente MQTT iniciado -> %s:%s (client_id=%s, LWT=%s)",
            config.MQTT_HOST,
            config.MQTT_PORT,
            client_id,
            topic_status,
        )

    def stop(self):
        """Publica un offline limpio y cierra la conexión."""
        if not self._iniciado or self._client is None:
            return
        self.publicar_status("offline", origen="apagado_controlado")
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as exc:
            log.warning("Error al cerrar el cliente MQTT: %s", exc)
        self._iniciado = False
        self._conectado = False
        log.info("Cliente MQTT detenido.")

    # Callbacks
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        codigo = getattr(reason_code, "value", reason_code)
        if codigo == 0:
            with self._lock:
                if self._conectado is False and self._stats["publicados"] > 0:
                    self._stats["reconexiones"] += 1
                self._conectado = True
                self._ultimo_error = None
            log.info("Conectado al broker MQTT %s:%s", config.MQTT_HOST, config.MQTT_PORT)
            self.publicar_status("online", origen="conexion")
        else:
            with self._lock:
                self._conectado = False
                self._ultimo_error = f"Conexión rechazada por el broker (código {codigo})"
            log.error("El broker rechazó la conexión (código %s).", codigo)

    def _on_disconnect(self, client, userdata, *args):
        codigo = args[0] if args else 0
        codigo = getattr(codigo, "value", codigo)
        with self._lock:
            self._conectado = False
            if codigo != 0:
                self._ultimo_error = f"Desconexión inesperada (código {codigo})"
        if codigo != 0:
            log.warning(
                "Desconectado del broker (código %s). paho reintentará solo.", codigo
            )
        else:
            log.info("Desconectado del broker de forma limpia.")

    # Publicación
    def publicar(self, clave: str, payload: dict, node_id: str = None) -> bool:
        """Publica en el topic asociado a `clave`"""
        if not config.MQTT_ENABLED or self._client is None:
            return False

        spec = topics.spec(clave)
        topic = topics.construir(clave, node_id or self._node_id)
        cuerpo = dict(payload)
        cuerpo.setdefault("node_id", node_id or self._node_id)
        cuerpo.setdefault("timestamp", _ahora_iso())

        try:
            mensaje = json.dumps(cuerpo, default=_json_safe, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            log.error("Payload no serializable para %s: %s", topic, exc)
            with self._lock:
                self._stats["fallidos"] += 1
            return False

        try:
            info = self._client.publish(
                topic, payload=mensaje, qos=spec.qos, retain=spec.retained
            )
        except Exception as exc:
            log.error("Error al publicar en %s: %s", topic, exc)
            with self._lock:
                self._stats["fallidos"] += 1
                self._ultimo_error = str(exc)
            return False

        exito = info.rc == mqtt.MQTT_ERR_SUCCESS
        with self._lock:
            if exito:
                self._stats["publicados"] += 1
                self._stats["ultimo_publicado_en"] = _ahora_iso()
                self._stats["ultimo_topic"] = topic
            else:
                self._stats["fallidos"] += 1
        if exito:
            log.debug("-> %s (qos=%s retain=%s) %s", topic, spec.qos, spec.retained, mensaje)
        else:
            log.warning("Publicación fallida en %s (rc=%s).", topic, info.rc)
        return exito

    # Atajos semánticos
    def publicar_lectura(self, lectura: dict, node_id: str = None):
        """Telemetria y valores para Grafana."""
        self.publicar(topics.SENSORES_LECTURA, lectura, node_id)

        if config.MQTT_PUBLISH_SPLIT_SENSORS:
            if lectura.get("temperatura") is not None:
                self.publicar(
                    topics.SENSORES_TEMPERATURA,
                    {"valor": lectura["temperatura"], "unidad": "C"},
                    node_id,
                )
            if lectura.get("humedad") is not None:
                self.publicar(
                    topics.SENSORES_HUMEDAD,
                    {"valor": lectura["humedad"], "unidad": "%"},
                    node_id,
                )

    def publicar_actuadores(self, estado: dict, node_id: str = None):
        self.publicar(topics.ACTUADORES_ESTADO, estado, node_id)

    def publicar_alarma(self, alarma: dict, node_id: str = None):
        self.publicar(topics.ALARMAS_CRITICA, alarma, node_id)

    def publicar_evento_puerta(self, evento: dict, node_id: str = None):
        self.publicar(topics.PUERTA_EVENTO, evento, node_id)

    def publicar_status(self, estado: str, origen: str = "backend", node_id: str = None):
        self.publicar(
            topics.STATUS, {"estado": estado, "origen": origen}, node_id
        )

    # Diagnóstico
    def estado(self) -> dict:
        with self._lock:
            stats = dict(self._stats)
            conectado = self._conectado
            error = self._ultimo_error
        return {
            "habilitado": config.MQTT_ENABLED,
            "conectado": conectado,
            "broker": f"{config.MQTT_HOST}:{config.MQTT_PORT}",
            "client_id": f"{config.MQTT_CLIENT_ID}-{self._node_id}",
            "node_id": self._node_id,
            "ultimo_error": error,
            "estadisticas": stats,
            "topics": topics.documentar(self._node_id),
        }


mqtt_publisher = MqttPublisher()
