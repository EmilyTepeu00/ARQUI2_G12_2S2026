#include <Arduino_FreeRTOS.h>
#include <semphr.h>

#include "estado_compartido.h"

static EstadoSistema estado = {37.5, 55.0, true, true, false, 0};
static SemaphoreHandle_t estadoMutex = NULL;

bool estadoInit() {
    estadoMutex = xSemaphoreCreateMutex();
    return (estadoMutex != NULL);
}

EstadoSistema estadoLeer() {
    EstadoSistema copia;
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    copia = estado;
    xSemaphoreGive(estadoMutex);
    return copia;
}

void estadoSetLectura(const LecturaSensor &lectura) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    estado.temperatura   = lectura.temperatura;
    estado.humedad       = lectura.humedad;
    estado.lecturaValida = lectura.valida;
    xSemaphoreGive(estadoMutex);
}

void estadoSetSistemaEncendido(bool encendido) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    estado.sistemaEncendido = encendido;
    xSemaphoreGive(estadoMutex);
}

void estadoSetAlarma(bool activa) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    estado.alarmaActiva = activa;
    xSemaphoreGive(estadoMutex);
}

void estadoSetEspaciosLibres(int espacios) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    estado.espaciosLibres = espacios;
    xSemaphoreGive(estadoMutex);
}

bool estadoSistemaEncendido() {
    bool encendido;
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    encendido = estado.sistemaEncendido;
    xSemaphoreGive(estadoMutex);
    return encendido;
}
