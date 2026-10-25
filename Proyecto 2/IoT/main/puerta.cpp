#include "puerta.h"

#if PUERTA_HABILITADA

#include "estado_compartido.h"

#include <SPI.h>
#include <MFRC522.h>
#include <string.h>

const int CERRADURA_ANGULO_BLOQUEADA    = 0;
const int CERRADURA_ANGULO_DESBLOQUEADA = 90;

static const OperadorAutorizado OPERADORES[NUM_OPERADORES] = {
    {"OP1", {0x59, 0x15, 0x91, 0x29}, 4},
    {"OP2", {0x61, 0xC0, 0xE7, 0xB0}, 4},
    {"ADMIN", {}, 0},   // sin tarjeta: el administrador solo entra desde la app
};

static const char METODO_RFID[] = "rfid";
static const char METODO_APP[]  = "bluetooth";

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

static void destrabar(const char *idOperador, const char *metodo) {
  anguloObjetivoCerradura   = CERRADURA_ANGULO_DESBLOQUEADA;
  estadoCerradura           = CERRADURA_DESTRABADA;
  espaciosLibresAlDestrabar = estadoLeer().espaciosLibres;

  strncpy(operadorQueAbrio, idOperador, sizeof(operadorQueAbrio) - 1);
  operadorQueAbrio[sizeof(operadorQueAbrio) - 1] = '\0';

  estadoSetPuertaAbierta(true);
  estadoSetOperadorActual(idOperador);
  estadoNotificarEventoPuerta("abrir", idOperador, metodo, 0);
}

static void trabar(const char *idOperador, const char *metodo) {
  anguloObjetivoCerradura = CERRADURA_ANGULO_BLOQUEADA;
  estadoCerradura         = CERRADURA_TRABADA;

  int huevosDelta = espaciosLibresAlDestrabar - estadoLeer().espaciosLibres;

  operadorQueAbrio[0] = '\0';

  estadoSetPuertaAbierta(false);
  estadoSetOperadorActual("");
  estadoNotificarEventoPuerta("cerrar", idOperador, metodo, huevosDelta);
}

void puertaInit() {
  SPI.begin();
  lector.PCD_Init();

  servoCerradura.attach(CERRADURA_SERVO_PIN);
  servoCerradura.write(CERRADURA_ANGULO_BLOQUEADA);
  anguloActualCerradura   = CERRADURA_ANGULO_BLOQUEADA;
  anguloObjetivoCerradura = CERRADURA_ANGULO_BLOQUEADA;

  // Aviso de que operadores tienen tarjeta registrada.
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
      destrabar(idOperador, METODO_RFID);
    } else {
      trabar(idOperador, METODO_RFID);
    }
  } else {
    char uidHex[UID_LONGITUD_MAX * 2 + 1];
    uidAHex(lector.uid, uidHex, sizeof(uidHex));
    estadoNotificarTarjetaNoRegistrada(uidHex);
  }

  lector.PICC_HaltA();
  lector.PCD_StopCrypto1();
}

bool puertaEstaDestrabada() {
  return estadoCerradura == CERRADURA_DESTRABADA;
}

ResultadoApp puertaAccionApp(bool abrir, const char *idOperador) {
  int indice = -1;
  for (byte i = 0; i < NUM_OPERADORES; i++) {
    if (strcasecmp(OPERADORES[i].id, idOperador) == 0) {
      indice = i;
      break;
    }
  }
  if (indice < 0) return APP_ERR_OPERADOR;

  // Se usa el id de la tabla, no el recibido: queda en RAM estatica y bien formado.
  const char *id = OPERADORES[indice].id;
  if (abrir) {
    if (estadoCerradura == CERRADURA_DESTRABADA) return APP_ERR_ESTADO;
    destrabar(id, METODO_APP);
  } else {
    if (estadoCerradura == CERRADURA_TRABADA) return APP_ERR_ESTADO;
    trabar(id, METODO_APP);
  }
  return APP_OK;
}

#endif  // PUERTA_HABILITADA
