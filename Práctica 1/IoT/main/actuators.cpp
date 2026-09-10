#include "actuators.h"

const uint8_t limitSwitchPins[NUM_EGG_SLOTS] = {50, 51, 52, 53, 11, 12};

const float TEMP_CRIT_MIN = 20.0;
const float TEMP_CRIT_MAX = 42.0;
const float HUM_CRIT_MIN  = 20.0;
const float HUM_CRIT_MAX  = 85.0;

const int SERVO_CENTER_ANGLE    = 90;
const int SERVO_ROTATION_OFFSET = 45;
const unsigned long ROTATION_INTERVAL_MS = 120000UL;

static Servo servoBandeja;
static bool  posicionDerecha = true;
static bool  alarmaActiva    = false;

static int anguloActualServo;
static int anguloObjetivoServo;

static const unsigned long DEBOUNCE_BOTON_MS = 200;

static const unsigned long DEBOUNCE_FIN_CARRERA_MS = 50;
static uint8_t  estadoEstableFinCarrera[NUM_EGG_SLOTS];
static uint8_t  estadoCandidatoFinCarrera[NUM_EGG_SLOTS];
static unsigned long ultimoCambioCandidatoFinCarrera[NUM_EGG_SLOTS];
static int      espaciosDisponibles = 0;

static void escribirRele(uint8_t pin, bool activar) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, activar ? LOW : HIGH);
  } else {
    digitalWrite(pin, activar ? HIGH : LOW);
  }
}

static void recontarEspaciosDisponibles() {
  int disponibles = 0;
  for (uint8_t i = 0; i < NUM_EGG_SLOTS; i++) {
    if (estadoEstableFinCarrera[i] == HIGH) {
      disponibles++;
    }
  }
  espaciosDisponibles = disponibles;
}

void actuadoresInit() {
  pinMode(RELAY_LUZ_PIN, OUTPUT);
  pinMode(RELAY_FAN_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  unsigned long ahora = millis();
  for (uint8_t i = 0; i < NUM_EGG_SLOTS; i++) {
    pinMode(limitSwitchPins[i], INPUT_PULLUP);
    uint8_t lectura = digitalRead(limitSwitchPins[i]);
    estadoEstableFinCarrera[i]         = lectura;
    estadoCandidatoFinCarrera[i]       = lectura;
    ultimoCambioCandidatoFinCarrera[i] = ahora;
  }
  recontarEspaciosDisponibles();

  escribirRele(RELAY_LUZ_PIN, false);
  escribirRele(RELAY_FAN_PIN, false);
  digitalWrite(BUZZER_PIN, LOW);

  servoBandeja.attach(SERVO_PIN);
  servoBandeja.write(SERVO_CENTER_ANGLE);
  anguloActualServo   = SERVO_CENTER_ANGLE;
  anguloObjetivoServo = SERVO_CENTER_ANGLE;
}

void controlarLuzVentilador(float temperatura) {
  if (temperatura < TEMP_MIN) {
    escribirRele(RELAY_LUZ_PIN, true);
    escribirRele(RELAY_FAN_PIN, false);
  } else if (temperatura > TEMP_MAX) {
    escribirRele(RELAY_LUZ_PIN, false);
    escribirRele(RELAY_FAN_PIN, true);
  } else {
    escribirRele(RELAY_LUZ_PIN, false);
    escribirRele(RELAY_FAN_PIN, false);
  }
}

void controlarAlarma(float temperatura, float humedad) {
  bool condicionCritica =
      (temperatura <= TEMP_CRIT_MIN) || (temperatura >= TEMP_CRIT_MAX) ||
      (humedad <= HUM_CRIT_MIN)      || (humedad >= HUM_CRIT_MAX);

  if (condicionCritica && !alarmaActiva) {
    alarmaActiva = true;
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (!condicionCritica && alarmaActiva) {
    alarmaActiva = false;
    digitalWrite(BUZZER_PIN, LOW);
  }
}

bool alarmaEstaActiva() {
  return alarmaActiva;
}

void apagarTodosLosActuadores() {
  escribirRele(RELAY_LUZ_PIN, false);
  escribirRele(RELAY_FAN_PIN, false);
  digitalWrite(BUZZER_PIN, LOW);
  alarmaActiva = false;
  anguloObjetivoServo = SERVO_CENTER_ANGLE;
}

void servoAlternarPosicion() {
  if (posicionDerecha) {
    anguloObjetivoServo = SERVO_CENTER_ANGLE - SERVO_ROTATION_OFFSET;
  } else {
    anguloObjetivoServo = SERVO_CENTER_ANGLE + SERVO_ROTATION_OFFSET;
  }
  posicionDerecha = !posicionDerecha;
}

void servoCentrar() {
  anguloObjetivoServo = SERVO_CENTER_ANGLE;
}

void servoPasoSuave() {
  if (anguloActualServo == anguloObjetivoServo) {
    return;
  }

  if (anguloActualServo < anguloObjetivoServo) {
    anguloActualServo++;
  } else {
    anguloActualServo--;
  }

  servoBandeja.write(anguloActualServo);
}

int procesarFinesDeCarrera() {
  bool huboCambio = false;
  unsigned long ahora = millis();

  for (uint8_t i = 0; i < NUM_EGG_SLOTS; i++) {
    uint8_t lectura = digitalRead(limitSwitchPins[i]);

    if (lectura != estadoCandidatoFinCarrera[i]) {
      estadoCandidatoFinCarrera[i]       = lectura;
      ultimoCambioCandidatoFinCarrera[i] = ahora;
    } else if (lectura != estadoEstableFinCarrera[i] &&
               (ahora - ultimoCambioCandidatoFinCarrera[i]) >= DEBOUNCE_FIN_CARRERA_MS) {
      estadoEstableFinCarrera[i] = lectura;
      huboCambio = true;
    }
  }

  if (huboCambio) {
    recontarEspaciosDisponibles();
  }

  return espaciosDisponibles;
}

bool botonPresionado() {
  static int ultimoNivel = HIGH;
  static unsigned long ultimoCambioMs = 0;

  int nivel = digitalRead(BUTTON_PIN);
  unsigned long ahora = millis();

  if (nivel != ultimoNivel && (ahora - ultimoCambioMs) > DEBOUNCE_BOTON_MS) {
    ultimoNivel    = nivel;
    ultimoCambioMs = ahora;
    return (nivel == LOW);   
  }

  return false;
}
