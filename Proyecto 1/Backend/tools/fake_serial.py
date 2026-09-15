import argparse
import json
import math
import os
import random
import sys
import time

ESPACIOS_TOTALES = 6
OPERADORES = ["OP1", "OP2"]
METODOS = ["rfid", "huella", "llave"]


def construir_lectura(t: float, escenario: str) -> dict:
    """Genera una lectura verosímil: onda suave + ruido."""
    base_temp = 37.5 + 0.45 * math.sin(t / 12.0)
    base_hum = 57.0 + 4.0 * math.sin(t / 17.0)

    if escenario == "alarma":
        # Deriva sostenida hacia fuera de umbral y regreso.
        base_temp += 1.6 * math.sin(t / 6.0)
        base_hum += 9.0 * math.sin(t / 9.0)
    elif escenario == "caotico":
        base_temp += random.uniform(-2.5, 2.5)
        base_hum += random.uniform(-15, 15)

    temperatura = round(base_temp + random.uniform(-0.12, 0.12), 2)
    humedad = round(max(0.0, min(100.0, base_hum + random.uniform(-0.5, 0.5))), 2)

    fuera_temp = not (37.0 <= temperatura <= 38.0)
    fuera_hum = not (50.0 <= humedad <= 65.0)

    return {
        "tipo": "lectura",
        "temperatura": temperatura,
        "humedad": humedad,
        "sistema_encendido": 1,
        "alarma": 1 if (fuera_temp or fuera_hum) else 0,
        "espacios_libres": construir_lectura.espacios,
        "calefaccion": 1 if temperatura < 37.0 else 0,
        "ventilacion": 1 if temperatura > 38.0 else 0,
        "rotacion": 1 if int(t) % 20 < 2 else 0,
        "puerta_abierta": 0,
    }


construir_lectura.espacios = 2


def formatear(lectura: dict) -> str:
    # El firmware emite JSON y el parser solo entiende JSON. El formato de texto
    # plano de la Práctica 1 se quitó: generaba líneas que el backend descarta,
    # y eso hacía perder tiempo buscando el fallo en el lado equivocado.
    return json.dumps(lectura, ensure_ascii=False)


def construir_evento_puerta(abierta: bool) -> dict:
    """Alterna abrir/cerrar; al cerrar mueve huevos y ajusta los espacios."""
    if abierta:
        delta = random.choice([-2, -1, 1, 2])
        libres = construir_lectura.espacios - delta
        construir_lectura.espacios = max(0, min(ESPACIOS_TOTALES, libres))
        return {
            "evento": "puerta",
            "accion": "cerrar",
            "id_operador": construir_evento_puerta.operador,
            "metodo": construir_evento_puerta.metodo,
            "huevos_delta": delta,
            "autorizado": 1,
        }

    construir_evento_puerta.operador = random.choice(OPERADORES)
    construir_evento_puerta.metodo = random.choice(METODOS)
    return {
        "evento": "puerta",
        "accion": "abrir",
        "id_operador": construir_evento_puerta.operador,
        "metodo": construir_evento_puerta.metodo,
        "huevos_delta": 0,
        "autorizado": 1,
    }


construir_evento_puerta.operador = "OP1"
construir_evento_puerta.metodo = "rfid"


def abrir_salida(args):
    """Devuelve (escribir, cerrar, descripcion)."""
    if args.archivo:
        f = open(args.archivo, "a", encoding="utf-8")

        def escribir(linea):
            f.write(linea + "\n")
            f.flush()

        return escribir, f.close, f"archivo {args.archivo}"

    try:
        import pty
    except ImportError:
        print(
            "Este sistema no soporta pty. Use --archivo o instale com0com en Windows.",
            file=sys.stderr,
        )
        sys.exit(1)

    maestro, esclavo = pty.openpty()
    nombre = os.ttyname(esclavo)

    # El numero del pty (/dev/pts/0, /dev/pts/1, ...) NO es estable: depende de
    # que otra cosa haya pedido un pty antes, y cada sesion `docker exec` con
    # terminal se lleva uno. Si el backend tiene SERIAL_PORT=/dev/pts/0 fijo,
    # termina escuchando un pty que no es el nuestro y no recibe nada.
    #
    # Por eso se crea un enlace con nombre fijo: el backend apunta siempre ahi
    # y no importa que numero le haya tocado al pty.
    enlace = args.enlace
    if enlace:
        try:
            if os.path.islink(enlace) or os.path.exists(enlace):
                os.unlink(enlace)
            os.symlink(nombre, enlace)
            # El backend corre como otro usuario dentro del contenedor y tiene
            # que poder leer el pty.
            os.chmod(nombre, 0o666)
        except OSError as exc:
            print(f"No se pudo crear el enlace {enlace}: {exc}", file=sys.stderr)
            enlace = None

    def escribir(linea):
        os.write(maestro, (linea + "\r\n").encode("utf-8"))

    def cerrar():
        if enlace:
            try:
                os.unlink(enlace)
            except OSError:
                pass
        os.close(maestro)
        os.close(esclavo)

    descripcion = f"{enlace} -> {nombre}" if enlace else nombre
    return escribir, cerrar, descripcion


def main():
    parser = argparse.ArgumentParser(description="Simulador serial del nodo SmartEgg")
    parser.add_argument("--intervalo", type=float, default=2.0)
    parser.add_argument(
        "--escenario", choices=["normal", "alarma", "caotico"], default="normal"
    )
    parser.add_argument(
        "--puerta-cada",
        type=int,
        default=15,
        help="Cada cuántas lecturas se emite un evento de puerta (0 = nunca).",
    )
    parser.add_argument("--archivo", help="Escribir a un archivo en vez de un pty.")
    parser.add_argument(
        "--enlace",
        default="/tmp/smartegg-serial",
        help="Ruta fija que apunta al pty, para que SERIAL_PORT no dependa del "
             "numero que le toque. Vacio para no crearlo.",
    )
    args = parser.parse_args()

    escribir, cerrar, destino = abrir_salida(args)

    print(f"Puerto virtual listo: {destino}")
    print(f"Escenario: {args.escenario}")
    print("Configure el backend con:")
    print(f"  SERIAL_PORT={args.enlace or destino}")
    print("  SERIAL_AUTO_DETECT=false")
    print("Ctrl+C para detener.\n")

    escribir("SmartEgg: iniciando planificador")

    contador = 0
    puerta_abierta = False
    t = 0.0

    try:
        while True:
            lectura = construir_lectura(t, args.escenario)
            lectura["puerta_abierta"] = 1 if puerta_abierta else 0
            escribir(formatear(lectura))

            contador += 1
            t += args.intervalo

            if args.puerta_cada and contador % args.puerta_cada == 0:
                evento = construir_evento_puerta(puerta_abierta)
                puerta_abierta = not puerta_abierta
                escribir(json.dumps(evento, ensure_ascii=False))
                print(f"  -> evento de puerta: {evento['accion']} ({evento['id_operador']})")

            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")
    finally:
        cerrar()


if __name__ == "__main__":
    main()
