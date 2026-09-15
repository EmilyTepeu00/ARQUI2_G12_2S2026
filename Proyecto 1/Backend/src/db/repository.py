"""
Repositorio de datos de SmartEgg.

Unico punto del backend que habla con MongoDB. Todo lo demas (API, lector
serial, cliente MQTT, reportes) pasa por aca, asi que esta clase es el contrato
de la capa de datos: mientras los metodos conserven su nombre y la forma de lo
que devuelven, se puede cambiar el motor por debajo sin tocar nada mas.

Reglas que cumplen todos los metodos:

  * Sin base disponible NO lanzan excepcion. Devuelven el valor neutro que le
    corresponda (None, [], 0 o el dict vacio), para que el backend siga
    leyendo el serial y publicando por MQTT aunque Mongo este caido.
  * Los historicos son append-only: nada de lo que entra se sobrescribe.
  * Las fechas se guardan siempre en UTC.
"""

from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from src.db.connection import ConexionMongo
from src.logger import get_logger

log = get_logger("db.repo")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _rango_dia(dia: datetime):
    inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(days=1) - timedelta(microseconds=1)
    return inicio, fin


def _con_tz(fecha):
    """Mongo puede devolver fechas sin zona. Se asumen UTC."""
    if isinstance(fecha, datetime) and fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


