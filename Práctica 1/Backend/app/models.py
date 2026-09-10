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
        "timestamp",
    )

    def __init__(
        self,
        temperatura: float,
        humedad: float,
        sistema_encendido: bool,
        alarma: bool,
        espacios_libres: int,
        timestamp: datetime = None,
    ):
        self.temperatura = temperatura
        self.humedad = humedad
        self.sistema_encendido = sistema_encendido
        self.alarma = alarma
        self.espacios_libres = espacios_libres
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "temperatura": self.temperatura,
            "humedad": self.humedad,
            "sistema_encendido": self.sistema_encendido,
            "alarma": self.alarma,
            "espacios_libres": self.espacios_libres,
            "timestamp": self.timestamp,
        }


class LoteHuevo:
    CAMPOS_REQUERIDOS = ("codigo", "nombre_lote", "cantidad_huevos")

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
                cantidad_num = int(cantidad)
                if cantidad_num <= 0:
                    errores.append("cantidad_huevos debe ser un entero positivo.")
            except (TypeError, ValueError):
                errores.append("cantidad_huevos debe ser un número entero.")

        raza = data.get("raza")
        if raza is not None and not isinstance(raza, str):
            errores.append("raza debe ser una cadena de texto.")

        estado = data.get("estado")
        estados_validos = {"incubando", "eclosionado", "descartado"}
        if estado is not None and estado not in estados_validos:
            errores.append(
                f"estado debe ser uno de: {', '.join(sorted(estados_validos))}"
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
