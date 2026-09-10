from datetime import datetime, timezone
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
from app.config import config
import sys


class Database:
    def __init__(self):
        try:
            self.client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
            self.db = self.client[config.MONGO_DB_NAME]
            self.lecturas = self.db["lecturas"]
            self.lotes = self.db["lotes"]
            self.alarmas = self.db["alarmas"]

            self.lecturas.create_index([("timestamp", DESCENDING)])
            self.alarmas.create_index([("timestamp", DESCENDING)])

            print(f"Conexión a MongoDB establecida ({config.MONGO_DB_NAME})")
        except PyMongoError as exc:
            print(
                f"Error crítico: No se pudo conectar a MongoDB. Requisito de persistencia fallido. Detalles: {exc}"
            )
            sys.exit(1)

    def guardar_lectura(self, lectura: dict):
        try:
            self.lecturas.insert_one(lectura)
        except PyMongoError as exc:
            print(f"Error al guardar lectura: {exc}")

    def obtener_ultima_lectura(self):
        try:
            resultados = list(
                self.lecturas.find({}, sort=[("timestamp", DESCENDING)], limit=1)
            )
            return resultados[0] if resultados else None
        except PyMongoError as exc:
            print(f"Error al obtener última lectura: {exc}")
            return None

    def obtener_historial(self, limit: int = 100):
        try:
            return list(
                self.lecturas.find({}, sort=[("timestamp", DESCENDING)], limit=limit)
            )
        except PyMongoError as exc:
            print(f"Error al obtener historial: {exc}")
            return []

    def obtener_lecturas_del_dia(self, dia: datetime):
        inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
        try:
            return list(
                self.lecturas.find(
                    {"timestamp": {"$gte": inicio, "$lte": fin}},
                    sort=[("timestamp", DESCENDING)],
                )
            )
        except PyMongoError as exc:
            print(f"Error al obtener lecturas del día: {exc}")
            return []

    def crear_lote(self, lote: dict):
        lote = dict(lote)
        lote.setdefault("fecha_ingreso", datetime.now(timezone.utc))
        result = self.lotes.insert_one(lote)
        lote["_id"] = getattr(result, "inserted_id", None)
        return lote

    def listar_lotes(self):
        try:
            return list(self.lotes.find({}, sort=[("fecha_ingreso", DESCENDING)]))
        except PyMongoError as exc:
            print(f"Error al listar lotes: {exc}")
            return []

    def obtener_lote(self, lote_id):
        return self.lotes.find_one({"_id": lote_id})

    def actualizar_lote(self, lote_id, cambios: dict):
        return self.lotes.update_one({"_id": lote_id}, {"$set": cambios})

    def eliminar_lote(self, lote_id):
        return self.lotes.delete_one({"_id": lote_id})

    def contar_lotes_activos(self):
        return self.lotes.count_documents({"estado": "incubando"})

    def registrar_alarma(self, alarma: dict):
        self.alarmas.insert_one(alarma)

    def obtener_alarmas_del_dia(self, dia: datetime):
        inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
        try:
            return list(
                self.alarmas.find(
                    {"timestamp": {"$gte": inicio, "$lte": fin}},
                    sort=[("timestamp", DESCENDING)],
                )
            )
        except PyMongoError as exc:
            print(f"Error al obtener alarmas del día: {exc}")
            return []

    def obtener_alarmas_recientes(self, limit: int = 50):
        try:
            return list(
                self.alarmas.find({}, sort=[("timestamp", DESCENDING)], limit=limit)
            )
        except PyMongoError as exc:
            print(f"Error al obtener alarmas recientes: {exc}")
            return []


db = Database()
