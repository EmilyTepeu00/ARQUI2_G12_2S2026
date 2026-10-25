#include "actuators.h"
#include <string.h>

const uint8_t limitSwitchPins[NUM_EGG_SLOTS] = {44, 45, 46, 47, 11, 12};

const float TEMP_CRIT_MIN = 20.0;
const float TEMP_CRIT_MAX = 42.0;
const float HUM_CRIT_MIN  = 20.0;
const float HUM_CRIT_MAX  = 85.0;

const int SERVO_CENTER_ANGLE    = 90;
const int SERVO_ROTATION_OFFSET = 45;
const unsigned long ROTATION_INTERVAL_MS = 10000UL;

static Servo servoBandeja;
static bool  posicionDerecha = true;
static bool  alarmaActiva    = false;

static int anguloActualServo;
static int anguloObjetivoServo;
static unsigned long ultimoPasoServoMs = 0;

// El giro dura ~1.4 s y el serial reporta cada 1 s: con "se mueve ahora" se perderia.
static const unsigned long ROTACION_VISIBLE_MS = 2000UL;

static const unsigned long DURACION_OVERRIDE_MS = 30000UL;
static bool          releLuzEncendido = false;
static bool          releFanEncendido = false;
static bool          overrideLuzActivo = false;
static bool          overrideFanActivo = false;
static bool          overrideLuzValor  = false;
static bool          overrideFanValor  = false;
static unsigned long overrideLuzFinMs  = 0;
static unsigned long overrideFanFinMs  = 0;

static const unsigned long DEBOUNCE_BOTON_MS = 200;

static const unsigned long DEBOUNCE_FIN_CARRERA_MS = 50;
static uint8_t  estadoEstableFinCarrera[NUM_EGG_SLOTS];
static uint8_t  estadoCandidatoFinCarrera[NUM_EGG_SLOTS];
static unsigned long ultimoCambioCandidatoFinCarrera[NUM_EGG_SLOTS];
static int      espaciosDisponibles = 0;

static void escribirRele(uint8_t pin, bool activar) {
  if (pin == RELAY_LUZ_PIN) releLuzEncendido = activar;
  if (pin == RELAY_FAN_PIN) releFanEncendido = activar;
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
  pinMode(LUZ_BLOQUEO_PIN, OUTPUT);
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
  noTone(BUZZER_PIN);
  digitalWrite(LUZ_BLOQUEO_PIN, LUZ_BLOQUEO_ACTIVE_LOW ? HIGH : LOW);

  servoBandeja.attach(SERVO_PIN);
  servoBandeja.write(SERVO_CENTER_ANGLE);
  anguloActualServo   = SERVO_CENTER_ANGLE;
  anguloObjetivoServo = SERVO_CENTER_ANGLE;
}

static bool overrideVigente(bool &activo, unsigned long finMs) {
  if (activo && (long)(millis() - finMs) >= 0) {
    activo = false;
  }
  return activo;
}

void controlarLuzVentilador(float temperatura) {
  bool luz = false;
  bool fan = false;

  if (temperatura < TEMP_MIN) {
    luz = true;
  } else if (temperatura > TEMP_MAX) {
    fan = true;
  }

  if (overrideVigente(overrideLuzActivo, overrideLuzFinMs)) luz = overrideLuzValor;
  if (overrideVigente(overrideFanActivo, overrideFanFinMs)) fan = overrideFanValor;

  escribirRele(RELAY_LUZ_PIN, luz);
  escribirRele(RELAY_FAN_PIN, fan);
}

void controlarAlarma(float temperatura, float humedad) {
  bool condicionCritica =
      (temperatura <= TEMP_CRIT_MIN) || (temperatura >= TEMP_CRIT_MAX) ||
      (humedad <= HUM_CRIT_MIN)      || (humedad >= HUM_CRIT_MAX);

  if (condicionCritica && !alarmaActiva) {
    alarmaActiva = true;
    tone(BUZZER_PIN, BUZZER_FRECUENCIA);
  } else if (!condicionCritica && alarmaActiva) {
    alarmaActiva = false;
    noTone(BUZZER_PIN);
  }
}

bool alarmaEstaActiva() {
  return alarmaActiva;
}

void apagarTodosLosActuadores() {
  escribirRele(RELAY_LUZ_PIN, false);
  escribirRele(RELAY_FAN_PIN, false);
  noTone(BUZZER_PIN);
  alarmaActiva = false;
  overrideLuzActivo = false;
  overrideFanActivo = false;
  anguloObjetivoServo = SERVO_CENTER_ANGLE;
}

bool calefaccionActiva() {
  return releLuzEncendido;
}

bool ventiladorActivo() {
  return releFanEncendido;
}

void activarBloqueo() {
  overrideLuzActivo = false;
  overrideFanActivo = false;
  escribirRele(RELAY_LUZ_PIN, false);
  escribirRele(RELAY_FAN_PIN, false);
  servoCentrar();
  tone(BUZZER_PIN, BUZZER_FRECUENCIA);
  digitalWrite(LUZ_BLOQUEO_PIN, LUZ_BLOQUEO_ACTIVE_LOW ? LOW : HIGH);
  alarmaActiva = true;
}

void desactivarBloqueo() {
  noTone(BUZZER_PIN);
  digitalWrite(LUZ_BLOQUEO_PIN, LUZ_BLOQUEO_ACTIVE_LOW ? HIGH : LOW);
  alarmaActiva = false;
}

bool forzarActuador(const char *nombre, bool encender) {
  unsigned long fin = millis() + DURACION_OVERRIDE_MS;
  if (strcmp(nombre, "calefaccion") == 0) {
    overrideLuzActivo = true;
    overrideLuzValor  = encender;
    overrideLuzFinMs  = fin;
    return true;
  }
  if (strcmp(nombre, "ventilador") == 0) {
    overrideFanActivo = true;
    overrideFanValor  = encender;
    overrideFanFinMs  = fin;
    return true;
  }
  return false;
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
  ultimoPasoServoMs = millis();
}

bool servoRotando() {
  return millis() - ultimoPasoServoMs < ROTACION_VISIBLE_MS;
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
