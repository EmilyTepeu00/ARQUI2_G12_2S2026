"""Ingesta MQTT, persistencia Fase 3 y política de bloqueo por visión."""

import json
import math
import threading
from datetime import datetime, timezone

from src.config import config
from src.db import db
from src.logger import get_logger
from src.mqtt import topics

log = get_logger("mqtt.ingestion")


def _timestamp(payload: dict) -> datetime:
    valor = payload.get("timestamp") or payload.get("fecha")
    if isinstance(valor, (int, float)):
        # Acepta epoch en segundos o milisegundos.
        if valor > 10_000_000_000:
            valor /= 1000
        try:
            return datetime.fromtimestamp(valor, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return datetime.now(timezone.utc)
    if isinstance(valor, str):
        try:
            fecha = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
            return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _verdadero(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    return isinstance(valor, str) and valor.strip().lower() in {"true", "1", "on", "si", "sí"}


class MqttIngestor:
    """Normaliza los mensajes entrantes y coordina la lógica de sistema."""

    def __init__(self, publicador):
        self.publicador = publicador
        self._lock = threading.RLock()
        self._fotogramas_objeto = {}

    def procesar(self, topic: str, raw_payload: bytes, retenido: bool = False):
        partes = topic.split("/")
        prefijo = config.MQTT_TOPIC_PREFIX
        if len(partes) < 3 or partes[0] != prefijo:
            log.debug("Topic MQTT ignorado por no pertenecer al contrato: %s", topic)
            return

        node_id = partes[1]
        sufijo = "/".join(partes[2:])
        if sufijo == "camara/frame":
            # No almacenar JPEG/base64 en Mongo: el resultado clasificado es suficiente.
            return

        try:
            payload = json.loads(raw_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            log.warning("Payload no JSON descartado en %s", topic)
            return
        if not isinstance(payload, dict):
            log.warning("Se esperaba un objeto JSON en %s", topic)
            return

        payload = dict(payload)
        node_id_en_payload = payload.get("node_id")
        if node_id_en_payload and str(node_id_en_payload) != node_id:
            log.warning(
                "node_id del payload (%s) no coincide con el del topic (%s); se usa el topic.",
                node_id_en_payload,
                node_id,
            )
            payload["node_id_payload"] = node_id_en_payload
        payload["node_id"] = node_id
        payload["timestamp"] = _timestamp(payload)
        payload["topic"] = topic
        payload["retenido"] = retenido

        if sufijo == "sensores/lectura":
            payload.setdefault("temperatura", payload.get("temp"))
            payload.setdefault("humedad", payload.get("hum"))
            try:
                temperatura = float(payload["temperatura"])
                humedad = float(payload["humedad"])
            except (KeyError, TypeError, ValueError):
                log.warning("Lectura sin temperatura/humedad numéricas descartada en %s", topic)
                return
            if (
                not math.isfinite(temperatura)
                or not math.isfinite(humedad)
                or not -40 <= temperatura <= 100
                or not 0 <= humedad <= 100
            ):
                log.warning("Lectura fuera del rango físico descartada en %s", topic)
                return
            payload["temperatura"] = temperatura
            payload["humedad"] = humedad
            # La retenida ya se guardó antes; no duplicarla al reconectar.
            if retenido:
                db.guardar_evento_fase3("mqtt", {**payload, "tipo": "snapshot_retenido"})
            else:
                db.guardar_lectura(payload)
            if not retenido and _verdadero(payload.get("alarma")):
                self._publicar_alarma(
                    node_id, {"tipo": "umbral_sensor", "activa": True, "lectura": payload}
                )
            if not retenido and any(
                campo in payload
                for campo in (
                    "calefaccion", "calentador", "heater", "ventilacion",
                    "ventilador", "fan", "rotacion", "motor", "volteo",
                )
            ):
                self._procesar_actuadores(node_id, payload)
        elif sufijo in {"sensores/temperatura", "sensores/humedad"}:
            if not retenido:
                db.guardar_evento_fase3("mqtt", payload)
        elif sufijo == "actuadores/estado":
            db.guardar_evento_fase3("actuadores", payload)
            self._procesar_actuadores(node_id, payload)
        elif sufijo == "ml/anomalia":
            db.guardar_evento_fase3("ml", payload)
            if not retenido and self._es_anomalia(payload):
                self._publicar_alarma(
                    node_id, {"tipo": "anomalia_ml", "activa": True, "detalle": payload}
                )
        elif sufijo == "vision/resultado":
            db.guardar_evento_fase3("vision", payload)
            if not retenido:
                self._procesar_vision(node_id, payload)
        elif sufijo == "sistema/cmd":
            db.guardar_evento_fase3(
                "sistema", {**payload, "tipo": "snapshot_retenido" if retenido else "comando"}
            )
            # Retenido = orden vieja.
            if not retenido:
                self._procesar_comando(node_id, payload)
        elif sufijo == "actuadores/cmd":
            db.guardar_evento_fase3("actuadores", {**payload, "tipo": "comando"})
        elif sufijo in {"sistema/estado", "energia/consumo", "alarmas/critica"}:
            # Los publica el propio backend.
            return
        else:
            db.guardar_evento_fase3("mqtt", payload)

    def _publicar_alarma(self, node_id: str, alarma: dict):
        mensaje = {
            **alarma,
            "node_id": node_id,
            "timestamp": datetime.now(timezone.utc),
        }
        db.guardar_evento_fase3("sistema", {**mensaje, "tipo_evento": "alarma"})
        self.publicador.publicar_alarma(mensaje, node_id=node_id)

    @staticmethod
    def _es_anomalia(payload: dict) -> bool:
        for campo in ("anomalia", "es_anomalia", "anomaly", "is_anomaly"):
            if campo in payload:
                return _verdadero(payload[campo])
        resultado = str(payload.get("resultado") or payload.get("clase") or "").strip().lower()
        return resultado in {"anomalia", "anomaly", "anomalous", "atipico", "atípico"}

    def _procesar_actuadores(self, node_id: str, payload: dict):
        originales = payload.get("actuadores")
        originales = originales if isinstance(originales, dict) else payload
        alias = {
            "calefaccion": ("calefaccion", "calentador", "heater", "calor"),
            "ventilacion": ("ventilacion", "ventilador", "fan"),
            "rotacion": ("rotacion", "motor", "volteo", "rotation"),
            "luz": ("luz", "light", "lamp"),
        }
        estados = {}
        for nombre in config.ENERGY_POWER_WATTS:
            campos = alias.get(nombre, (nombre,))
            campo_estado = next((campo for campo in campos if campo in originales), None)
            if campo_estado is not None:
                estados[nombre] = _verdadero(originales[campo_estado])

        if not estados:
            log.warning("Estado MQTT de actuadores sin estados reconocidos para %s.", node_id)
            return

        consumo = db.registrar_consumo_actuadores(
            node_id,
            estados,
            config.ENERGY_POWER_WATTS,
            payload["timestamp"],
            limite_kwh=config.ENERGY_LIMIT_KWH_PER_CYCLE,
        )
        if consumo is None:
            return
        self.publicador.publicar(topics.ENERGIA_CONSUMO, consumo, node_id=node_id)
        if consumo.get("alerta_limite_nueva"):
            self._publicar_alarma(
                node_id,
                {
                    "tipo": "consumo_electrico",
                    "activa": True,
                    "energia_ciclo_kwh": consumo["energia_ciclo_kwh"],
                    "limite_ciclo_kwh": consumo["limite_ciclo_kwh"],
                    "energia_historica_kwh": consumo["energia_kwh"],
                }
            )

    def _estado(self, node_id: str) -> dict:
        return db.obtener_estado_sistema(node_id) or {
            "node_id": node_id,
            "estado": "normal",
            "bloqueado": False,
            "ciclo_activo": False,
        }

    def _guardar_y_publicar_estado(self, node_id: str, cambios: dict):
        estado = self._estado(node_id)
        estado.update(cambios)
        estado.pop("_id", None)
        estado["timestamp"] = datetime.now(timezone.utc)
        guardado = db.actualizar_estado_sistema(node_id, estado)
        mensaje = dict(guardado or estado)
        mensaje.pop("_id", None)
        self.publicador.publicar(topics.SISTEMA_ESTADO, mensaje, node_id=node_id)
        return mensaje

    def _procesar_comando(self, node_id: str, payload: dict):
        accion = str(payload.get("accion") or payload.get("comando") or "").strip().lower()
        if accion in {"iniciar", "iniciar_ciclo", "start", "iniciar ciclo"}:
            estado = self._estado(node_id)
            if estado.get("bloqueado"):
                log.warning("No se inicia el ciclo de %s: el sistema está bloqueado.", node_id)
                return
            if estado.get("ciclo_activo"):
                log.warning("Se ignora inicio duplicado del ciclo de %s.", node_id)
                return
            self._fotogramas_objeto[node_id] = 0
            consumo = db.iniciar_ciclo_energia(
                node_id,
                datetime.now(timezone.utc),
                config.ENERGY_POWER_WATTS,
                limite_kwh=config.ENERGY_LIMIT_KWH_PER_CYCLE,
            )
            if consumo is not None:
                self.publicador.publicar(topics.ENERGIA_CONSUMO, consumo, node_id=node_id)
            self._guardar_y_publicar_estado(
                node_id, {"ciclo_activo": True, "estado": "normal", "bloqueado": False}
            )
        elif accion in {"detener", "detener_ciclo", "stop", "detener ciclo"}:
            self._fotogramas_objeto[node_id] = 0
            estado = self._estado(node_id)
            self._guardar_y_publicar_estado(
                node_id,
                {
                    "ciclo_activo": False,
                    "estado": "bloqueado" if estado.get("bloqueado") else "normal",
                    "bloqueado": bool(estado.get("bloqueado")),
                },
            )
        elif accion in {"desbloquear", "unlock"}:
            rol = str(payload.get("rol") or "").strip().lower()
            autorizado = _verdadero(payload.get("autorizado")) and rol in config.SYSTEM_UNLOCK_ROLES
            if not autorizado:
                log.warning("Comando de desbloqueo rechazado para %s: no autorizado.", node_id)
                db.guardar_evento_fase3(
                    "sistema",
                    {
                        "node_id": node_id,
                        "timestamp": datetime.now(timezone.utc),
                        "tipo": "desbloqueo_rechazado",
                    },
                )
                return
            self._fotogramas_objeto[node_id] = 0
            self._guardar_y_publicar_estado(
                node_id,
                {
                    "bloqueado": False,
                    "estado": "normal",
                    "motivo": None,
                    "ciclo_activo": bool(self._estado(node_id).get("ciclo_activo")),
                },
            )
            db.guardar_evento_fase3(
                "sistema",
                {
                    "node_id": node_id,
                    "timestamp": datetime.now(timezone.utc),
                    "tipo": "desbloqueo_autorizado",
                    "rol": rol or None,
                },
            )
        else:
            log.warning("Acción sistema/cmd desconocida: %s", accion)

    def _procesar_vision(self, node_id: str, payload: dict):
        etiqueta = str(
            payload.get("clase") or payload.get("label") or payload.get("resultado") or ""
        ).strip().lower()
        confianza = payload.get(
            "confianza",
            payload.get("confidence", payload.get("probabilidad", payload.get("score", 0))),
        )
        try:
            confianza = float(confianza)
        except (TypeError, ValueError):
            confianza = 0.0
        if 1 < confianza <= 100:
            confianza /= 100
        if not 0 <= confianza <= 1:
            log.warning("Confianza de visión inválida (%s); se ignora el resultado.", confianza)
            confianza = 0

        objeto_extrano = etiqueta in {
            "objeto_extrano", "objeto extraño", "objeto-estrano", "objeto_extraño",
            "foreign_object", "extraño", "objeto_ajeno", "objeto_no_huevo",
        }
        with self._lock:
            if objeto_extrano and confianza >= config.VISION_CONFIDENCE_THRESHOLD:
                self._fotogramas_objeto[node_id] = self._fotogramas_objeto.get(node_id, 0) + 1
            else:
                self._fotogramas_objeto[node_id] = 0

            consecutivos = self._fotogramas_objeto[node_id]
            estado = self._estado(node_id)
            if (
                estado.get("ciclo_activo")
                and not estado.get("bloqueado")
                and consecutivos >= config.VISION_CONSECUTIVE_FRAMES
            ):
                motivo = {
                    "tipo": "objeto_extrano",
                    "clase": etiqueta,
                    "confianza": confianza,
                    "fotogramas_consecutivos": consecutivos,
                }
                self._guardar_y_publicar_estado(
                    node_id,
                    {
                        "bloqueado": True,
                        "estado": "bloqueado",
                        "ciclo_activo": True,
                        "motivo": motivo,
                    },
                )
                db.guardar_evento_fase3(
                    "sistema",
                    {
                        "node_id": node_id,
                        "timestamp": datetime.now(timezone.utc),
                        "tipo": "bloqueo_automatico",
                        "motivo": motivo,
                    },
                )
                self._publicar_alarma(
                    node_id,
                    {
                        "tipo": "vision_objeto_extrano",
                        "activa": True,
                        "detalle": motivo,
                    }
                )
                log.warning("Incubadora %s bloqueada por resultado de visión.", node_id)
