#include <Arduino_FreeRTOS.h>
#include <task.h>
#include <semphr.h>
#include <string.h>

#include "sensors.h"
#include "logica_umbrales.h"
#include "actuators.h"
#include "lcd_display.h"
#include "estado_compartido.h"
#include "puerta.h"            

#define MS_A_TICKS(ms)                                                        \
    ( (TickType_t)( ((uint32_t)(ms) * configTICK_RATE_HZ) / 1000UL ) > 0      \
        ? (TickType_t)( ((uint32_t)(ms) * configTICK_RATE_HZ) / 1000UL )      \
        : (TickType_t)1 )

static const TickType_t PERIODO_ENTRADAS = MS_A_TICKS(20);
static const TickType_t PERIODO_SERVO    = MS_A_TICKS(15);
static const TickType_t PERIODO_CONTROL  = MS_A_TICKS(250);
static const TickType_t PERIODO_LCD      = MS_A_TICKS(500);
static const TickType_t PERIODO_SERIAL   = MS_A_TICKS(1000);
static const TickType_t PERIODO_SENSORES = MS_A_TICKS(MUESTREO_MS);
static const TickType_t PERIODO_PUERTA   = MS_A_TICKS(20);   

#define PRIO_ENTRADAS   (tskIDLE_PRIORITY + 3)
#define PRIO_SERVO      (tskIDLE_PRIORITY + 2)
#define PRIO_CONTROL    (tskIDLE_PRIORITY + 2)
#define PRIO_PUERTA     (tskIDLE_PRIORITY + 1)
#define PRIO_SENSORES   (tskIDLE_PRIORITY + 1)
#define PRIO_LCD        (tskIDLE_PRIORITY + 1)
#define PRIO_SERIAL     (tskIDLE_PRIORITY + 1)

static void TareaEntradas(void *pvParameters);
static void TareaSensores(void *pvParameters);
static void TareaControl(void *pvParameters);
static void TareaServo(void *pvParameters);
static void TareaLCD(void *pvParameters);
static void TareaSerial(void *pvParameters);
#if PUERTA_HABILITADA
static void TareaPuerta(void *pvParameters);
#endif

#define STACK_ENTRADAS  224
#define STACK_SENSORES  512
#define STACK_CONTROL   256
#define STACK_SERVO     256
#define STACK_LCD       320
#define STACK_SERIAL    320
#define STACK_PUERTA    384   

static void crearTarea(TaskFunction_t fn, const char *nombre,
                       uint16_t stack, UBaseType_t prioridad) {
    if (xTaskCreate(fn, nombre, stack, NULL, prioridad, NULL) != pdPASS) {
        Serial.print(F("ERROR: sin RAM para la tarea "));
        Serial.println(nombre);
    }
}

void setup() {
    Serial.begin(9600);

    lcd_init();
    actuadoresInit();
    sensors_init();
#if PUERTA_HABILITADA
    puertaInit();
#endif

    if (!estadoInit()) {
        Serial.println(F("ERROR: no se pudo crear el mutex de estado"));
        while (true) { }
    }

    crearTarea(TareaEntradas, "Entradas", STACK_ENTRADAS, PRIO_ENTRADAS);
    crearTarea(TareaSensores, "Sensores", STACK_SENSORES, PRIO_SENSORES);
    crearTarea(TareaControl,  "Control",  STACK_CONTROL,  PRIO_CONTROL);
    crearTarea(TareaServo,    "Servo",    STACK_SERVO,    PRIO_SERVO);
    crearTarea(TareaLCD,      "LCD",      STACK_LCD,      PRIO_LCD);
    crearTarea(TareaSerial,   "Serial",   STACK_SERIAL,   PRIO_SERIAL);
#if PUERTA_HABILITADA
    crearTarea(TareaPuerta,   "Puerta",   STACK_PUERTA,   PRIO_PUERTA);
#endif

    Serial.println(F("SmartEgg: iniciando planificador"));

    vTaskStartScheduler();

    Serial.println(F("ERROR: memoria insuficiente para FreeRTOS"));
}

void loop() {
}

