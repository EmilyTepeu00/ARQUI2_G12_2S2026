from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId


def serialize_doc(doc):
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


def serialize_list(docs):
    return [serialize_doc(d) for d in docs]


def to_object_id(raw_id):
    if raw_id is None:
        return None
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        return raw_id


class LecturaSensor:
    __slots__ = (
        "temperatura",
        "humedad",
        "sistema_encendido",
        "alarma",
        "espacios_libres",
        "calefaccion",
        "ventilacion",
        "rotacion",
        "puerta_abierta",
        "node_id",
        "timestamp",
    )

    def __init__(
        self,
        temperatura: float,
        humedad: float,
        sistema_encendido: bool,
        alarma: bool,
        espacios_libres: int,
        calefaccion: bool = False,
        ventilacion: bool = False,
        rotacion: bool = False,
        puerta_abierta: bool = False,
        node_id: str = None,
        timestamp: datetime = None,
    ):
        self.temperatura = temperatura
        self.humedad = humedad
        self.sistema_encendido = sistema_encendido
        self.alarma = alarma
        self.espacios_libres = espacios_libres
        self.calefaccion = calefaccion
        self.ventilacion = ventilacion
        self.rotacion = rotacion
        self.puerta_abierta = puerta_abierta
        self.node_id = node_id
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "temperatura": self.temperatura,
            "humedad": self.humedad,
            "sistema_encendido": self.sistema_encendido,
            "alarma": self.alarma,
            "espacios_libres": self.espacios_libres,
            "calefaccion": self.calefaccion,
            "ventilacion": self.ventilacion,
            "rotacion": self.rotacion,
            "puerta_abierta": self.puerta_abierta,
            "node_id": self.node_id,
            "timestamp": self.timestamp,
        }

    def actuadores_dict(self):
        return {
            "calefaccion": self.calefaccion,
            "ventilacion": self.ventilacion,
            "rotacion": self.rotacion,
            "sistema_encendido": self.sistema_encendido,
            "puerta_abierta": self.puerta_abierta,
        }


class LoteHuevo:
    CAMPOS_REQUERIDOS = ("codigo", "nombre_lote", "cantidad_huevos")
    ESTADOS_VALIDOS = {"incubando", "eclosionado", "descartado"}

    @staticmethod
    def validar(data: dict):
        errores = []
        if not isinstance(data, dict):
            return ["El cuerpo de la petición debe ser un objeto JSON."]

        for campo in LoteHuevo.CAMPOS_REQUERIDOS:
            if not data.get(campo):
                errores.append(f"El campo '{campo}' es obligatorio.")

        cantidad = data.get("cantidad_huevos")
        if cantidad is not None:
            try:
                if int(cantidad) <= 0:
                    errores.append("cantidad_huevos debe ser un entero positivo.")
            except (TypeError, ValueError):
                errores.append("cantidad_huevos debe ser un número entero.")

        raza = data.get("raza")
        if raza is not None and not isinstance(raza, str):
            errores.append("raza debe ser una cadena de texto.")

        estado = data.get("estado")
        if estado is not None and estado not in LoteHuevo.ESTADOS_VALIDOS:
            errores.append(
                f"estado debe ser uno de: {', '.join(sorted(LoteHuevo.ESTADOS_VALIDOS))}"
            )

        return errores

    @staticmethod
    def build(data: dict):
        return {
            "codigo": data.get("codigo"),
            "nombre_lote": data.get("nombre_lote"),
            "cantidad_huevos": int(data.get("cantidad_huevos")),
            "raza": data.get("raza", ""),
            "responsable": data.get("responsable", ""),
            "observaciones": data.get("observaciones", ""),
            "estado": data.get("estado", "incubando"),
        }


class Operador:
    """Operador 1 / 2 y administrador"""

    CAMPOS_REQUERIDOS = ("id_operador", "nombre")
    ROLES_VALIDOS = {"operador_1", "operador_2", "administrador"}
    GENEROS_VALIDOS = {"masculino", "femenino", "otro", "no_especificado"}

    @staticmethod
    def validar(data: dict):
        errores = []
        if not isinstance(data, dict):
            return ["El cuerpo de la petición debe ser un objeto JSON."]

        for campo in Operador.CAMPOS_REQUERIDOS:
            if not data.get(campo):
                errores.append(f"El campo '{campo}' es obligatorio.")

        edad = data.get("edad")
        if edad is not None:
            try:
                edad_num = int(edad)
                if edad_num < 0 or edad_num > 120:
                    errores.append("edad debe estar entre 0 y 120.")
            except (TypeError, ValueError):
                errores.append("edad debe ser un número entero.")

        genero = data.get("genero")
        if genero is not None and genero not in Operador.GENEROS_VALIDOS:
            errores.append(
                f"genero debe ser uno de: {', '.join(sorted(Operador.GENEROS_VALIDOS))}"
            )

        rol = data.get("rol")
        if rol is not None and rol not in Operador.ROLES_VALIDOS:
            errores.append(
                f"rol debe ser uno de: {', '.join(sorted(Operador.ROLES_VALIDOS))}"
            )

        metodo = data.get("metodo_acceso")
        if metodo is not None and metodo not in EventoPuerta.METODOS_VALIDOS:
            errores.append(
                "metodo_acceso debe ser uno de: "
                f"{', '.join(sorted(EventoPuerta.METODOS_VALIDOS))}"
            )

        return errores

    @staticmethod
    def build(data: dict):
        return {
            "id_operador": str(data.get("id_operador")).strip(),
            "nombre": data.get("nombre"),
            "edad": int(data["edad"]) if data.get("edad") not in (None, "") else None,
            "genero": data.get("genero", "no_especificado"),
            "rol": data.get("rol", "operador_1"),
            "metodo_acceso": data.get("metodo_acceso", "rfid"),
            "activo": bool(data.get("activo", True)),
        }


class EventoPuerta:
    """Apertura/cierre de la incubadora con identificación del operador."""

    ACCIONES_VALIDAS = {"abrir", "cerrar"}
    METODOS_VALIDOS = {"rfid", "huella", "llave", "manual"}

    @staticmethod
    def validar(data: dict):
        errores = []
        if not isinstance(data, dict):
            return ["El cuerpo de la petición debe ser un objeto JSON."]

        accion = data.get("accion")
        if accion not in EventoPuerta.ACCIONES_VALIDAS:
            errores.append("accion debe ser 'abrir' o 'cerrar'.")

        if not data.get("id_operador"):
            errores.append("El campo 'id_operador' es obligatorio.")

        metodo = data.get("metodo")
        if metodo is not None and metodo not in EventoPuerta.METODOS_VALIDOS:
            errores.append(
                f"metodo debe ser uno de: {', '.join(sorted(EventoPuerta.METODOS_VALIDOS))}"
            )

        delta = data.get("huevos_delta")
        if delta is not None:
            try:
                int(delta)
            except (TypeError, ValueError):
                errores.append("huevos_delta debe ser un número entero.")

        return errores

    @staticmethod
    def build(data: dict, node_id: str = None):
        delta = data.get("huevos_delta", 0)
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            delta = 0

        return {
            "accion": data.get("accion"),
            "id_operador": str(data.get("id_operador")).strip(),
            "metodo": data.get("metodo", "manual"),
            "huevos_delta": delta,
            "huevos_ingresados": delta if delta > 0 else 0,
            "huevos_retirados": -delta if delta < 0 else 0,
            "autorizado": bool(data.get("autorizado", True)),
            "observaciones": data.get("observaciones", ""),
            "node_id": node_id,
        }
