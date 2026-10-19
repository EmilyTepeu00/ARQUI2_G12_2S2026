#include "bluetooth.h"
#include "puerta.h"

#if PUERTA_HABILITADA

#include <string.h>

static char    linea[BT_LINEA_MAX + 1];
static uint8_t largo       = 0;
static bool    desbordada  = false;   // linea mas larga que el buffer: se descarta entera

static void responderResultado(ResultadoApp r, bool abrir) {
  switch (r) {
    case APP_OK:            BT_SERIAL.println(abrir ? F("OK ABIERTA") : F("OK CERRADA")); break;
    case APP_ERR_OPERADOR:  BT_SERIAL.println(F("ERR OPERADOR")); break;
    case APP_ERR_ESTADO:    BT_SERIAL.println(abrir ? F("ERR YA_ABIERTA") : F("ERR YA_CERRADA")); break;
  }
}

static void procesarLinea(char *texto) {
  char *comando = strtok(texto, " ");
  if (comando == NULL) return;   // linea vacia

  if (strcasecmp(comando, "ESTADO") == 0) {
    BT_SERIAL.println(puertaEstaDestrabada() ? F("ESTADO ABIERTA") : F("ESTADO CERRADA"));
    return;
  }

  bool abrir  = strcasecmp(comando, "ABRIR") == 0;
  bool cerrar = strcasecmp(comando, "CERRAR") == 0;
  char *id    = strtok(NULL, " ");

  if (!(abrir || cerrar) || id == NULL) {
    BT_SERIAL.println(F("ERR CMD"));
    return;
  }

  responderResultado(puertaAccionApp(abrir, id), abrir);
}

void bluetoothInit() {
  BT_SERIAL.begin(BT_BAUDIOS);
}

void bluetoothActualizar() {
  while (BT_SERIAL.available() > 0) {
    char c = (char) BT_SERIAL.read();

    if (c == '\r') continue;

    if (c == '\n') {
      if (!desbordada) {
        linea[largo] = '\0';
        procesarLinea(linea);
      } else {
        BT_SERIAL.println(F("ERR CMD"));
      }
      largo = 0;
      desbordada = false;
      continue;
    }

    if (largo < BT_LINEA_MAX) linea[largo++] = c;
    else desbordada = true;
  }
}

#endif  // PUERTA_HABILITADA
