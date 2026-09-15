/*
  puerta.cpp - SmartEgg: control de acceso de la puerta

  Control de acceso: solo las tarjetas registradas en la tabla OPERADORES
  pueden destrabar y trabar la incubadora. Cada apertura y cierre se encola
  como evento para que la tarea serial lo publique en JSON.
*/

#include "puerta.h"

#if PUERTA_HABILITADA

#include "estado_compartido.h"

#include <SPI.h>
#include <MFRC522.h>
#include <string.h>

const int CERRADURA_ANGULO_BLOQUEADA    = 0;
const int CERRADURA_ANGULO_DESBLOQUEADA = 90;

/* ---------------------------------------------------------------------------
   TARJETAS DE LOS OPERADORES  <-- lo unico que hay que editar para dar acceso

   Como registrar una tarjeta real:
     1. Cargar el sketch con la tabla como esta (uidLongitud = 0).
     2. Abrir el monitor serial a 9600 y pasar la tarjeta por el lector.
     3. El nodo responde con la linea:
          {"evento":"tarjeta_no_registrada","uid":"A1B2C3D4"}
     4. Copiar ese UID byte por byte al renglon del operador y poner
        uidLongitud con la cantidad de bytes (4 en el ejemplo, 7 en tarjetas
        MIFARE Ultralight/DESFire).

   Ejemplo ya registrado para el UID "A1B2C3D4":
     {"OP1", {0xA1, 0xB2, 0xC3, 0xD4}, 4},

   Mientras uidLongitud sea 0 el renglon se ignora: ninguna tarjeta abre por
   ese operador y todas siguen reportandose como tarjeta_no_registrada.
--------------------------------------------------------------------------- */
static const OperadorAutorizado OPERADORES[NUM_OPERADORES] = {
    {"OP1", {0x59, 0x15, 0x91, 0x29}, 4},
    {"OP2", {0x61, 0xC0, 0xE7, 0xB0}, 4},
};

static const char METODO_ACCESO[] = "rfid";

enum EstadoCerradura { CERRADURA_TRABADA, CERRADURA_DESTRABADA };

static MFRC522 lector(RFID_SS_PIN, RFID_RST_PIN);
static Servo servoCerradura;

static EstadoCerradura estadoCerradura = CERRADURA_TRABADA;
static int  espaciosLibresAlDestrabar = 0;
static char operadorQueAbrio[8]       = "";
static uint32_t ultimaLecturaMs       = 0;

static int anguloActualCerradura;
static int anguloObjetivoCerradura;

// Devuelve el indice del operador dueño de la tarjeta, o -1 si no esta registrada.
static int buscarOperador(const MFRC522::Uid &uid) {
  for (byte i = 0; i < NUM_OPERADORES; i++) {
    const OperadorAutorizado &op = OPERADORES[i];

    if (op.uidLongitud == 0) continue;          // renglon sin registrar
    if (op.uidLongitud != uid.size) continue;   // longitudes distintas

    if (memcmp(uid.uidByte, op.uid, op.uidLongitud) == 0) {
      return i;
    }
  }
  return -1;
}

static void uidAHex(const MFRC522::Uid &uid, char *destino, size_t tamDestino) {
  static const char HEX_DIGITOS[] = "0123456789ABCDEF";
  size_t pos = 0;
  for (byte i = 0; i < uid.size && (pos + 2) < tamDestino; i++) {
    destino[pos++] = HEX_DIGITOS[(uid.uidByte[i] >> 4) & 0x0F];
    destino[pos++] = HEX_DIGITOS[uid.uidByte[i] & 0x0F];
  }
  destino[pos] = '\0';
}

static void cerraduraPasoSuave() {
  if (anguloActualCerradura == anguloObjetivoCerradura) return;
  if (anguloActualCerradura < anguloObjetivoCerradura) anguloActualCerradura++;
  else anguloActualCerradura--;
  servoCerradura.write(anguloActualCerradura);
}

static void destrabar(const char *idOperador) {
  anguloObjetivoCerradura   = CERRADURA_ANGULO_DESBLOQUEADA;
  estadoCerradura           = CERRADURA_DESTRABADA;
  espaciosLibresAlDestrabar = estadoLeer().espaciosLibres;

  strncpy(operadorQueAbrio, idOperador, sizeof(operadorQueAbrio) - 1);
  operadorQueAbrio[sizeof(operadorQueAbrio) - 1] = '\0';

  estadoSetPuertaAbierta(true);
  estadoSetOperadorActual(idOperador);
  estadoNotificarEventoPuerta("abrir", idOperador, METODO_ACCESO, 0);
}

static void trabar(const char *idOperador) {
  anguloObjetivoCerradura = CERRADURA_ANGULO_BLOQUEADA;
  estadoCerradura         = CERRADURA_TRABADA;

  // Espacios libres antes menos espacios libres ahora:
  //   positivo -> ingresaron huevos, negativo -> retiraron huevos.
  int huevosDelta = espaciosLibresAlDestrabar - estadoLeer().espaciosLibres;

  operadorQueAbrio[0] = '\0';

  estadoSetPuertaAbierta(false);
  estadoSetOperadorActual("");
  estadoNotificarEventoPuerta("cerrar", idOperador, METODO_ACCESO, huevosDelta);
}

void puertaInit() {
  SPI.begin();
  lector.PCD_Init();

  servoCerradura.attach(CERRADURA_SERVO_PIN);
  servoCerradura.write(CERRADURA_ANGULO_BLOQUEADA);
  anguloActualCerradura   = CERRADURA_ANGULO_BLOQUEADA;
  anguloObjetivoCerradura = CERRADURA_ANGULO_BLOQUEADA;

  // Aviso de que operadores tienen tarjeta registrada. El backend ignora las
  // lineas que no son JSON, asi que esto solo sirve para el monitor serial.
  for (byte i = 0; i < NUM_OPERADORES; i++) {
    Serial.print(F("Puerta: operador "));
    Serial.print(OPERADORES[i].id);
    if (OPERADORES[i].uidLongitud == 0) {
      Serial.println(F(" SIN tarjeta registrada"));
    } else {
      Serial.print(F(" con tarjeta de "));
      Serial.print(OPERADORES[i].uidLongitud);
      Serial.println(F(" bytes"));
    }
  }
}

void puertaActualizar() {
  cerraduraPasoSuave();

  if (!(lector.PICC_IsNewCardPresent() && lector.PICC_ReadCardSerial())) {
    return;
  }

  // Anti-rebote: si la tarjeta se queda apoyada, el lector la vuelve a
  // detectar cada pocos milisegundos y la cerradura oscilaria sin parar.
  if (ultimaLecturaMs != 0 && (millis() - ultimaLecturaMs) < PUERTA_COOLDOWN_MS) {
    lector.PICC_HaltA();
    lector.PCD_StopCrypto1();
    return;
  }
  ultimaLecturaMs = millis();

  int indice = buscarOperador(lector.uid);

  if (indice >= 0) {
    const char *idOperador = OPERADORES[indice].id;

    if (estadoCerradura == CERRADURA_TRABADA) {
      destrabar(idOperador);
    } else {
      trabar(idOperador);
    }
  } else {
    char uidHex[UID_LONGITUD_MAX * 2 + 1];
    uidAHex(lector.uid, uidHex, sizeof(uidHex));
    estadoNotificarTarjetaNoRegistrada(uidHex);
  }

  lector.PICC_HaltA();
  lector.PCD_StopCrypto1();
}

#endif  // PUERTA_HABILITADA
