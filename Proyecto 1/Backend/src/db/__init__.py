"""
Capa de datos de SmartEgg.

Es el unico modulo del backend que habla con MongoDB:

    connection.py   conexion, indices y modo degradado
    repository.py   las consultas del dominio (la clase Database)

Todo el backend importa la instancia ya construida:

    from src.db import db

Cambiar de motor de base de datos significa reescribir estos dos archivos
respetando los nombres y las formas de retorno de repository.py. Ni el lector
serial, ni el cliente MQTT, ni la API se enteran.
"""

from src.db.repository import Database, db

__all__ = ["db", "Database"]
