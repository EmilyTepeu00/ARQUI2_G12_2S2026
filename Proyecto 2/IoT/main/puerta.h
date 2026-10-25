#ifndef PUERTA_H
#define PUERTA_H

#include <Arduino.h>
#include <Servo.h>

// Puerta/RFID deshabilitada mientras no haya tarjetas MIFARE para probar.
#define PUERTA_HABILITADA 1

// Pines.
#define RFID_SS_PIN          53
#define RFID_RST_PIN         49
#define CERRADURA_SERVO_PIN  10

// Longitud maxima de UID que acepta MIFARE (4, 7 o 10 bytes).
#define UID_LONGITUD_MAX     10

// Operadores autorizados a abrir y cerrar la incubadora.
#define NUM_OPERADORES       3

struct OperadorAutorizado {
    const char *id;                    // "OP1" | "OP2", viaja en el JSON serial
    byte        uid[UID_LONGITUD_MAX]; // UID de la tarjeta
    byte        uidLongitud;           // bytes validos de uid[]; 0 = sin registrar
};

// Tiempo minimo entre dos lecturas aceptadas de la misma tarjeta.
#define PUERTA_COOLDOWN_MS   2000UL

extern const int CERRADURA_ANGULO_BLOQUEADA;
extern const int CERRADURA_ANGULO_DESBLOQUEADA;

enum ResultadoApp : uint8_t {
    APP_OK,               // la accion se ejecuto
    APP_ERR_OPERADOR,     // el id no esta en la tabla OPERADORES
    APP_ERR_ESTADO        // la puerta ya estaba abierta (o ya cerrada)
};

void puertaInit();
void puertaActualizar();

// Apertura/cierre pedido desde la app.
ResultadoApp puertaAccionApp(bool abrir, const char *idOperador);
bool puertaEstaDestrabada();

#endif
