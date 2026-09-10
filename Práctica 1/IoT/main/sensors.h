#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>

#define DHTPIN 4
#define DHTTYPE DHT11
#define MUESTREO_MS 2000UL

#define TEMP_MIN 37.0
#define TEMP_MAX 38.0
#define HUM_MIN 50.0
#define HUM_MAX 65.0

struct LecturaSensor{
    float temperatura;
    float humedad;
    bool valida;
};

void sensors_init();

LecturaSensor sensors_leer();

#endif
