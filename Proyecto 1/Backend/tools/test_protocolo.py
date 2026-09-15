import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.serial import protocol

CASOS_OK = [
    (
        "json de lectura",
        '{"tipo":"lectura","temperatura":37.8,"humedad":60,"sistema_encendido":1,'
        '"alarma":0,"espacios_libres":4,"calefaccion":0,"ventilacion":1,"rotacion":0}',
        protocol.TIPO_LECTURA,
    ),
    (
        "json sin campo tipo",
        '{"temperatura":37.1,"humedad":52,"sistema_encendido":true,"alarma":false,'
        '"espacios_libres":6}',
        protocol.TIPO_LECTURA,
    ),
    (
        "evento de puerta",
        '{"evento":"puerta","accion":"abrir","id_operador":"OP1","metodo":"rfid",'
        '"huevos_delta":-2}',
        protocol.TIPO_PUERTA,
    ),
    (
        "evento de puerta con acento en la clave",
        '{"evento":"puerta","accion":"cerrar","id_operador":"OP2","método":"huella",'
        '"huevos_delta":3}',
        protocol.TIPO_PUERTA,
    ),
    # El firmware emite esto cuando alguien pasa una tarjeta que no está
    # registrada. Antes caía en la rama de lectura y reventaba pidiendo una
    # temperatura que el mensaje nunca trae.
    (
        "tarjeta no registrada",
        '{"evento":"tarjeta_no_registrada","uid":"A1B2C3D4"}',
        protocol.TIPO_ACCESO_DENEGADO,
    ),
    (
        "tarjeta no registrada sin uid",
        '{"evento":"tarjeta_no_registrada"}',
        protocol.TIPO_ACCESO_DENEGADO,
    ),
]

CASOS_IGNORADOS = [
    ("mensaje de arranque", "SmartEgg: iniciando planificador"),
    ("línea vacía", "   "),
    ("ruido", "\x00\xff basura"),
    ("json que no es objeto", "[1,2,3]"),
    # El formato de texto plano es de la Práctica 1. El firmware del proyecto
    # emite solo JSON, así que estas líneas ya no deben interpretarse: se
    # ignoran igual que cualquier otro texto suelto del puerto serial.
    (
        "formato de texto viejo (Práctica 1)",
        "Temperatura: 37.50, Humedad: 55.00, Sistema Encendido: 1, Alarma: 0, Espacios Libres: 3",
    ),
    (
        "formato de texto viejo con espacios raros",
        "Temperatura:37.5 ,Humedad:  55 , Sistema Encendido:1, Alarma:1, Espacios Libres:0",
    ),
]

CASOS_INVALIDOS = [
    ("temperatura imposible", '{"temperatura":-999,"humedad":50,"espacios_libres":1}'),
    ("humedad fuera de rango", '{"temperatura":37,"humedad":150,"espacios_libres":1}'),
    ("espacios imposibles", '{"temperatura":37,"humedad":55,"espacios_libres":99}'),
    (
        "acción de puerta inválida",
        '{"evento":"puerta","accion":"romper","id_operador":"OP1"}',
    ),
    (
        "temperatura no numérica",
        '{"temperatura":"caliente","humedad":55,"espacios_libres":1}',
    ),
]

fallos = 0

print("== Casos válidos ==")
for nombre, linea, tipo_esperado in CASOS_OK:
    try:
        resultado = protocol.parsear_linea(linea)
    except protocol.ErrorProtocolo as exc:
        print(f"  FALLO  {nombre}: lanzó ErrorProtocolo ({exc})")
        fallos += 1
        continue
    if resultado is None or resultado["tipo"] != tipo_esperado:
        print(f"  FALLO  {nombre}: se esperaba {tipo_esperado}, llegó {resultado}")
        fallos += 1
    else:
        print(f"  OK     {nombre} -> {resultado['datos']}")

print("\n== Líneas que deben ignorarse (None) ==")
for nombre, linea in CASOS_IGNORADOS:
    try:
        resultado = protocol.parsear_linea(linea)
    except protocol.ErrorProtocolo as exc:
        print(f"  FALLO  {nombre}: lanzó ErrorProtocolo ({exc})")
        fallos += 1
        continue
    if resultado is not None:
        print(f"  FALLO  {nombre}: se esperaba None, llegó {resultado}")
        fallos += 1
    else:
        print(f"  OK     {nombre}")

print("\n== Líneas inválidas (deben lanzar ErrorProtocolo) ==")
for nombre, linea in CASOS_INVALIDOS:
    try:
        resultado = protocol.parsear_linea(linea)
    except protocol.ErrorProtocolo:
        print(f"  OK     {nombre}")
        continue
    print(f"  FALLO  {nombre}: no lanzó excepción, devolvió {resultado}")
    fallos += 1

print()
if fallos:
    print(f"RESULTADO: {fallos} fallo(s).")
    sys.exit(1)
print("RESULTADO: todas las pruebas pasaron.")
