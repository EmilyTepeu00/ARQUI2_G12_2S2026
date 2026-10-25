#include <Arduino.h>
#include <ArduinoJson.h>
#include <string.h>

#include "comandos.h"
#include "actuators.h"
#include "estado_compartido.h"

#define COMANDOS_LINEA_MAX 120

static char    linea[COMANDOS_LINEA_MAX];
static uint8_t longitud = 0;
static bool    descartando = false;

static StaticJsonDocument<160> doc;

static void aplicarBloqueo(bool bloquear) {
    bool actual = estadoBloqueado();
    if (bloquear && !actual) {
        estadoSetBloqueado(true);
        activarBloqueo();
    } else if (!bloquear && actual) {
        estadoSetBloqueado(false);
        desactivarBloqueo();
    }
}

static void procesarLinea(const char *texto) {
    DeserializationError error = deserializeJson(doc, texto);
    if (error) {
        return;
    }

    const char *cmd = doc["cmd"];
    if (cmd == NULL) {
        return;
    }

    if (strcmp(cmd, "sistema") == 0) {
        const char *valor = doc["estado"];
        if (valor == NULL) return;
        if (strcmp(valor, "bloqueado") == 0) {
            aplicarBloqueo(true);
        } else if (strcmp(valor, "normal") == 0) {
            aplicarBloqueo(false);
        }
    } else if (strcmp(cmd, "actuador") == 0) {
        if (estadoBloqueado()) return;
        const char *nombre = doc["nombre"];
        const char *accion = doc["accion"];
        if (nombre == NULL || accion == NULL) return;
        if (strcmp(accion, "on") == 0) {
            forzarActuador(nombre, true);
        } else if (strcmp(accion, "off") == 0) {
            forzarActuador(nombre, false);
        }
    }
}

void comandosInit() {
    longitud = 0;
    descartando = false;
}

void comandosActualizar() {
    while (Serial.available() > 0) {
        char c = (char)Serial.read();

        if (c == '\n' || c == '\r') {
            if (!descartando && longitud > 0) {
                linea[longitud] = '\0';
                procesarLinea(linea);
            }
            longitud = 0;
            descartando = false;
        } else if (descartando) {
            continue;
        } else if (longitud < COMANDOS_LINEA_MAX - 1) {
            linea[longitud++] = c;
        } else {
            descartando = true;
            longitud = 0;
        }
    }
}