static void TareaEntradas(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        if (botonPresionado()) {
            estadoSetSistemaEncendido(!estadoSistemaEncendido());
        }
        estadoSetEspaciosLibres(procesarFinesDeCarrera());

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_ENTRADAS);
    }
}

static void TareaSensores(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        LecturaSensor lectura = sensors_leer();
        if (lectura.valida) {
            estadoSetLectura(lectura);
        }

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_SENSORES);
    }
}

static void TareaControl(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        EstadoSistema estado = estadoLeer();

        if (estado.sistemaEncendido) {
            LecturaSensor lectura = {estado.temperatura, estado.humedad, estado.lecturaValida};
            EstadoControl control = umbrales_evaluar(lectura);

            if (control.lecturaValida) {
                controlarLuzVentilador(estado.temperatura);
                controlarAlarma(estado.temperatura, estado.humedad);
            }
        } else {
            apagarTodosLosActuadores();
        }

        estadoSetAlarma(alarmaEstaActiva());

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_CONTROL);
    }
}

static void TareaServo(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();
    uint32_t ultimaRotacionMs = millis();

    for (;;) {
        if (!estadoSistemaEncendido()) {
            ultimaRotacionMs = millis();
        } else if (millis() - ultimaRotacionMs >= ROTATION_INTERVAL_MS) {
            ultimaRotacionMs = millis();
            servoAlternarPosicion();
        }

        servoPasoSuave();

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_SERVO);
    }
}

static void TareaLCD(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        EstadoSistema estado = estadoLeer();
        lcd_mostrar(estado.temperatura,
                    estado.humedad,
                    estado.sistemaEncendido,
                    estado.alarmaActiva,
                    estado.espaciosLibres);

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_LCD);
    }
}


#if PUERTA_HABILITADA
static void TareaPuerta(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        puertaActualizar();

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_PUERTA);
    }
}
#endif  // PUERTA_HABILITADA


static void TareaSerial(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        EstadoSistema estado = estadoLeer();

        Serial.print(F("{\"temperatura\":"));
        Serial.print(estado.temperatura);
        Serial.print(F(",\"humedad\":"));
        Serial.print(estado.humedad);
        Serial.print(F(",\"sistema_encendido\":"));
        Serial.print(estado.sistemaEncendido ? 1 : 0);
        Serial.print(F(",\"alarma\":"));
        Serial.print(estado.alarmaActiva ? 1 : 0);
        Serial.print(F(",\"espacios_libres\":"));
        Serial.print(estado.espaciosLibres);
        Serial.print(F(",\"puerta_abierta\":"));
        Serial.print(estado.puertaAbierta ? 1 : 0);
        Serial.print(F(",\"id_operador_actual\":"));
        if (strlen(estado.idOperadorActual) > 0) {
            Serial.print(F("\""));
            Serial.print(estado.idOperadorActual);
            Serial.print(F("\""));
        } else {
            Serial.print(F("null"));
        }
        Serial.println(F("}"));

        // Se drena la cola completa: si se acumularon varios eventos mientras
        // la tarea dormia, todos salen en este mismo ciclo y no se retrasan.
        EventoPuertaPendiente evento;
        while (estadoConsumirEventoPuerta(evento)) {
            if (evento.tipo == EVENTO_PUERTA_ACCESO) {
                Serial.print(F("{\"evento\":\"puerta\",\"accion\":\""));
                Serial.print(evento.accion);
                Serial.print(F("\",\"id_operador\":\""));
                Serial.print(evento.idOperador);
                Serial.print(F("\",\"metodo\":\""));
                Serial.print(evento.metodo);
                Serial.print(F("\""));
                if (strcmp(evento.accion, "cerrar") == 0) {
                    Serial.print(F(",\"huevos_delta\":"));
                    Serial.print(evento.huevosDelta);
                }
                Serial.println(F("}"));
            } else if (evento.tipo == EVENTO_PUERTA_TARJETA_NO_REGISTRADA) {
                Serial.print(F("{\"evento\":\"tarjeta_no_registrada\",\"uid\":\""));
                Serial.print(evento.uidHex);
                Serial.println(F("\"}"));
            }
        }

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_SERIAL);
    }
}
