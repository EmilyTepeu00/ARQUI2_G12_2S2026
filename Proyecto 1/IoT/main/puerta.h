#ifndef PUERTA_H
#define PUERTA_H



#include <Arduino.h>
#include <Servo.h>

// Puerta/RFID deshabilitada mientras no haya tarjetas MIFARE para probar.
// Poner en 1 cuando lleguen: no hay nada mas que descomentar.
#define PUERTA_HABILITADA 1

// Pines. SPI hardware fijo: MISO=50, MOSI=51, SCK=52.
#define RFID_SS_PIN          53
#define RFID_RST_PIN         49
#define CERRADURA_SERVO_PIN  10

// Longitud maxima de UID que acepta MIFARE (4, 7 o 10 bytes).
#define UID_LONGITUD_MAX     10

// Operadores autorizados a abrir y cerrar la incubadora.
// Las tarjetas se registran en la tabla OPERADORES de puerta.cpp.
#define NUM_OPERADORES       2

struct OperadorAutorizado {
    const char *id;                    // "OP1" | "OP2", viaja en el JSON serial
    byte        uid[UID_LONGITUD_MAX]; // UID de la tarjeta
    byte        uidLongitud;           // bytes validos de uid[]; 0 = sin registrar
};

// Tiempo minimo entre dos lecturas aceptadas de la misma tarjeta. Evita que al
// dejar la tarjeta apoyada en el lector la cerradura se abra y cierre en bucle.
#define PUERTA_COOLDOWN_MS   2000UL

extern const int CERRADURA_ANGULO_BLOQUEADA;
extern const int CERRADURA_ANGULO_DESBLOQUEADA;

void puertaInit();
void puertaActualizar();

#endif
