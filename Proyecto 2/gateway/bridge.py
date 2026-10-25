#!/usr/bin/env python3
"""Puente USB serial/cámara a MQTT para SmartEgg."""
import argparse
import json
import logging
import math
import os
import queue
import random
import signal
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger("puente")
ACTUADORES = ("calefaccion", "ventilacion", "rotacion")
ESTADO = lambda e: json.dumps({"estado": e})  # el backend solo acepta JSON
BOOLEANOS = (*ACTUADORES, "sistema_encendido", "alarma", "puerta_abierta", "bloqueado")


def normalizar(datos):
    if not isinstance(datos, dict):
        raise ValueError("Se esperaba un objeto")
    datos = dict(datos)
    if "ventilador" in datos:
        datos["ventilacion"] = datos.pop("ventilador")
    for campo in BOOLEANOS:
        if campo in datos:
            if datos[campo] not in (0, 1, False, True):
                raise ValueError(f"Booleano inválido: {campo}")
            datos[campo] = bool(datos[campo])
    if "evento" not in datos:
        for campo, minimo, maximo in (("temperatura", -40, 100), ("humedad", 0, 100)):
            valor = float(datos[campo])
            if not math.isfinite(valor) or not minimo <= valor <= maximo:
                raise ValueError(f"Lectura inválida: {campo}")
            datos[campo] = valor
    datos["timestamp"] = datetime.now(timezone.utc).isoformat()
    return datos


def traducir(sufijo, datos, simulado=False):
    if not isinstance(datos, dict):
        raise ValueError("Comando no es objeto")
    if sufijo == "sistema/estado" and datos.get("estado") in ("normal", "bloqueado"):
        return {"cmd": "sistema", "estado": datos["estado"]}
    nombres = {"calefaccion": "calefaccion", "ventilacion": "ventilador"}
    if simulado:
        nombres["rotacion"] = "rotacion"
    if sufijo == "actuadores/cmd" and datos.get("actuador") in nombres and datos.get("accion") in ("on", "off"):
        return {"cmd": "actuador", "nombre": nombres[datos["actuador"]], "accion": datos["accion"]}
    raise ValueError("Comando inválido o actuador no soportado por el firmware")


def aplicar_simulado(estado, comando, bloqueado):
    if comando["cmd"] == "sistema":
        bloqueado = comando["estado"] == "bloqueado"
        if bloqueado:
            estado.update(dict.fromkeys(ACTUADORES, False))
    elif not bloqueado:
        nombre = comando["nombre"].replace("ventilador", "ventilacion")
        estado[nombre] = comando["accion"] == "on"
    return bloqueado