class Database(ConexionMongo):

    # =====================================================================
    #  LECTURAS
    # =====================================================================
    def guardar_lectura(self, lectura: dict):
        if not self._guard():
            return None
        try:
            return self.lecturas.insert_one(dict(lectura)).inserted_id
        except PyMongoError as exc:
            log.error("Error al guardar lectura: %s", exc)
            self._marcar_caida(exc)
            return None

    def obtener_ultima_lectura(self):
        if not self._guard():
            return None
        try:
            docs = list(
                self.lecturas.find({}, sort=[("timestamp", DESCENDING)], limit=1)
            )
            return docs[0] if docs else None
        except PyMongoError as exc:
            log.error("Error al obtener última lectura: %s", exc)
            return None

    def obtener_historial(self, limit: int = 100, desde=None, hasta=None):
        if not self._guard():
            return []
        filtro = self._filtro_rango("timestamp", desde, hasta)
        try:
            return list(
                self.lecturas.find(
                    filtro, sort=[("timestamp", DESCENDING)], limit=limit
                )
            )
        except PyMongoError as exc:
            log.error("Error al obtener historial: %s", exc)
            return []

    def obtener_lecturas_del_dia(self, dia: datetime):
        inicio, fin = _rango_dia(dia)
        return self.obtener_lecturas_rango(inicio, fin)

    def obtener_lecturas_rango(self, desde: datetime, hasta: datetime):
        if not self._guard():
            return []
        try:
            return list(
                self.lecturas.find(
                    {"timestamp": {"$gte": desde, "$lte": hasta}},
                    sort=[("timestamp", DESCENDING)],
                )
            )
        except PyMongoError as exc:
            log.error("Error al obtener lecturas por rango: %s", exc)
            return []

    def estadisticas_rango(self, desde: datetime, hasta: datetime):
        """Mínimo, máximo y promedio de temperatura y humedad"""
        if not self._guard():
            return None
        pipeline = [
            {"$match": {"timestamp": {"$gte": desde, "$lte": hasta}}},
            {
                "$group": {
                    "_id": None,
                    "temp_min": {"$min": "$temperatura"},
                    "temp_max": {"$max": "$temperatura"},
                    "temp_prom": {"$avg": "$temperatura"},
                    "hum_min": {"$min": "$humedad"},
                    "hum_max": {"$max": "$humedad"},
                    "hum_prom": {"$avg": "$humedad"},
                    "lecturas_totales": {"$sum": 1},
                }
            },
        ]
        try:
            resultado = list(self.lecturas.aggregate(pipeline))
        except PyMongoError as exc:
            log.error("Error al calcular estadísticas: %s", exc)
            return None
        if not resultado:
            return None
        doc = resultado[0]
        doc.pop("_id", None)
        return doc

    # =====================================================================
    #  LOTES
    # =====================================================================
    def crear_lote(self, lote: dict):
        if not self._guard():
            return None
        lote = dict(lote)
        lote.setdefault("fecha_ingreso", _ahora())
        result = self.lotes.insert_one(lote)
        lote["_id"] = getattr(result, "inserted_id", None)
        return lote

    def listar_lotes(self):
        if not self._guard():
            return []
        try:
            return list(self.lotes.find({}, sort=[("fecha_ingreso", DESCENDING)]))
        except PyMongoError as exc:
            log.error("Error al listar lotes: %s", exc)
            return []

    def obtener_lote(self, lote_id):
        if not self._guard():
            return None
        return self.lotes.find_one({"_id": lote_id})

    def actualizar_lote(self, lote_id, cambios: dict):
        if not self._guard():
            return None
        return self.lotes.update_one({"_id": lote_id}, {"$set": cambios})

    def eliminar_lote(self, lote_id):
        if not self._guard():
            return None
        return self.lotes.delete_one({"_id": lote_id})

    def contar_lotes_activos(self):
        if not self._guard():
            return 0
        return self.lotes.count_documents({"estado": "incubando"})

    def estadisticas_por_lote(self, lote_id):
        """Condiciones ambientales durante la incubación de un lote.

        Las lecturas NO llevan lote_id: el Arduino no sabe que lote hay dentro,
        solo mide la incubadora. Asi que el cruce se hace por tiempo, tomando la
        ventana entre la fecha de ingreso del lote y su cierre (o ahora, si
        sigue incubando).
        """
        if not self._guard():
            return None
        lote = self.obtener_lote(lote_id)
        if lote is None:
            return None

        desde = _con_tz(lote.get("fecha_ingreso")) or _ahora()
        hasta = _con_tz(lote.get("fecha_eclosion")) or _ahora()

        stats = self.estadisticas_rango(desde, hasta) or {
            "temp_min": None, "temp_max": None, "temp_prom": None,
            "hum_min": None, "hum_max": None, "hum_prom": None,
            "lecturas_totales": 0,
        }
        stats["lote_id"] = str(lote_id)
        stats["codigo"] = lote.get("codigo")
        stats["estado"] = lote.get("estado")
        stats["desde"] = desde
        stats["hasta"] = hasta
        stats["dias_incubando"] = round((hasta - desde).total_seconds() / 86400, 2)
        return stats

    # =====================================================================
    #  ALARMAS
    # =====================================================================
    def abrir_alarma(self, alarma: dict):
        """Registra el inicio de una condición crítica y devuelve el documento."""
        if not self._guard():
            return None
        doc = dict(alarma)
        doc.setdefault("inicio", _ahora())
        doc.setdefault("timestamp", doc["inicio"])
        doc["fin"] = None
        doc["duracion_segundos"] = None
        doc["activa"] = True
        try:
            doc["_id"] = self.alarmas.insert_one(doc).inserted_id
            return doc
        except PyMongoError as exc:
            log.error("Error al registrar alarma: %s", exc)
            return None

    def cerrar_alarma(self, alarma_id, mensaje_resolucion: str = None):
        """Cierra la alarma abierta y calcula su duración."""
        if not self._guard() or alarma_id is None:
            return None
        try:
            doc = self.alarmas.find_one({"_id": alarma_id})
            if not doc:
                return None
            inicio = _con_tz(doc.get("inicio") or doc.get("timestamp")) or _ahora()
            fin = _ahora()
            cambios = {
                "fin": fin,
                "duracion_segundos": round((fin - inicio).total_seconds(), 2),
                "activa": False,
            }
            if mensaje_resolucion:
                cambios["mensaje_resolucion"] = mensaje_resolucion
            self.alarmas.update_one({"_id": alarma_id}, {"$set": cambios})
            doc.update(cambios)
            return doc
        except PyMongoError as exc:
            log.error("Error al cerrar alarma: %s", exc)
            return None

    def obtener_alarma_activa(self):
        if not self._guard():
            return None
        try:
            return self.alarmas.find_one(
                {"activa": True}, sort=[("inicio", DESCENDING)]
            )
        except PyMongoError as exc:
            log.error("Error al buscar alarma activa: %s", exc)
            return None

    def obtener_alarmas_recientes(self, limit: int = 50):
        if not self._guard():
            return []
        try:
            return list(
                self.alarmas.find({}, sort=[("timestamp", DESCENDING)], limit=limit)
            )
        except PyMongoError as exc:
            log.error("Error al obtener alarmas recientes: %s", exc)
            return []

    def obtener_alarmas_del_dia(self, dia: datetime):
        inicio, fin = _rango_dia(dia)
        return self.obtener_alarmas_rango(inicio, fin)

    def obtener_alarmas_rango(self, desde: datetime, hasta: datetime):
        if not self._guard():
            return []
        try:
            return list(
                self.alarmas.find(
                    {"timestamp": {"$gte": desde, "$lte": hasta}},
                    sort=[("timestamp", DESCENDING)],
                )
            )
        except PyMongoError as exc:
            log.error("Error al obtener alarmas por rango: %s", exc)
            return []

    # =====================================================================
    #  OPERADORES
    # =====================================================================
    def crear_operador(self, operador: dict):
        if not self._guard():
            return None
        doc = dict(operador)
        doc.setdefault("fecha_registro", _ahora())
        doc["_id"] = self.operadores.insert_one(doc).inserted_id
        return doc

    def listar_operadores(self):
        if not self._guard():
            return []
        try:
            return list(self.operadores.find({}, sort=[("id_operador", ASCENDING)]))
        except PyMongoError as exc:
            log.error("Error al listar operadores: %s", exc)
            return []

    def obtener_operador(self, id_operador: str):
        if not self._guard():
            return None
        return self.operadores.find_one({"id_operador": id_operador})

    def actualizar_operador(self, id_operador: str, cambios: dict):
        if not self._guard():
            return None
        return self.operadores.update_one(
            {"id_operador": id_operador}, {"$set": cambios}
        )

    def eliminar_operador(self, id_operador: str):
        if not self._guard():
            return None
        return self.operadores.delete_one({"id_operador": id_operador})

    # =====================================================================
    #  APERTURAS DE PUERTA
    # =====================================================================
    def registrar_apertura(self, evento: dict):
        if not self._guard():
            return None
        doc = dict(evento)
        doc.setdefault("timestamp", _ahora())
        try:
            doc["_id"] = self.aperturas.insert_one(doc).inserted_id
            return doc
        except PyMongoError as exc:
            log.error("Error al registrar evento de puerta: %s", exc)
            self._marcar_caida(exc)
            return None

    def listar_aperturas(
        self, limit: int = 100, id_operador=None, desde=None, hasta=None
    ):
        if not self._guard():
            return []
        filtro = self._filtro_rango("timestamp", desde, hasta)
        if id_operador:
            filtro["id_operador"] = id_operador
        try:
            return list(
                self.aperturas.find(
                    filtro, sort=[("timestamp", DESCENDING)], limit=limit
                )
            )
        except PyMongoError as exc:
            log.error("Error al listar aperturas: %s", exc)
            return []

    def resumen_puerta(self, desde: datetime, hasta: datetime, id_operador=None):
        """Conteo de aperturas/cierres y saldo de huevos"""
        if not self._guard():
            return {
                "veces_abierta": 0,
                "veces_cerrada": 0,
                "huevos_ingresados": 0,
                "huevos_retirados": 0,
                "por_operador": [],
            }
        match = {"timestamp": {"$gte": desde, "$lte": hasta}}
        if id_operador:
            match["id_operador"] = id_operador

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$id_operador",
                    "aperturas": {
                        "$sum": {"$cond": [{"$eq": ["$accion", "abrir"]}, 1, 0]}
                    },
                    "cierres": {
                        "$sum": {"$cond": [{"$eq": ["$accion", "cerrar"]}, 1, 0]}
                    },
                    "ingresados": {
                        "$sum": {
                            "$cond": [
                                {"$gt": ["$huevos_delta", 0]},
                                "$huevos_delta",
                                0,
                            ]
                        }
                    },
                    "retirados": {
                        "$sum": {
                            "$cond": [
                                {"$lt": ["$huevos_delta", 0]},
                                {"$abs": "$huevos_delta"},
                                0,
                            ]
                        }
                    },
                }
            },
            {"$sort": {"_id": ASCENDING}},
        ]
        try:
            grupos = list(self.aperturas.aggregate(pipeline))
        except PyMongoError as exc:
            log.error("Error al resumir eventos de puerta: %s", exc)
            grupos = []

        resumen = {
            "veces_abierta": sum(g["aperturas"] for g in grupos),
            "veces_cerrada": sum(g["cierres"] for g in grupos),
            "huevos_ingresados": sum(g["ingresados"] for g in grupos),
            "huevos_retirados": sum(g["retirados"] for g in grupos),
            "por_operador": [
                {
                    "id_operador": g["_id"] or "desconocido",
                    "veces_abierta": g["aperturas"],
                    "veces_cerrada": g["cierres"],
                    "huevos_ingresados": g["ingresados"],
                    "huevos_retirados": g["retirados"],
                }
                for g in grupos
            ],
        }
        return resumen

    # =====================================================================
    #  CONSULTAS HISTORICAS  (dashboards y reportes)
    # =====================================================================
    def serie_temporal(self, desde: datetime, hasta: datetime, intervalo_minutos: int = 5):
        """Promedios de temperatura y humedad agrupados por intervalos de tiempo.

        Graficar lectura por lectura no escala: en un dia hay miles de puntos y
        el navegador se ahoga. Esto agrupa por bloques y devuelve un punto por
        bloque, con el minimo y el maximo de cada uno para poder dibujar la
        banda de variacion.
        """
        if not self._guard():
            return []
        ms = max(1, int(intervalo_minutos)) * 60 * 1000
        pipeline = [
            {"$match": {"timestamp": {"$gte": desde, "$lte": hasta}}},
            {
                "$group": {
                    # Trunca cada marca de tiempo al inicio de su bloque.
                    "_id": {
                        "$toDate": {
                            "$subtract": [
                                {"$toLong": "$timestamp"},
                                {"$mod": [{"$toLong": "$timestamp"}, ms]},
                            ]
                        }
                    },
                    "temp_prom": {"$avg": "$temperatura"},
                    "temp_min": {"$min": "$temperatura"},
                    "temp_max": {"$max": "$temperatura"},
                    "hum_prom": {"$avg": "$humedad"},
                    "hum_min": {"$min": "$humedad"},
                    "hum_max": {"$max": "$humedad"},
                    "lecturas": {"$sum": 1},
                    "alarmas": {"$sum": {"$cond": ["$alarma", 1, 0]}},
                }
            },
            {"$sort": {"_id": ASCENDING}},
        ]
        try:
            filas = list(self.lecturas.aggregate(pipeline))
        except PyMongoError as exc:
            log.error("Error al construir la serie temporal: %s", exc)
            return []

        return [
            {
                "timestamp": f["_id"],
                "temp_prom": round(f["temp_prom"], 2) if f["temp_prom"] is not None else None,
                "temp_min": f["temp_min"],
                "temp_max": f["temp_max"],
                "hum_prom": round(f["hum_prom"], 2) if f["hum_prom"] is not None else None,
                "hum_min": f["hum_min"],
                "hum_max": f["hum_max"],
                "lecturas": f["lecturas"],
                "alarmas": f["alarmas"],
            }
            for f in filas
        ]

    def resumen_diario(self, dias: int = 7):
        """Una fila por dia: promedios, extremos, alarmas y aperturas."""
        if not self._guard():
            return []
        hasta = _ahora()
        desde = hasta - timedelta(days=max(1, int(dias)))

        pipeline = [
            {"$match": {"timestamp": {"$gte": desde, "$lte": hasta}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}
                    },
                    "temp_prom": {"$avg": "$temperatura"},
                    "temp_min": {"$min": "$temperatura"},
                    "temp_max": {"$max": "$temperatura"},
                    "hum_prom": {"$avg": "$humedad"},
                    "hum_min": {"$min": "$humedad"},
                    "hum_max": {"$max": "$humedad"},
                    "lecturas": {"$sum": 1},
                    "lecturas_en_alarma": {"$sum": {"$cond": ["$alarma", 1, 0]}},
                }
            },
            {"$sort": {"_id": ASCENDING}},
        ]
        try:
            filas = list(self.lecturas.aggregate(pipeline))
        except PyMongoError as exc:
            log.error("Error al calcular el resumen diario: %s", exc)
            return []

        # Aperturas del mismo periodo, para pegarlas por dia.
        aperturas_por_dia = {}
        try:
            for f in self.aperturas.aggregate([
                {"$match": {"timestamp": {"$gte": desde, "$lte": hasta}}},
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}
                        },
                        "aperturas": {
                            "$sum": {"$cond": [{"$eq": ["$accion", "abrir"]}, 1, 0]}
                        },
                    }
                },
            ]):
                aperturas_por_dia[f["_id"]] = f["aperturas"]
        except PyMongoError as exc:
            log.error("Error al contar aperturas por día: %s", exc)

        return [
            {
                "dia": f["_id"],
                "temp_prom": round(f["temp_prom"], 2) if f["temp_prom"] is not None else None,
                "temp_min": f["temp_min"],
                "temp_max": f["temp_max"],
                "hum_prom": round(f["hum_prom"], 2) if f["hum_prom"] is not None else None,
                "hum_min": f["hum_min"],
                "hum_max": f["hum_max"],
                "lecturas": f["lecturas"],
                "lecturas_en_alarma": f["lecturas_en_alarma"],
                "aperturas_puerta": aperturas_por_dia.get(f["_id"], 0),
            }
            for f in filas
        ]

    def conteo_alarmas_por_tipo(self, desde: datetime, hasta: datetime):
        """Cuantas alarmas hubo de cada tipo y cuanto duraron."""
        if not self._guard():
            return []
        pipeline = [
            {"$match": {"timestamp": {"$gte": desde, "$lte": hasta}}},
            {
                "$group": {
                    "_id": {"$ifNull": ["$tipo", "desconocido"]},
                    "cantidad": {"$sum": 1},
                    "duracion_total": {"$sum": {"$ifNull": ["$duracion_segundos", 0]}},
                    "duracion_promedio": {"$avg": "$duracion_segundos"},
                    "activas": {"$sum": {"$cond": ["$activa", 1, 0]}},
                }
            },
            {"$sort": {"cantidad": DESCENDING}},
        ]
        try:
            filas = list(self.alarmas.aggregate(pipeline))
        except PyMongoError as exc:
            log.error("Error al contar alarmas por tipo: %s", exc)
            return []

        return [
            {
                "tipo": f["_id"],
                "cantidad": f["cantidad"],
                "duracion_total_segundos": round(f["duracion_total"], 2),
                "duracion_promedio_segundos": (
                    round(f["duracion_promedio"], 2)
                    if f["duracion_promedio"] is not None
                    else None
                ),
                "activas": f["activas"],
            }
            for f in filas
        ]

    def actividad_por_operador(self, desde: datetime, hasta: datetime):
        """Ranking de operadores por actividad en la puerta.

        Es resumen_puerta visto al reves: en lugar de los totales de la
        incubadora, la lista por operador ya ordenada, que es lo que necesita la
        tabla del dashboard.
        """
        resumen = self.resumen_puerta(desde, hasta)
        filas = resumen.get("por_operador", [])
        return sorted(filas, key=lambda f: f["veces_abierta"], reverse=True)

    # =====================================================================
    #  UTILIDADES INTERNAS
    # =====================================================================
    @staticmethod
    def _filtro_rango(campo: str, desde, hasta):
        filtro = {}
        rango = {}
        if desde is not None:
            rango["$gte"] = desde
        if hasta is not None:
            rango["$lte"] = hasta
        if rango:
            filtro[campo] = rango
        return filtro


# Instancia unica que importa todo el backend.
db = Database()
