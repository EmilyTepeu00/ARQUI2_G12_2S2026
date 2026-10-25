#ifndef BLUETOOTH_H
#define BLUETOOTH_H

#include <Arduino.h>

#define BT_SERIAL   Serial1
#define BT_BAUDIOS  9600

#define BT_LINEA_MAX 32

// 1 = tambien acepta los comandos desde el Monitor Serie (USB), para probar sin Bluetooth.
#define BT_PRUEBA_USB 0

void bluetoothInit();

// No bloquea: procesa lo que haya llegado.
void bluetoothActualizar();

#endif
