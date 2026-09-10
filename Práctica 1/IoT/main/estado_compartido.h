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
};

// Debe llamarse en setup(), antes de crear las tareas.
bool estadoInit();

EstadoSistema estadoLeer();

void estadoSetLectura(const LecturaSensor &lectura);
void estadoSetSistemaEncendido(bool encendido);
void estadoSetAlarma(bool activa);
void estadoSetEspaciosLibres(int espacios);

bool estadoSistemaEncendido();

#endif
