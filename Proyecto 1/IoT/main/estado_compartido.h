#ifndef ESTADO_COMPARTIDO_H
#define ESTADO_COMPARTIDO_H

#include <Arduino.h>
#include "sensors.h"

// Estado que varias tareas de FreeRTOS leen y escriben.
// Todo acceso pasa por un mutex, por eso no se expone la estructura directamente.
struct EstadoSistema {
    float temperatura;
    float humedad;
    bool  lecturaValida;
    bool  sistemaEncendido;
    bool  alarmaActiva;
    int   espaciosLibres;

    bool  puertaAbierta;
    char  idOperadorActual[8]; 
};

// Tipo de evento de puerta. Sustituye al campo de texto que se comparaba con
// strcmp() en la tarea serial: ocupa 1 byte en vez de 24 y no se puede escribir mal.
enum TipoEventoPuerta : uint8_t {
    EVENTO_PUERTA_NINGUNO = 0,
    EVENTO_PUERTA_ACCESO,              // apertura o cierre autorizado
    EVENTO_PUERTA_TARJETA_NO_REGISTRADA
};

struct EventoPuertaPendiente {
    TipoEventoPuerta tipo;
    char accion[8];        // "abrir" | "cerrar"  (solo en EVENTO_PUERTA_ACCESO)
    char idOperador[8];    // "OP1" | "OP2"       (solo en EVENTO_PUERTA_ACCESO)
    char metodo[8];        // "rfid"              (solo en EVENTO_PUERTA_ACCESO)
    int  huevosDelta;      // + ingresados / - retirados (solo al cerrar)
    char uidHex[21];       // UID leido (solo en EVENTO_PUERTA_TARJETA_NO_REGISTRADA)
};

// Capacidad de la cola FIFO de eventos de puerta. Con la tarea serial drenandola
// completa cada segundo sobra de largo; si aun asi se llena, se descarta el evento
// mas antiguo y se cuenta en estadoEventosPuertaDescartados().
#define EVENTOS_PUERTA_CAPACIDAD 8

// Debe llamarse en setup(), antes de crear las tareas.
bool estadoInit();

EstadoSistema estadoLeer();

void estadoSetLectura(const LecturaSensor &lectura);
void estadoSetSistemaEncendido(bool encendido);
void estadoSetAlarma(bool activa);
void estadoSetEspaciosLibres(int espacios);

bool estadoSistemaEncendido();

// control de acceso a la puerta 
void estadoSetPuertaAbierta(bool abierta);
bool estadoPuertaAbierta();
void estadoSetOperadorActual(const char *idOperador);

// Cola FIFO de eventos: la tarea de puerta encola, la tarea serial consume.
void estadoNotificarEventoPuerta(const char *accion, const char *idOperador,
                                  const char *metodo, int huevosDelta);
void estadoNotificarTarjetaNoRegistrada(const char *uidHex);
bool estadoConsumirEventoPuerta(EventoPuertaPendiente &destino);
uint16_t estadoEventosPuertaDescartados();

#endif
