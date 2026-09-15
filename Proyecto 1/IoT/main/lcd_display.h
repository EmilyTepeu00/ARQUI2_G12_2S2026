#ifndef LCD_DISPLAY_H
#define LCD_DISPLAY_H

#include <Arduino.h>

void lcd_init();

void lcd_mostrar(float temp, float hum, bool sistemaEncendido, bool alarma, int espaciosDisponibles);

#endif