def main():
    import paho.mqtt.client as mqtt
    import serial

    parser = argparse.ArgumentParser(description=__doc__)
    for nombre, defecto in (("mqtt-host", "localhost"), ("mqtt-port", "1883"), ("mqtt-user", ""),
                            ("mqtt-pass", ""), ("node-id", "incubadora-01"), ("serial-port", "/dev/ttyACM0")):
        parser.add_argument("--" + nombre, default=os.getenv(nombre.upper().replace("-", "_"), defecto))
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--no-camera", action="store_true")
    parser.add_argument("--estado-intervalo", type=float, default=10)
    args = parser.parse_args()
    if not args.node_id or any(c in args.node_id for c in "/+#") or args.estado_intervalo <= 0:
        parser.error("Nodo o intervalo inválido")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    detener = threading.Event()
    for senal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(senal, lambda *_: detener.set())
    pendientes = queue.Queue(maxsize=100)
    base = f"smartegg/{args.node_id}/"
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"puente-{args.node_id}")
    cliente.max_queued_messages_set(100)
    if args.mqtt_user:
        cliente.username_pw_set(args.mqtt_user, args.mqtt_pass)
    cliente.will_set(base + "status", ESTADO("offline"), qos=1, retain=True)

    def conectado(cli, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("Conexión rechazada: %s", reason_code)
            return
        cli.subscribe([(base + "actuadores/cmd", 1), (base + "sistema/estado", 1)])
        cli.publish(base + "status", ESTADO("online"), qos=1, retain=True)
        log.info("MQTT conectado: %s", base)

    def mensaje(cli, userdata, msg):
        sufijo = msg.topic[len(base):]
        if sufijo == "actuadores/cmd" and msg.retain:
            return
        try:
            pendientes.put_nowait(traducir(sufijo, json.loads(msg.payload), args.simulate))
        except (ValueError, TypeError, queue.Full) as error:
            log.warning("Comando descartado: %s", error)

    cliente.on_connect = conectado
    cliente.on_message = mensaje
    puerto = camara = None
    estado = dict.fromkeys(ACTUADORES, False)
    bloqueado = False
    sim_t, sim_h = 37.5, 57.0  # caminata aleatoria: un DHT real cambia poco entre lecturas
    anterior, ultimo_estado, ultima_lectura, ultimo_frame = None, 0, 0, 0
    buffer = b""
    try:
        if not args.no_camera:
            import cv2
            camara = cv2.VideoCapture(args.camera)
            if not camara.isOpened():
                raise RuntimeError("No se pudo abrir la cámara; use --no-camera")
            camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # sin cola: read() no entrega fotogramas de hace segundos
        cliente.connect_async(args.mqtt_host, int(args.mqtt_port), 30)
        cliente.loop_start()
        ultimo_sistema, reintento, reenviar = None, 0, None
        while not detener.is_set():
            ahora = time.monotonic()
            # Arduino reiniciado o desconectado: reabrir el puerto cada 2 s sin cortar MQTT ni la cámara.
            if not args.simulate and puerto is None and ahora - reintento >= 2:
                reintento = ahora
                try:
                    puerto = serial.Serial(args.serial_port, 9600, timeout=0.1, write_timeout=2)
                    reenviar = ahora + 2.5  # al abrir USB el Arduino arranca de cero y olvida el bloqueo
                    log.info("Serial reconectado: %s", args.serial_port)
                except serial.SerialException:
                    pass
            datos = None
            try:
                if puerto and reenviar and ahora >= reenviar:
                    reenviar = None
                    if ultimo_sistema:
                        puerto.write((json.dumps(ultimo_sistema) + "\n").encode())
                while not pendientes.empty():
                    comando = pendientes.get_nowait()
                    if comando["cmd"] == "sistema":
                        ultimo_sistema = comando
                    if puerto:
                        puerto.write((json.dumps(comando) + "\n").encode())
                    elif args.simulate:
                        bloqueado = aplicar_simulado(estado, comando, bloqueado)
                if puerto:
                    buffer += puerto.read_until(b"\n", 4096)
                    if len(buffer) > 4096:
                        raise ValueError("Línea serial demasiado larga")
                    if buffer.endswith(b"\n"):
                        try:
                            datos = normalizar(json.loads(buffer))
                        except (ValueError, TypeError, KeyError) as error:
                            log.warning("Línea descartada: %s", error)
                        buffer = b""
            except serial.SerialException as error:
                log.warning("Serial perdido (%s); reintentando cada 2 s...", error)
                puerto.close()
                puerto, buffer = None, b""
            if args.simulate and ahora - ultima_lectura >= 1:
                sim_t += random.uniform(-0.03, 0.03) + (37.5 - sim_t) * 0.05
                sim_h += random.uniform(-0.2, 0.2) + (57.0 - sim_h) * 0.05
                datos = normalizar({**estado, "temperatura": round(sim_t, 2),
                                    "humedad": round(sim_h, 2), "bloqueado": bloqueado,
                                    "sistema_encendido": True, "alarma": bloqueado, "espacios_libres": 2,
                                    "puerta_abierta": False, "id_operador_actual": None})
                ultima_lectura = ahora
            if datos and cliente.is_connected():
                evento = "evento" in datos
                cliente.publish(base + ("puerta/evento" if evento else "sensores/lectura"), json.dumps(datos), qos=1)
                if not evento:
                    actual = {k: datos[k] for k in ACTUADORES if k in datos}
                    if actual and (actual != anterior or ahora - ultimo_estado >= args.estado_intervalo):
                        cliente.publish(base + "actuadores/estado", json.dumps({**actual, "timestamp": datos["timestamp"]}), qos=1, retain=True)
                        anterior, ultimo_estado = actual, ahora
            if camara and ahora - ultimo_frame >= 1.5:
                ultimo_frame = ahora
                camara.grab()  # descarta el fotograma que quedó guardado desde la lectura anterior
                ok, frame = camara.read()
                if ok:
                    alto, ancho = frame.shape[:2]
                    frame = cv2.resize(frame, (320, max(1, round(alto * 320 / ancho))))
                    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ok and cliente.is_connected():
                        cliente.publish(base + "camara/frame", jpeg.tobytes())
                else:
                    log.warning("No se pudo leer la cámara")
            detener.wait(0.02)
    finally:
        if cliente.is_connected():
            cliente.publish(base + "status", ESTADO("offline"), qos=1, retain=True).wait_for_publish(timeout=2)
        cliente.disconnect()
        cliente.loop_stop()
        if puerto:
            puerto.close()
        if camara:
            camara.release()


if __name__ == "__main__":
    main()
