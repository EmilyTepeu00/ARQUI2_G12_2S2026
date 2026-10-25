"""Contrato serial/MQTT y bloqueo, sin hardware ni red."""
import unittest
from datetime import datetime

from bridge import ACTUADORES, aplicar_simulado, normalizar, traducir


class PruebaPuente(unittest.TestCase):
    def test_lectura(self):
        datos = normalizar({"temperatura": 37.5, "humedad": 57, "ventilador": 1,
                            "calefaccion": 0, "rotacion": 0, "espacios_libres": 1,
                            "id_operador_actual": None})
        self.assertIs(datos["ventilacion"], True)
        self.assertIs(datos["calefaccion"], False)
        self.assertNotIn("ventilador", datos)
        self.assertIs(type(datos["espacios_libres"]), int)
        self.assertIsNone(datos["id_operador_actual"])
        self.assertIsNotNone(datetime.fromisoformat(datos["timestamp"]).tzinfo)

    def test_evento(self):
        datos = normalizar({"evento": "puerta", "puerta_abierta": 1})
        self.assertIs(datos["puerta_abierta"], True)
        self.assertNotIn("temperatura", datos)

    def test_lecturas_invalidas(self):
        for valor in (float('nan'), float('inf'), 101, -41):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                normalizar({"temperatura": valor, "humedad": 57})
        with self.assertRaises(ValueError):
            normalizar({"temperatura": 37, "humedad": 57, "ventilador": "false"})

    def test_traduccion(self):
        self.assertEqual(traducir("actuadores/cmd", {"actuador": "ventilacion", "accion": "on"}),
                         {"cmd": "actuador", "nombre": "ventilador", "accion": "on"})
        self.assertEqual(traducir("sistema/estado", {"estado": "bloqueado", "ciclo_activo": True}),
                         {"cmd": "sistema", "estado": "bloqueado"})
        for datos in ({"actuador": "rotacion", "accion": "on"}, {"actuador": "calefaccion", "accion": "toggle"}, []):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                traducir("actuadores/cmd", datos)

    def test_simulacion_y_bloqueo(self):
        estado = dict.fromkeys(ACTUADORES, False)
        orden = traducir("actuadores/cmd", {"actuador": "ventilacion", "accion": "on"}, True)
        bloqueado = aplicar_simulado(estado, orden, False)
        self.assertIs(estado["ventilacion"], True)
        bloqueado = aplicar_simulado(estado, {"cmd": "sistema", "estado": "bloqueado"}, bloqueado)
        self.assertTrue(bloqueado)
        self.assertFalse(any(estado.values()))
        aplicar_simulado(estado, orden, bloqueado)
        self.assertFalse(estado["ventilacion"])
        bloqueado = aplicar_simulado(estado, {"cmd": "sistema", "estado": "normal"}, bloqueado)
        aplicar_simulado(estado, orden, bloqueado)
        self.assertTrue(estado["ventilacion"])


if __name__ == "__main__":
    unittest.main()
