import re
import threading
import time
from datetime import datetime, timezone
import serial
from serial.tools import list_ports
from app.config import config
from app.database import db
from app.models import LecturaSensor

LINEA_REGEX = re.compile(
    r"Temperatura:\s*(?P<temperatura>-?\d+(?:\.\d+)?)\s*,\s*"
    r"Humedad:\s*(?P<humedad>-?\d+(?:\.\d+)?)\s*,\s*"
    r"Sistema Encendido:\s*(?P<sistema>[01])\s*,\s*"
    r"Alarma:\s*(?P<alarma>[01])\s*,\s*"
    r"Espacios Libres:\s*(?P<espacios>\d+)",
    re.IGNORECASE,
)


class SerialReader:
    def __init__(self):
        self._serial_conn = None
        self._thread = None
        self._lock = threading.Lock()
        self._running = False
        self._ultima_lectura = None
        self._alarma_previa = False
        self._conectado = False
        self._puerto_actual = None
        self._ultimo_error = None

    def start(self):
        if self._running:
            print("El lector serial ya se encuentra en ejecución.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="SerialReaderThread", daemon=True
        )
        self._thread.start()
        print("Hilo de lectura serial iniciado.")

    def stop(self):
        self._running = False
        with self._lock:
            if self._serial_conn and self._serial_conn.is_open:
                self._serial_conn.close()
        if self._thread:
            self._thread.join(timeout=2)
        print("Hilo de lectura serial detenido.")

    def _detectar_puerto(self):
        puertos = list(list_ports.comports())
        if not puertos:
            return None
        return puertos[0].device

    def _conectar(self):
        puerto = config.SERIAL_PORT
        try:
            conn = serial.Serial(
                port=puerto,
                baudrate=config.SERIAL_BAUDRATE,
                timeout=config.SERIAL_TIMEOUT,
            )
            with self._lock:
                self._serial_conn = conn
                self._conectado = True
                self._puerto_actual = puerto
                self._ultimo_error = None
            print(f"Conectado al Arduino en el puerto {puerto}")
            return True
        except serial.SerialException as exc:
            print(f"No se pudo abrir el puerto configurado '{puerto}': {exc}")

        if config.SERIAL_AUTO_DETECT:
            puerto_detectado = self._detectar_puerto()
            if puerto_detectado and puerto_detectado != puerto:
                try:
                    conn = serial.Serial(
                        port=puerto_detectado,
                        baudrate=config.SERIAL_BAUDRATE,
                        timeout=config.SERIAL_TIMEOUT,
                    )
                    with self._lock:
                        self._serial_conn = conn
                        self._conectado = True
                        self._puerto_actual = puerto_detectado
                        self._ultimo_error = None
                    print(
                        f"Conectado al Arduino en el puerto autodetectado {puerto_detectado}"
                    )
                    return True
                except serial.SerialException as exc:
                    print(
                        f"Falló la conexión al puerto autodetectado '{puerto_detectado}': {exc}"
                    )

        with self._lock:
            self._conectado = False
            self._ultimo_error = "No se encontró un puerto serial disponible."
        return False

    def _run_loop(self):
        while self._running:
            if not self._conectado:
                conectado = self._conectar()
                if not conectado:
                    time.sleep(config.SERIAL_RECONNECT_DELAY)
                    continue
            try:
                linea_bytes = self._serial_conn.readline()
                if not linea_bytes:
                    continue
                linea = linea_bytes.decode("utf-8", errors="ignore").strip()
                if not linea:
                    continue
                self._procesar_linea(linea)
            except (serial.SerialException, OSError) as exc:
                print(f"Error de comunicación serial: {exc}")
                with self._lock:
                    if self._serial_conn:
                        try:
                            self._serial_conn.close()
                        except Exception:
                            pass
                    self._conectado = False
                    self._ultimo_error = str(exc)
                time.sleep(config.SERIAL_RECONNECT_DELAY)

    def _procesar_linea(self, linea: str):
        match = LINEA_REGEX.search(linea)
        if not match:
            print(f"Línea serial no reconocida, se ignora: {linea}")
            return
        try:
            lectura = LecturaSensor(
                temperatura=float(match.group("temperatura")),
                humedad=float(match.group("humedad")),
                sistema_encendido=bool(int(match.group("sistema"))),
                alarma=bool(int(match.group("alarma"))),
                espacios_libres=int(match.group("espacios")),
            )
        except (ValueError, TypeError) as exc:
            print(f"No se pudo interpretar la línea serial '{linea}': {exc}")
            return

        lectura_dict = lectura.to_dict()
        with self._lock:
            self._ultima_lectura = lectura_dict

        # Se pasa una copia porque pymongo muta el dict recibido para
        # inyectarle el ObjectId generado (`_id`); si no se copia, ese
        # ObjectId termina en self._ultima_lectura y rompe la serialización
        # JSON de /actual, /estado y /stream en cuanto llega la primera lectura.
        db.guardar_lectura(dict(lectura_dict))

        if lectura.alarma and not self._alarma_previa:
            db.registrar_alarma(
                {
                    "tipo": "condicion_critica",
                    "mensaje": self._construir_mensaje_alarma(lectura),
                    "temperatura": lectura.temperatura,
                    "humedad": lectura.humedad,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            print(f"Alarma detectada: {self._construir_mensaje_alarma(lectura)}")
        self._alarma_previa = lectura.alarma

    @staticmethod
    def _construir_mensaje_alarma(lectura: LecturaSensor):
        motivos = []
        if (
            lectura.temperatura < config.TEMP_MIN
            or lectura.temperatura > config.TEMP_MAX
        ):
            motivos.append(f"temperatura fuera de rango ({lectura.temperatura} C)")
        if lectura.humedad < config.HUM_MIN or lectura.humedad > config.HUM_MAX:
            motivos.append(f"humedad fuera de rango ({lectura.humedad} %)")
        if not motivos:
            motivos.append("condición crítica detectada por el nodo físico")
        return "Alarma activada: " + "; ".join(motivos)

    def get_estado(self):
        with self._lock:
            return {
                "conectado": self._conectado,
                "puerto": self._puerto_actual,
                "ultimo_error": self._ultimo_error,
            }

    def get_ultima_lectura(self):
        with self._lock:
            return dict(self._ultima_lectura) if self._ultima_lectura else None


serial_reader = SerialReader()
