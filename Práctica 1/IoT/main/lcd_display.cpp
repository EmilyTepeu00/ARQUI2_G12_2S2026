#include "lcd_display.h"
#include "actuators.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

static LiquidCrystal_I2C lcd(0x27, 16, 2);

static const uint8_t NUM_PANTALLAS = 3;
static const uint32_t INTERVALO_ROTACION_MS = 3000;

static uint8_t  pantallaActual   = 0;
static uint8_t  pantallaAnterior = 255;
static uint32_t ultimaRotacionMs = 0;
static bool     estabaEncendido = true;

void lcd_init(){
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("SmartEgg IOT");
    lcd.setCursor(0, 1);
    lcd.print("INICIANDO ...");
}

static void dibujarPantallaTempHum(float temp, float hum){
    lcd.setCursor(0, 0);
    lcd.print("Temp: ");
    lcd.print(temp, 1);
    lcd.print("C   ");
    lcd.setCursor(0, 1);
    lcd.print("Hum:  ");
    lcd.print(hum, 0);
    lcd.print("%   ");
}

static void dibujarPantallaEstado(bool alarma){
    lcd.setCursor(0, 0);
    lcd.print("Sist: ENCENDIDO ");
    lcd.setCursor(0, 1);
    if(alarma){
        lcd.print("ALARMA CRITICA!");
    }else{
        lcd.print("Estado: OK     ");
    }
}

static void dibujarPantallaHuevos(int espaciosDisponibles){
    lcd.setCursor(0, 0);
    lcd.print("Huevos Disponib:");
    lcd.setCursor(0, 1);
    lcd.print(espaciosDisponibles);
    lcd.print(" / ");
    lcd.print(NUM_EGG_SLOTS);
    lcd.print(" libres   ");
}

void lcd_mostrar(float temp, float hum, bool sistemaEncendido, bool alarma, int espaciosDisponibles){
    if (sistemaEncendido != estabaEncendido) {
        lcd.clear();
        estabaEncendido = sistemaEncendido;
        pantallaAnterior = 255;
    }

    if(!sistemaEncendido){
        lcd.setCursor(0, 0);
        lcd.print("SISTEMA: APAGADO");
        lcd.setCursor(0, 1);
        lcd.print("Modo Standby    ");
        return;
    }

    uint32_t ahora = millis();
    if (ahora - ultimaRotacionMs >= INTERVALO_ROTACION_MS) {
        ultimaRotacionMs = ahora;
        pantallaActual = (pantallaActual + 1) % NUM_PANTALLAS;
    }

    if (pantallaActual != pantallaAnterior) {
        lcd.clear();
        pantallaAnterior = pantallaActual;
    }

    switch (pantallaActual) {
        case 0:
            dibujarPantallaTempHum(temp, hum);
            break;
        case 1:
            dibujarPantallaEstado(alarma);
            break;
        case 2:
            dibujarPantallaHuevos(espaciosDisponibles);
            break;
    }
}
