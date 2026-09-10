#include <Arduino_FreeRTOS.h>
#include <task.h>
#include <semphr.h>

#include "sensors.h"
#include "logica_umbrales.h"
#include "actuators.h"
#include "lcd_display.h"
#include "estado_compartido.h"

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

#define PRIO_ENTRADAS   (tskIDLE_PRIORITY + 3)
#define PRIO_SERVO      (tskIDLE_PRIORITY + 2)
#define PRIO_CONTROL    (tskIDLE_PRIORITY + 2)
#define PRIO_SENSORES   (tskIDLE_PRIORITY + 1)
#define PRIO_LCD        (tskIDLE_PRIORITY + 1)
#define PRIO_SERIAL     (tskIDLE_PRIORITY + 1)

static void TareaEntradas(void *pvParameters);
static void TareaSensores(void *pvParameters);
static void TareaControl(void *pvParameters);
static void TareaServo(void *pvParameters);
static void TareaLCD(void *pvParameters);
static void TareaSerial(void *pvParameters);

#define STACK_ENTRADAS  224
#define STACK_SENSORES  512
#define STACK_CONTROL   256
#define STACK_SERVO     256
#define STACK_LCD       320
#define STACK_SERIAL    320

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

static void TareaSerial(void *pvParameters) {
    (void) pvParameters;

    TickType_t ultimaEjecucion = xTaskGetTickCount();

    for (;;) {
        EstadoSistema estado = estadoLeer();

        Serial.print("Temperatura: ");
        Serial.print(estado.temperatura);
        Serial.print(", ");
        Serial.print("Humedad: ");
        Serial.print(estado.humedad);
        Serial.print(", ");
        Serial.print("Sistema Encendido: ");
        Serial.print(estado.sistemaEncendido ? 1 : 0);
        Serial.print(", ");
        Serial.print("Alarma: ");
        Serial.print(estado.alarmaActiva ? 1 : 0);
        Serial.print(", ");
        Serial.print("Espacios Libres: ");
        Serial.println(estado.espaciosLibres);

        vTaskDelayUntil(&ultimaEjecucion, PERIODO_SERIAL);
    }
}