#include "logica_umbrales.h"

EstadoControl umbrales_evaluar(const LecturaSensor &lectura){
    EstadoControl estado;

    if (!lectura.valida){
        estado.activarCalefaccion = false;
        estado.activarVentilador = false;
        estado.alarmaCritica = false;
        estado.lecturaValida = false;
        return estado;
    }

    estado.lecturaValida = true;

    estado.activarCalefaccion = lectura.temperatura < TEMP_MIN;
    estado.activarVentilador = lectura.temperatura > TEMP_MAX;

    bool humedadFueraDeRango = (lectura.humedad < HUM_MIN) || (lectura.humedad > HUM_MAX);
    bool tempCritica = (lectura.temperatura < TEMP_MIN - 2.0) || (lectura.temperatura > TEMP_MAX + 2.0);
    estado.alarmaCritica = humedadFueraDeRango || tempCritica;

    return estado;
}
