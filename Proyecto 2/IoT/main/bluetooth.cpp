#include "bluetooth.h"
#include "puerta.h"
#include "estado_compartido.h"

#if PUERTA_HABILITADA

#include <string.h>

struct Canal {
  Stream  &puerto;
  char    linea[BT_LINEA_MAX + 1];
  uint8_t largo;
  bool    desbordada;   // linea mas larga que el buffer: se descarta entera
};

static Canal canalBt = {BT_SERIAL, {0}, 0, false};
#if BT_PRUEBA_USB
static Canal canalUsb = {Serial, {0}, 0, false};
#endif

static void responderResultado(Stream &p, ResultadoApp r, bool abrir) {
  switch (r) {
    case APP_OK:            p.println(abrir ? F("OK ABIERTA") : F("OK CERRADA")); break;
    case APP_ERR_OPERADOR:  p.println(F("ERR OPERADOR")); break;
    case APP_ERR_ESTADO:    p.println(abrir ? F("ERR YA_ABIERTA") : F("ERR YA_CERRADA")); break;
  }
}

static void procesarLinea(Stream &p, char *texto) {
  char *comando = strtok(texto, " ");
  if (comando == NULL) return;   // linea vacia

  if (strcasecmp(comando, "ESTADO") == 0) {
    p.println(puertaEstaDestrabada() ? F("ESTADO ABIERTA") : F("ESTADO CERRADA"));

    // DATOS <temperatura> <humedad> <encendido 0|1> <alarma 0|1> <espacios_libres>
    EstadoSistema e = estadoLeer();
    p.print(F("DATOS "));
    p.print(e.temperatura, 1);
    p.print(' ');
    p.print(e.humedad, 1);
    p.print(' ');
    p.print(e.sistemaEncendido ? 1 : 0);
    p.print(' ');
    p.print(e.alarmaActiva ? 1 : 0);
    p.print(' ');
    p.println(e.espaciosLibres);
    return;
  }

  bool abrir  = strcasecmp(comando, "ABRIR") == 0;
  bool cerrar = strcasecmp(comando, "CERRAR") == 0;
  char *id    = strtok(NULL, " ");

  if (!(abrir || cerrar) || id == NULL) {
    p.println(F("ERR CMD"));
    return;
  }

  responderResultado(p, puertaAccionApp(abrir, id), abrir);
}

static void leerCanal(Canal &c) {
  while (c.puerto.available() > 0) {
    char ch = (char) c.puerto.read();

    if (ch == '\r') continue;

    if (ch == '\n') {
      if (!c.desbordada) {
        c.linea[c.largo] = '\0';
        procesarLinea(c.puerto, c.linea);
      } else {
        c.puerto.println(F("ERR CMD"));
      }
      c.largo = 0;
      c.desbordada = false;
      continue;
    }

    if (c.largo < BT_LINEA_MAX) c.linea[c.largo++] = ch;
    else c.desbordada = true;
  }
}

void bluetoothInit() {
  BT_SERIAL.begin(BT_BAUDIOS);
}

void bluetoothActualizar() {
  leerCanal(canalBt);
#if BT_PRUEBA_USB
  leerCanal(canalUsb);
#endif
}

#endif  // PUERTA_HABILITADA
