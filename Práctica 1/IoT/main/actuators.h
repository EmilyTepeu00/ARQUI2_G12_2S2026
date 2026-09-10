#ifndef ACTUATORS_H
#define ACTUATORS_H

#include <Arduino.h>
#include <Servo.h>
#include "sensors.h"

#define RELAY_LUZ_PIN      7
#define RELAY_FAN_PIN      8
#define SERVO_PIN          9
#define BUZZER_PIN         6
#define BUTTON_PIN         2

#define RELAY_ACTIVE_LOW   true

#define NUM_EGG_SLOTS      6
extern const uint8_t limitSwitchPins[NUM_EGG_SLOTS];

extern const float TEMP_CRIT_MIN;
extern const float TEMP_CRIT_MAX;
extern const float HUM_CRIT_MIN;
extern const float HUM_CRIT_MAX;

extern const int SERVO_CENTER_ANGLE;
extern const int SERVO_ROTATION_OFFSET;
extern const unsigned long ROTATION_INTERVAL_MS;

void actuadoresInit();

// Control de relés y buzzer
void controlarLuzVentilador(float temperatura);
void controlarAlarma(float temperatura, float humedad);
bool alarmaEstaActiva();
void apagarTodosLosActuadores();

// Servomotor de la bandeja
void servoAlternarPosicion();   // cambia el ángulo objetivo (izquierda <-> derecha)
void servoCentrar();            // deja como objetivo la posición central
void servoPasoSuave();          // avanza 1 grado hacia el objetivo (llamar periódicamente)

// Entradas digitales
int  procesarFinesDeCarrera();
bool botonPresionado();          // true solo en el flanco de pulsación, con antirrebote

#endif
