#include <Arduino_FreeRTOS.h>
#include <semphr.h>
#include <string.h>

#include "estado_compartido.h"

static EstadoSistema estado = {37.5, 55.0, true, true, false, 0, false, ""};

// Cola circular de eventos de puerta (FIFO).
static EventoPuertaPendiente colaEventos[EVENTOS_PUERTA_CAPACIDAD];
static uint8_t  colaInicio    = 0;   // siguiente a consumir
static uint8_t  colaCantidad  = 0;   // eventos en espera
static uint16_t colaDescartados = 0; // desbordes acumulados

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

// control de acceso a la puerta.
// Reutiliza el mismo estadoMutex de arriba, no se crea ningun semaforo nuevo.

void estadoSetPuertaAbierta(bool abierta) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    estado.puertaAbierta = abierta;
    xSemaphoreGive(estadoMutex);
}

bool estadoPuertaAbierta() {
    bool abierta;
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    abierta = estado.puertaAbierta;
    xSemaphoreGive(estadoMutex);
    return abierta;
}

void estadoSetOperadorActual(const char *idOperador) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    strncpy(estado.idOperadorActual, idOperador, sizeof(estado.idOperadorActual) - 1);
    estado.idOperadorActual[sizeof(estado.idOperadorActual) - 1] = '\0';
    xSemaphoreGive(estadoMutex);
}

// --- Cola FIFO de eventos de puerta ---------------------------------------
// Se llama con el mutex ya tomado. Devuelve la ranura donde escribir el evento;
// si la cola esta llena descarta el mas antiguo para no perder el mas reciente.
static EventoPuertaPendiente *reservarRanura() {
    if (colaCantidad == EVENTOS_PUERTA_CAPACIDAD) {
        colaInicio = (colaInicio + 1) % EVENTOS_PUERTA_CAPACIDAD;
        colaCantidad--;
        colaDescartados++;
    }

    uint8_t indice = (colaInicio + colaCantidad) % EVENTOS_PUERTA_CAPACIDAD;
    colaCantidad++;

    EventoPuertaPendiente *ranura = &colaEventos[indice];
    memset(ranura, 0, sizeof(EventoPuertaPendiente));
    return ranura;
}

static void copiarCampo(char *destino, const char *origen, size_t tamDestino) {
    strncpy(destino, origen, tamDestino - 1);
    destino[tamDestino - 1] = '\0';
}

void estadoNotificarEventoPuerta(const char *accion, const char *idOperador,
                                  const char *metodo, int huevosDelta) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);

    EventoPuertaPendiente *evento = reservarRanura();
    evento->tipo = EVENTO_PUERTA_ACCESO;
    copiarCampo(evento->accion, accion, sizeof(evento->accion));
    copiarCampo(evento->idOperador, idOperador, sizeof(evento->idOperador));
    copiarCampo(evento->metodo, metodo, sizeof(evento->metodo));
    evento->huevosDelta = huevosDelta;

    xSemaphoreGive(estadoMutex);
}

void estadoNotificarTarjetaNoRegistrada(const char *uidHex) {
    xSemaphoreTake(estadoMutex, portMAX_DELAY);

    EventoPuertaPendiente *evento = reservarRanura();
    evento->tipo = EVENTO_PUERTA_TARJETA_NO_REGISTRADA;
    copiarCampo(evento->uidHex, uidHex, sizeof(evento->uidHex));

    xSemaphoreGive(estadoMutex);
}

bool estadoConsumirEventoPuerta(EventoPuertaPendiente &destino) {
    bool habia = false;
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    if (colaCantidad > 0) {
        destino = colaEventos[colaInicio];
        colaEventos[colaInicio].tipo = EVENTO_PUERTA_NINGUNO;
        colaInicio = (colaInicio + 1) % EVENTOS_PUERTA_CAPACIDAD;
        colaCantidad--;
        habia = true;
    }
    xSemaphoreGive(estadoMutex);
    return habia;
}

uint16_t estadoEventosPuertaDescartados() {
    uint16_t descartados;
    xSemaphoreTake(estadoMutex, portMAX_DELAY);
    descartados = colaDescartados;
    xSemaphoreGive(estadoMutex);
    return descartados;
}
