#ifndef LOGICA_UMBRALES_H
#define LOGICA_UMBRALES_H
#include "sensors.h"

struct EstadoControl{
    bool activarCalefaccion;
    bool activarVentilador;
    bool alarmaCritica;
    bool lecturaValida;
};

EstadoControl umbrales_evaluar(const LecturaSensor &lectura);

#endif
