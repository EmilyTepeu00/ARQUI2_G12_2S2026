"""Repositorio de datos de SmartEgg."""

from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from src.config import config
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
    """Mongo puede devolver fechas sin zona."""
    if isinstance(fecha, datetime) and fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha

def _segundos_integrables(actual, previo):
    """Tiempo a integrar entre dos estados. Un hueco mayor que ENERGY_MAX_GAP_S significa que no
    hubo datos (nodo apagado o snapshot retenido viejo) y no se cuenta como tiempo encendido."""
    segundos = max(0.0, (actual - previo).total_seconds())
    return 0.0 if segundos > config.ENERGY_MAX_GAP_S else segundos


COLECCIONES_FASE3 = {
    "actuadores": "actuadores_estado",
    "ml": "ml_anomalias",
    "vision": "vision_resultados",
    "sistema": "sistema_eventos",
    "energia": "energia_consumo",
    "mqtt": "mqtt_eventos",
}

class Database(ConexionMongo):

    # INGESTA MQTT FASE 3
    def guardar_evento_fase3(self, categoria: str, evento: dict):
        """Persiste un evento MQTT en una coleccion Fase 3 permitida."""
        if not self._guard():
            return None
        nombre = COLECCIONES_FASE3.get(categoria)
        if nombre is None:
            log.warning("Categoria MQTT no permitida para persistencia: %s", categoria)
            return None
        documento = dict(evento)
        documento.setdefault("timestamp", _ahora())
        try:
            resultado = self.db[nombre].insert_one(documento)
            return resultado.inserted_id
        except PyMongoError as exc:
            log.error("Error al guardar evento Fase 3 (%s): %s", categoria, exc)
            self._marcar_caida(exc)
            return None

    def obtener_estado_sistema(self, node_id: str):
        if not self._guard() or not node_id:
            return None
        try:
            return self.estado_sistema.find_one({"node_id": node_id})
        except PyMongoError as exc:
            log.error("Error al consultar estado del sistema: %s", exc)
            self._marcar_caida(exc)
            return None

    def actualizar_estado_sistema(self, node_id: str, cambios: dict):
        """Actualiza el estado vigente del nodo y devuelve el documento persistido."""
        if not self._guard() or not node_id:
            return None
        valores = dict(cambios)
        valores.pop("_id", None)
        valores["node_id"] = node_id
        valores["timestamp"] = valores.get("timestamp") or _ahora()
        try:
            self.estado_sistema.update_one(
                {"node_id": node_id}, {"$set": valores}, upsert=True
            )
            return self.estado_sistema.find_one({"node_id": node_id})
        except PyMongoError as exc:
            log.error("Error al actualizar estado del sistema: %s", exc)
            self._marcar_caida(exc)
            return None

    def registrar_consumo_actuadores(
        self, node_id: str, estados: dict, potencias_w: dict, timestamp: datetime,
        limite_kwh: float = 0,
    ):
        """Integra consumo histórico y del ciclo actual hasta el instante recibido."""
        if not self._guard() or not node_id:
            return None
        try:
            previo = self.estado_energia.find_one({"node_id": node_id}) or {}
            instante_previo = _con_tz(previo.get("timestamp"))
            if instante_previo and timestamp < instante_previo:
                log.warning(
                    "Estado de actuadores antiguo descartado para %s (%s < %s)",
                    node_id, timestamp, instante_previo,
                )
                return None

            estados_previos = previo.get("actuadores_encendidos", {})
            kwh = dict(previo.get("kwh_por_actuador", {}))
            kwh_ciclo = dict(previo.get("kwh_ciclo_por_actuador", {}))
            if instante_previo is not None:
                segundos = _segundos_integrables(timestamp, instante_previo)
                for nombre, encendido in estados_previos.items():
                    if encendido:
                        potencia = max(0.0, float(potencias_w.get(nombre, 0.0)))
                        incremento = potencia * segundos / 3_600_000
                        kwh[nombre] = float(kwh.get(nombre, 0.0)) + incremento
                        if previo.get("inicio_ciclo") is not None:
                            kwh_ciclo[nombre] = float(kwh_ciclo.get(nombre, 0.0)) + incremento

            estados_actuales = dict(estados_previos)
            estados_actuales.update(
                {str(nombre): bool(valor) for nombre, valor in estados.items()}
            )
            for nombre in estados_actuales:
                kwh.setdefault(nombre, 0.0)
                kwh_ciclo.setdefault(nombre, 0.0)
            potencia_actual = sum(
                max(0.0, float(potencias_w.get(nombre, 0.0)))
                for nombre, encendido in estados_actuales.items()
                if encendido
            )
            total_kwh = sum(float(valor) for valor in kwh.values())
            total_ciclo_kwh = sum(float(valor) for valor in kwh_ciclo.values())
            ciclo_activo = previo.get("inicio_ciclo") is not None
            excedido = ciclo_activo and limite_kwh > 0 and total_ciclo_kwh >= limite_kwh
            alerta_nueva = excedido and not bool(previo.get("limite_ciclo_alertado"))
            documento = {
                "node_id": node_id,
                "timestamp": timestamp,
                "actuadores_encendidos": estados_actuales,
                "potencias_w": dict(potencias_w),
                "potencia_actual_w": round(potencia_actual, 4),
                "kwh_por_actuador": {nombre: round(valor, 8) for nombre, valor in kwh.items()},
                "energia_kwh": round(total_kwh, 8),
                "kwh_ciclo_por_actuador": {
                    nombre: round(valor, 8) for nombre, valor in kwh_ciclo.items()
                },
                "energia_ciclo_kwh": round(total_ciclo_kwh, 8),
                "inicio_ciclo": previo.get("inicio_ciclo"),
                "limite_ciclo_kwh": limite_kwh,
                "limite_ciclo_superado": excedido,
                "limite_ciclo_alertado": bool(previo.get("limite_ciclo_alertado")) or alerta_nueva,
            }
            self.estado_energia.update_one(
                {"node_id": node_id}, {"$set": documento}, upsert=True
            )
            evento = {**documento, "alerta_limite_nueva": alerta_nueva}
            self.energia_consumo.insert_one(dict(evento))
            return evento
        except (PyMongoError, TypeError, ValueError) as exc:
            log.error("Error al calcular o guardar consumo eléctrico: %s", exc)
            if isinstance(exc, PyMongoError):
                self._marcar_caida(exc)
            return None

    def iniciar_ciclo_energia(
        self, node_id: str, timestamp: datetime, potencias_w: dict, limite_kwh: float = 0
    ):
        """Cierra el intervalo previo y reinicia solo los contadores del ciclo."""
        if not self._guard() or not node_id:
            return None
        try:
            previo = self.estado_energia.find_one({"node_id": node_id}) or {}
            kwh = dict(previo.get("kwh_por_actuador", {}))
            instante_previo = _con_tz(previo.get("timestamp"))
            inicio_ciclo = max(timestamp, instante_previo) if instante_previo else timestamp
            if instante_previo and timestamp < instante_previo:
                log.warning(
                    "Inicio de ciclo de %s ajustado a la última marca de energía (%s)",
                    node_id, instante_previo,
                )
            if instante_previo and timestamp >= instante_previo:
                segundos = _segundos_integrables(timestamp, instante_previo)
                for nombre, encendido in previo.get("actuadores_encendidos", {}).items():
                    if encendido:
                        potencia = max(0.0, float(potencias_w.get(nombre, 0.0)))
                        kwh[nombre] = float(kwh.get(nombre, 0.0)) + potencia * segundos / 3_600_000
            for nombre in previo.get("actuadores_encendidos", {}):
                kwh.setdefault(nombre, 0.0)
            estados = dict(previo.get("actuadores_encendidos", {}))
            potencia_actual = sum(
                max(0.0, float(potencias_w.get(nombre, 0.0)))
                for nombre, encendido in estados.items()
                if encendido
            )
            cambios = {
                "node_id": node_id,
                "timestamp": inicio_ciclo,
                "actuadores_encendidos": estados,
                "potencias_w": dict(potencias_w),
                "potencia_actual_w": round(potencia_actual, 4),
                "kwh_por_actuador": {nombre: round(valor, 8) for nombre, valor in kwh.items()},
                "energia_kwh": round(sum(float(valor) for valor in kwh.values()), 8),
                "inicio_ciclo": inicio_ciclo,
                "energia_ciclo_kwh": 0.0,
                "kwh_ciclo_por_actuador": {
                    nombre: 0.0 for nombre in previo.get("actuadores_encendidos", {})
                },
                "limite_ciclo_kwh": limite_kwh,
                "limite_ciclo_superado": False,
                "limite_ciclo_alertado": False,
            }
            self.estado_energia.update_one(
                {"node_id": node_id}, {"$set": cambios}, upsert=True
            )
            evento = {**previo, **cambios, "alerta_limite_nueva": False}
            evento.pop("_id", None)
            self.energia_consumo.insert_one(dict(evento))
            return evento
        except PyMongoError as exc:
            log.error("Error al iniciar ciclo de energía: %s", exc)
            self._marcar_caida(exc)
            return None

    # LECTURAS
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

    # LOTES
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
        """Condiciones ambientales durante la incubación de un lote."""
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

    # ALARMAS
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

    # OPERADORES
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

    # APERTURAS DE PUERTA
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

    # CONSULTAS HISTORICAS (dashboards y reportes)
    def serie_temporal(self, desde: datetime, hasta: datetime, intervalo_minutos: int = 5):
        """Promedios de temperatura y humedad agrupados por intervalos de tiempo."""
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
        """Ranking de operadores por actividad en la puerta."""
        resumen = self.resumen_puerta(desde, hasta)
        filas = resumen.get("por_operador", [])
        return sorted(filas, key=lambda f: f["veces_abierta"], reverse=True)

    # UTILIDADES INTERNAS
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
