import threading
import time
from collections import deque
from datetime import datetime, timezone

import serial as pyserial
from serial.tools import list_ports

from src.config import config
from src.logger import get_logger
from src.models import LecturaSensor
from src.mqtt import mqtt_publisher
from src.serial import protocol
from src.serial.persistence import persistencia

log = get_logger("serial")

# Cuántas líneas se conservan para diagnóstico por API.
BUFFER_DIAGNOSTICO = 30


def _ahora():
    return datetime.now(timezone.utc)


class SerialReader:
    def __init__(self):
        self._serial_conn = None
        self._thread = None
        self._lock = threading.Lock()
        self._running = False

        self._ultima_lectura = None
        self._ultimo_evento_puerta = None
        self._alarma_previa = False
        self._alarma_activa_id = None
        self._ultimo_estado_actuadores = None
        self._ultimo_persistido_en = 0.0

        self._conectado = False
        self._puerto_actual = None
        self._ultimo_error = None
        self._buffer_lineas = deque(maxlen=BUFFER_DIAGNOSTICO)
        self._buffer_bytes = bytearray()

        self._stats = {
            "lineas_recibidas": 0,
            "lecturas_validas": 0,
            "lineas_descartadas": 0,
            "eventos_puerta": 0,
            "accesos_denegados": 0,
            "alarmas_abiertas": 0,
            "alarmas_cerradas": 0,
            "reconexiones": 0,
            "conectado_desde": None,
        }

    # Ciclo de vida
    def start(self):
        if self._running:
            log.debug("El lector serial ya se encuentra en ejecución.")
            return
        if not config.SERIAL_ENABLED:
            log.warning("SERIAL_ENABLED=false: no se abrirá el puerto serial.")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="SerialReaderThread", daemon=True
        )
        self._thread.start()
        log.info("Hilo de lectura serial iniciado.")

    def stop(self):
        self._running = False
        with self._lock:
            if self._serial_conn and self._serial_conn.is_open:
                try:
                    self._serial_conn.close()
                except Exception:
                    pass
        if self._thread:
            self._thread.join(timeout=2)
        log.info("Hilo de lectura serial detenido.")

    # Conexión
    def _candidatos(self):
        """Puerto configurado primero, luego autodetección."""
        candidatos = [config.SERIAL_PORT]
        if config.SERIAL_AUTO_DETECT:
            for p in list_ports.comports():
                if p.device not in candidatos:
                    candidatos.append(p.device)
        return [c for c in candidatos if c]

    def _conectar(self) -> bool:
        for puerto in self._candidatos():
            try:
                conn = pyserial.Serial(
                    port=puerto,
                    baudrate=config.SERIAL_BAUDRATE,
                    timeout=config.SERIAL_TIMEOUT,
                )
            except (pyserial.SerialException, OSError) as exc:
                log.debug("No se pudo abrir '%s': %s", puerto, exc)
                continue

            with self._lock:
                self._serial_conn = conn
                self._conectado = True
                self._puerto_actual = puerto
                self._ultimo_error = None
                self._buffer_bytes.clear()
                self._stats["conectado_desde"] = _ahora().isoformat()
            log.info(
                "Conectado al nodo físico en %s a %s baudios",
                puerto,
                config.SERIAL_BAUDRATE,
            )
            mqtt_publisher.publicar_status("online", origen="serial_conectado")
            return True

        with self._lock:
            self._conectado = False
            self._ultimo_error = "No se encontró un puerto serial disponible."
        return False

    def _desconectar(self, motivo: str):
        with self._lock:
            if self._serial_conn:
                try:
                    self._serial_conn.close()
                except Exception:
                    pass
            self._serial_conn = None
            self._conectado = False
            self._ultimo_error = motivo
            self._stats["reconexiones"] += 1
        log.warning("Serial desconectado (%s). Reintentando en %.0f s.",
                    motivo, config.SERIAL_RECONNECT_DELAY)
        mqtt_publisher.publicar_status("degradado", origen="serial_desconectado")

    # Bucle principal
    def _run_loop(self):
        while self._running:
            if not self._conectado:
                if not self._conectar():
                    time.sleep(config.SERIAL_RECONNECT_DELAY)
                    continue

            try:
                self._leer_bloque()
            except (pyserial.SerialException, OSError) as exc:
                self._desconectar(str(exc))
                time.sleep(config.SERIAL_RECONNECT_DELAY)
            except Exception as exc:
                # Un fallo procesando una línea jamás debe matar el hilo.
                log.exception("Error inesperado en el hilo serial: %s", exc)
                time.sleep(1)

    def _leer_bloque(self):
        """Lee lo disponible y separa por saltos de línea"""
        conn = self._serial_conn
        if conn is None or not conn.is_open or not self._running:
            return

        try:
            pendientes = conn.in_waiting or 1
            datos = conn.read(pendientes)
        except (TypeError, AttributeError):
            if self._running:
                raise
            return

        if not datos:
            return

        self._buffer_bytes.extend(datos)

        if len(self._buffer_bytes) > 8192:
            log.warning("Buffer serial desbordado sin salto de línea; se descarta.")
            self._buffer_bytes.clear()
            return

        while b"\n" in self._buffer_bytes:
            crudo, _, resto = bytes(self._buffer_bytes).partition(b"\n")
            self._buffer_bytes = bytearray(resto)
            linea = crudo.decode("utf-8", errors="ignore").strip()
            if linea:
                self._procesar_linea(linea)

    # Procesamiento
    def _procesar_linea(self, linea: str):
        with self._lock:
            self._stats["lineas_recibidas"] += 1
            self._buffer_lineas.append(
                {"timestamp": _ahora().isoformat(), "linea": linea}
            )

        try:
            mensaje = protocol.parsear_linea(linea)
        except protocol.ErrorProtocolo as exc:
            with self._lock:
                self._stats["lineas_descartadas"] += 1
            log.warning("Línea inválida descartada (%s): %s", exc, linea)
            return

        if mensaje is None:
            with self._lock:
                self._stats["lineas_descartadas"] += 1
            log.debug("Línea no reconocida, se ignora: %s", linea)
            return

        if mensaje["tipo"] == protocol.TIPO_PUERTA:
            self._procesar_evento_puerta(mensaje["datos"])
        elif mensaje["tipo"] == protocol.TIPO_ACCESO_DENEGADO:
            self._procesar_acceso_denegado(mensaje["datos"])
        else:
            self._procesar_lectura(mensaje["datos"])

    def _procesar_acceso_denegado(self, datos: dict):
        """Tarjeta RFID desconocida: queda el rastro, pero no es una apertura."""
        evento = {
            "accion": "denegado",
            "id_operador": None,
            "uid": datos.get("uid", "desconocido"),
            "metodo": "rfid",
            "autorizado": False,
            "huevos_delta": 0,
            "origen": "serial",
            "node_id": config.NODE_ID,
        }
        log.warning("Acceso denegado: tarjeta %s no registrada.", evento["uid"])

        with self._lock:
            self._stats["accesos_denegados"] += 1

        persistencia.insert_evento_puerta(dict(evento))
        mqtt_publisher.publicar_evento_puerta(evento)

    def _procesar_lectura(self, datos: dict):
        datos = protocol.derivar_actuadores(datos, config.TEMP_MIN, config.TEMP_MAX)

        lectura = LecturaSensor(
            temperatura=datos["temperatura"],
            humedad=datos["humedad"],
            sistema_encendido=datos["sistema_encendido"],
            alarma=datos["alarma"],
            espacios_libres=datos["espacios_libres"],
            calefaccion=datos.get("calefaccion", False),
            ventilacion=datos.get("ventilacion", False),
            rotacion=datos.get("rotacion", False),
            puerta_abierta=datos.get("puerta_abierta", False),
            node_id=config.NODE_ID,
        )
        lectura_dict = lectura.to_dict()

        with self._lock:
            self._ultima_lectura = lectura_dict
            self._stats["lecturas_validas"] += 1

        if self._debe_persistir():
            persistencia.insert_lectura(dict(lectura_dict))

        # MQTT
        mqtt_publisher.publicar_lectura(lectura_dict)

        actuadores = lectura.actuadores_dict()
        if actuadores != self._ultimo_estado_actuadores:
            mqtt_publisher.publicar_actuadores(actuadores)
            self._ultimo_estado_actuadores = actuadores

        self._gestionar_alarma(lectura)

    def _debe_persistir(self) -> bool:
        intervalo = config.SERIAL_MIN_PERSIST_INTERVAL
        if intervalo <= 0:
            return True
        ahora = time.monotonic()
        if ahora - self._ultimo_persistido_en >= intervalo:
            self._ultimo_persistido_en = ahora
            return True
        return False

    def _gestionar_alarma(self, lectura: LecturaSensor):
        """Ciclo de vida completo: flanco de subida abre, flanco de bajada cierra."""
        if lectura.alarma and not self._alarma_previa:
            mensaje = self._construir_mensaje_alarma(lectura)
            doc = persistencia.abrir_alarma(
                {
                    "tipo": "condicion_critica",
                    "severidad": self._severidad(lectura),
                    "mensaje": mensaje,
                    "temperatura": lectura.temperatura,
                    "humedad": lectura.humedad,
                    "node_id": config.NODE_ID,
                }
            )
            self._alarma_activa_id = doc.get("_id") if doc else None
            with self._lock:
                self._stats["alarmas_abiertas"] += 1

            mqtt_publisher.publicar_alarma(
                {
                    "estado": "activa",
                    "tipo": "condicion_critica",
                    "severidad": self._severidad(lectura),
                    "mensaje": mensaje,
                    "temperatura": lectura.temperatura,
                    "humedad": lectura.humedad,
                }
            )
            log.warning("ALARMA ACTIVADA: %s", mensaje)

        elif not lectura.alarma and self._alarma_previa:
            persistencia.cerrar_alarma(
                self._alarma_activa_id, "Condición normalizada por el nodo."
            )
            self._alarma_activa_id = None
            with self._lock:
                self._stats["alarmas_cerradas"] += 1

            mqtt_publisher.publicar_alarma(
                {
                    "estado": "resuelta",
                    "tipo": "condicion_critica",
                    "severidad": "informativa",
                    "mensaje": "Condición crítica resuelta: valores dentro de umbrales.",
                    "temperatura": lectura.temperatura,
                    "humedad": lectura.humedad,
                }
            )
            log.info("Alarma resuelta: condiciones dentro de umbrales.")

        self._alarma_previa = lectura.alarma

    def _procesar_evento_puerta(self, datos: dict):
        from src.models import EventoPuerta

        evento = EventoPuerta.build(datos, node_id=config.NODE_ID)
        evento["origen"] = "serial"
        evento["timestamp"] = _ahora()

        guardado = persistencia.insert_evento_puerta(dict(evento))

        with self._lock:
            self._ultimo_evento_puerta = {
                **evento,
                "timestamp": evento["timestamp"].isoformat(),
            }
            self._stats["eventos_puerta"] += 1

        mqtt_publisher.publicar_evento_puerta(
            {
                "accion": evento["accion"],
                "id_operador": evento["id_operador"],
                "metodo": evento["metodo"],
                "huevos_delta": evento["huevos_delta"],
                "autorizado": evento["autorizado"],
            }
        )
        log.info(
            "Puerta %s por %s (%s), huevos_delta=%s%s",
            evento["accion"],
            evento["id_operador"],
            evento["metodo"],
            evento["huevos_delta"],
            "" if guardado else " [no persistido]",
        )

    # Utilidades
    @staticmethod
    def _fuera_de_rango(lectura: LecturaSensor):
        motivos = []
        if not config.TEMP_MIN <= lectura.temperatura <= config.TEMP_MAX:
            motivos.append(f"temperatura fuera de rango ({lectura.temperatura} C)")
        if not config.HUM_MIN <= lectura.humedad <= config.HUM_MAX:
            motivos.append(f"humedad fuera de rango ({lectura.humedad} %)")
        return motivos

    @classmethod
    def _construir_mensaje_alarma(cls, lectura: LecturaSensor) -> str:
        motivos = cls._fuera_de_rango(lectura)
        if not motivos:
            motivos.append("condición crítica detectada por el nodo físico")
        return "Alarma activada: " + "; ".join(motivos)

    @classmethod
    def _severidad(cls, lectura: LecturaSensor) -> str:
        motivos = cls._fuera_de_rango(lectura)
        if len(motivos) >= 2:
            return "critica"
        return "advertencia" if motivos else "informativa"

    # Diagnóstico
    def get_estado(self) -> dict:
        with self._lock:
            return {
                "habilitado": config.SERIAL_ENABLED,
                "conectado": self._conectado,
                "puerto": self._puerto_actual,
                "baudrate": config.SERIAL_BAUDRATE,
                "ultimo_error": self._ultimo_error,
                "estadisticas": dict(self._stats),
            }

    def get_ultima_lectura(self):
        with self._lock:
            return dict(self._ultima_lectura) if self._ultima_lectura else None

    def get_ultimo_evento_puerta(self):
        with self._lock:
            return dict(self._ultimo_evento_puerta) if self._ultimo_evento_puerta else None

    def get_lineas_crudas(self, limit: int = 20):
        with self._lock:
            return list(self._buffer_lineas)[-limit:]

    def puertos_disponibles(self):
        return [
            {"device": p.device, "descripcion": p.description}
            for p in list_ports.comports()
        ]


serial_reader = SerialReader()
