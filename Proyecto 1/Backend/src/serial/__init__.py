from src.serial import protocol
from src.serial.reader import SerialReader, serial_reader

__all__ = ["SerialReader", "serial_reader", "protocol", "init", "stop"]


def init():
    serial_reader.start()
    return serial_reader


def stop():
    serial_reader.stop()
