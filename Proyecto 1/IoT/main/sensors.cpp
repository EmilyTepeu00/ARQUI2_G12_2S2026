#include "sensors.h"
#include <DHT.h>

static DHT dht(DHTPIN, DHTTYPE);

void sensors_init(){
    dht.begin();
}

LecturaSensor sensors_leer() {
    LecturaSensor s1;
    s1.temperatura = dht.readTemperature();
    s1.humedad = dht.readHumidity();

    s1.valida = !(isnan(s1.temperatura) || isnan(s1.humedad));

    return s1;
}
