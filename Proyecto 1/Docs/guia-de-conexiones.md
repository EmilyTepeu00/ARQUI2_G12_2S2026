# SmartEgg — Guía de pines y conexiones

Para quien arma el nodo físico. Todo lo que está aquí sale del firmware en
`Proyecto_1/IoT/main/`; si un pin no coincide con la tabla, el firmware manda.

- **Placa:** Arduino Mega 2560 (obligatorio, no cabe en un Uno)
- **Baudios del serial:** 9600
- **Alimentación:** Arduino por USB · servos y bobinas de relé por fuente externa de 5 V

---

## ⚠️ Antes de nada: la tabla vieja está mal

La tabla de pines de la **Práctica 1** ponía los finales de carrera en los pines
**50, 51, 52, 53**. En el Proyecto 1 esos cuatro pines son el bus SPI del lector
RFID. **No los uses para los finales de carrera** o el lector nunca va a
responder. La tabla del `README.md` del Proyecto 1 ya está corregida; si te topás
con la vieja en apuntes o capturas antiguas, ignorala.

Los finales de carrera se movieron a **44, 45, 46, 47, 11, 12**.

---

## 1. Tabla de pines

### Sensores y entradas

| Componente | Pin del componente | Pin del Mega | Modo en firmware | Definido en |
| :--- | :--- | :---: | :--- | :--- |
| Sensor DHT11 | DATA | **4** | Entrada 1-wire | `sensors.h` |
| Botón ON/OFF | una pata | **2** | `INPUT_PULLUP` | `actuators.h` |
| Final de carrera — espacio 1 | COM | **44** | `INPUT_PULLUP` | `actuators.cpp` |
| Final de carrera — espacio 2 | COM | **45** | `INPUT_PULLUP` | `actuators.cpp` |
| Final de carrera — espacio 3 | COM | **46** | `INPUT_PULLUP` | `actuators.cpp` |
| Final de carrera — espacio 4 | COM | **47** | `INPUT_PULLUP` | `actuators.cpp` |
| Final de carrera — espacio 5 | COM | **11** | `INPUT_PULLUP` | `actuators.cpp` |
| Final de carrera — espacio 6 | COM | **12** | `INPUT_PULLUP` | `actuators.cpp` |

### Salidas y actuadores

| Componente | Pin del componente | Pin del Mega | Modo en firmware | Definido en |
| :--- | :--- | :---: | :--- | :--- |
| Buzzer **activo** | + | **6** | `OUTPUT` (HIGH = suena) | `actuators.h` |
| Relé calor/luz | IN1 | **7** | `OUTPUT`, **activo en bajo** | `actuators.h` |
| Relé ventilador | IN2 | **8** | `OUTPUT`, **activo en bajo** | `actuators.h` |
| Servo bandeja (volteo) | señal (naranja) | **9** | PWM `Servo.h` | `actuators.h` |
| Servo cerradura | señal (naranja) | **10** | PWM `Servo.h` | `puerta.h` |

### Pantalla y lector

| Componente | Pin del componente | Pin del Mega | Notas | Definido en |
| :--- | :--- | :---: | :--- | :--- |
| LCD 16x2 (módulo I2C) | SDA | **20** | Dirección `0x27` | `lcd_display.cpp` |
| LCD 16x2 (módulo I2C) | SCL | **21** | | `lcd_display.cpp` |
| Lector RFID MFRC522 | SDA / SS | **53** | | `puerta.h` |
| Lector RFID MFRC522 | RST | **49** | | `puerta.h` |
| Lector RFID MFRC522 | MOSI | **51** | SPI por hardware, fijo | — |
| Lector RFID MFRC522 | MISO | **50** | SPI por hardware, fijo | — |
| Lector RFID MFRC522 | SCK | **52** | SPI por hardware, fijo | — |
| Lector RFID MFRC522 | IRQ | *sin conectar* | El firmware hace polling | — |

### Pines que no se tocan

| Pin | Por qué |
| :---: | :--- |
| **0 (RX0)** y **1 (TX0)** | Es el puerto USB por donde el backend lee el JSON. Cualquier cosa cableada ahí rompe la comunicación. |
| **50, 51, 52** | SPI por hardware, del lector RFID. |

> **Nota sin consecuencias:** la librería `Servo.h` en el Mega toma el Timer5 y
> con eso deshabilita el PWM de los pines 44, 45 y 46. Ahí tenemos finales de
> carrera usados como entradas digitales, así que no afecta en nada. No te
> alarmes si lo lees en algún foro.

---

## 2. Alimentación de los servos (fuente externa)

Esta es la parte que hay que hacer bien. Son **dos servos**: el de la bandeja
(pin 9) y el de la cerradura (pin 10).

### Por qué no van al pin 5V del Arduino

Un SG90 pide unos 650–700 mA cuando arranca contra carga; un MG996R pasa de
2 A. El regulador del Mega entrega alrededor de 800 mA en total y el puerto USB
corta a los 500 mA. Con los dos servos moviéndose a la vez el voltaje se hunde,
el Arduino se resetea a media escritura del LCD y el backend ve el puerto
serial reconectándose solo. Es el bug más difícil de diagnosticar del proyecto
justamente porque parece un problema de software.

### Qué comprar

| | Si ambos servos son SG90 / MG90S | Si alguno es MG996R o metálico |
| :--- | :--- | :--- |
| Fuente | 5 V DC, **≥ 2 A** | 5 V DC, **≥ 3 A** |
| Capacitor | 470 µF / 10 V | 1000 µF / 10 V |

Sirve un cargador de celular con salida 5 V partido, o una fuente de escritorio
5 V 3 A. Si la fuente es de 6 V también funciona (los servos aguantan 4.8–6 V),
pero **no** conectes 6 V a nada más del circuito.

### Cableado, paso a paso

Cada servo trae tres cables. Los colores varían de fábrica, pero el orden en el
conector es siempre el mismo:

| Cable | Nombre típico | A dónde va |
| :--- | :--- | :--- |
| Naranja o amarillo | Señal | **Al Arduino**: pin 9 (bandeja) o pin 10 (cerradura) |
| Rojo | V+ | Al **+5 V de la fuente externa** |
| Café, negro o azul | GND | Al **GND de la fuente externa** |

Y el paso que todo el mundo olvida:

> ### 🔴 Tierra común
> Un cable del **GND de la fuente externa** al **GND del Arduino**.
>
> Sin esto la señal PWM del pin 9 no tiene contra qué medirse: el servo
> tiembla, se va a un extremo, o simplemente no se mueve. Si un servo se
> comporta raro, revisa esto **antes** que cualquier otra cosa.

Orden sugerido en el protoboard:

1. Lleva el **+5 V de la fuente** a una línea roja del protoboard.
2. Lleva el **GND de la fuente** a una línea azul del protoboard.
3. Puentea esa línea azul a cualquier **GND del Arduino** (los 5 GND del Mega
   son el mismo nodo eléctrico, usa el que te quede más cómodo).
4. Monta el **capacitor electrolítico** entre la línea roja y la azul, lo más
   cerca de los servos que puedas. **Respeta la polaridad**: la franja gris con
   el signo `−` va a la línea azul. Al revés explota, literalmente.
5. Conecta rojo y café de ambos servos a esas dos líneas.
6. Recién ahora lleva los cables de señal a los pines 9 y 10.

### Lo que NO hay que hacer

- ❌ Conectar el rojo del servo al pin 5V del Arduino.
- ❌ Conectar la fuente externa al jack o al Vin del Arduino esperando que
  alimente los servos por el pin 5V. Pasa por el mismo regulador, es el mismo
  problema.
- ❌ Dejar las tierras separadas.
- ❌ Alimentar los servos y omitir el capacitor. Sin él "casi" funciona, y
  después falla en la demo.

---

## 3. Conexión del resto, componente por componente

### 3.1 Sensor DHT11

| DHT11 | Va a |
| :--- | :--- |
| VCC / + | 5 V del Arduino |
| DATA | Pin **4** |
| GND / − | GND del Arduino |

Si es el **sensor pelado de 4 patas** (no el módulo azul de 3), agrega una
resistencia de **10 kΩ entre DATA y VCC**. La pata sin usar se deja al aire.
Los módulos de 3 patas ya la traen adentro.

El firmware lo lee cada 2 s. Si el cableado está flojo devuelve `nan` y el
sistema simplemente no actualiza la lectura, sin dar error visible.

### 3.2 Pantalla LCD 16x2 con módulo I2C

| LCD I2C | Va a |
| :--- | :--- |
| VCC | 5 V del Arduino |
| GND | GND del Arduino |
| SDA | Pin **20** |
| SCL | Pin **21** |

Cuatro cables, nada más. Ojo: en el Mega el I2C **no** está en A4/A5 como en el
Uno.

Si al encender la pantalla se ve iluminada pero sin letras, gira el
potenciómetro azul que trae el módulo por atrás: es el contraste. Si sigue en
blanco después de ajustarlo, la dirección I2C no es `0x27` — muchos módulos
vienen en `0x3F`. Corre el sketch `i2c_scanner` y cambia el valor en
`lcd_display.cpp` línea 6.

### 3.3 Botón de encendido / apagado

| Botón | Va a |
| :--- | :--- |
| Una pata | Pin **2** |
| La otra pata | GND del Arduino |

**No lleva resistencia externa.** El firmware usa `INPUT_PULLUP`, o sea la
resistencia va por dentro del chip. Presionar conecta el pin a GND y eso es lo
que el firmware detecta.

En un push button de 4 patas, las patas están unidas de dos en dos. Usa dos
patas de esquinas **diagonalmente opuestas** y no te equivocas.

### 3.4 Finales de carrera (los 6 espacios de huevo)

Los microswitches traen tres terminales: **COM**, **NO** (normalmente abierto) y
**NC** (normalmente cerrado). Usa **COM y NO**, ignora NC.

| Terminal | Va a |
| :--- | :--- |
| COM | Su pin: **44, 45, 46, 47, 11** o **12** |
| NO | GND del Arduino |

Tampoco llevan resistencia, misma razón que el botón. La lógica que espera el
firmware es:

| Situación | Switch | Pin | Cuenta como |
| :--- | :--- | :--- | :--- |
| Espacio vacío | sin presionar | HIGH | **libre** |
| Huevo puesto | presionado | LOW | ocupado |

Es decir: **el huevo, al asentarse en el molde impreso, tiene que presionar el
switch**. Si al montar la huevera te queda al revés (el huevo suelta el switch),
avísame y lo invierto en firmware — no lo resuelvas cableando NC, porque
entonces un cable suelto se leería como "huevo presente".

El firmware ya trae antirrebote de 50 ms por canal, no hace falta capacitor.

### 3.5 Buzzer

| Buzzer | Va a |
| :--- | :--- |
| + (pata larga, o marcado) | Pin **6** |
| − | GND del Arduino |

Tiene que ser un **buzzer activo** (el que ya trae el oscilador adentro y suena
solo con darle voltaje). El firmware hace `digitalWrite(6, HIGH)` y espera
sonido. Un buzzer **pasivo** necesitaría `tone()` y con este código se quedaría
mudo.

Cómo distinguirlos si no vienen etiquetados: el activo suele venir sellado con
una calcomanía arriba y suena si le pones 5 V directo de una pila; el pasivo
tiene la membrana visible y con 5 V directo sólo hace un "clic".

### 3.6 Módulo de relés (2 canales)

| Módulo relé | Va a |
| :--- | :--- |
| IN1 (calor/luz) | Pin **7** |
| IN2 (ventilador) | Pin **8** |
| VCC | 5 V del Arduino *(ver abajo)* |
| GND | GND del Arduino |

El firmware asume módulos **activos en bajo** (`RELAY_ACTIVE_LOW true` en
`actuators.h`), que es lo normal en los módulos azules genéricos. Cómo
comprobarlo: al arrancar el Arduino los dos relés deben quedar en **reposo**
(sin chasquido, LED apagado). Si al contrario arrancan los dos pegados, el
módulo es activo en alto: cambia esa constante a `false` y recompila. No lo
resuelvas invirtiendo cables.

**Sobre la alimentación de las bobinas.** Cada relé consume ~70 mA al activarse.
Sumado al LCD, al DHT y al lector, con los dos relés pegados a la vez el Mega
por USB queda muy justo. Si el módulo trae el jumper **JD-VCC**, la solución
limpia es:

1. Quitar el jumper que une VCC con JD-VCC.
2. Llevar **JD-VCC al +5 V de la fuente externa** (la misma de los servos).
3. Dejar VCC en el 5 V del Arduino y GND en el GND del Arduino.

Así las bobinas se alimentan de la fuente y el optoacoplador mantiene aislado al
Arduino. Si el módulo no tiene ese jumper, alimenta VCC directo del +5 V de la
fuente externa (recuerda: la tierra ya es común).

#### Del lado de la carga

| Terminal | Qué es |
| :--- | :--- |
| COM | Común |
| NO | Normalmente abierto — **usa este** |
| NC | Normalmente cerrado |

Se corta **un solo hilo** del circuito de la carga (el foco o el ventilador) y
cada punta va a COM y NO. El otro hilo pasa de largo, sin tocar el relé.

> ### ⚡ Si el foco es de 110 V
> - Trabaja con todo **desenchufado**. No hay excepción a esto.
> - Corta y conecta **la línea viva**, nunca el neutro.
> - Nada de cable expuesto: termorretráctil o cinta de aislar en cada empalme, y
>   el módulo montado dentro del nivel inferior de la maqueta.
> - No dejes que el cable de 110 V corra pegado a los cables de señal del
>   Arduino.
> - Si pueden cambiarlo por una resistencia calefactora o un foco de **12 V DC**,
>   háganlo. Se defiende igual de bien y nadie se electrocuta.

### 3.7 Lector RFID MFRC522

| MFRC522 | Va a |
| :--- | :--- |
| **3.3V** | **3.3 V del Arduino — NO 5 V** |
| RST | Pin **49** |
| GND | GND del Arduino |
| IRQ | *sin conectar* |
| MISO | Pin **50** |
| MOSI | Pin **51** |
| SCK | Pin **52** |
| SDA (SS) | Pin **53** |

> ### 🔴 El error que mata el módulo
> El MFRC522 es de **3.3 V**. Conectarle 5 V lo quema, casi siempre de
> inmediato y sin humo visible: simplemente deja de responder para siempre.
> Es el componente más frágil de todo el nodo. Confirma ese cable dos veces
> antes de energizar.

Los pines de datos van directo a los del Mega, que son de 5 V. En la práctica
funciona y es como está armado el 99 % de los proyectos con este módulo, pero
si tienen un conversor de nivel a la mano, mejor.

Si el módulo viene con las cabeceras sueltas, hay que soldarlas. Las juntas
frías en este módulo dan un síntoma engañoso: lee una tarjeta de cada diez.

**Ojo:** aunque el lector esté perfecto, la puerta no va a abrir hasta que
Integrante 1 registre los UID reales de las dos tarjetas en la tabla
`OPERADORES` de `puerta.cpp`. Mientras tanto el nodo responde
`{"evento":"tarjeta_no_registrada","uid":"..."}` en el serial. **Eso no es una
falla de armado.**

---

## 4. Resumen de alimentación

```
USB de la PC ──> Arduino Mega ──> 5 V  ──> LCD, DHT11, módulo de relés (VCC)
                              └─> 3.3V ──> MFRC522
                              └─> GND  ─┐
                                        │  ← TIERRA COMÚN (cable obligatorio)
Fuente externa 5 V / 2–3 A ──> +5 V ──┬─┴─> Servo bandeja  (rojo)
                            └─> GND ──┘   └─> Servo cerradura (rojo)
                                          └─> JD-VCC del módulo de relés
                                          └─> Capacitor 470–1000 µF
```

Regla corta: **señales al Arduino, potencia a la fuente, tierras todas juntas.**

---

## 5. Orden de armado sugerido

No conectes los 20 componentes y enciendas a ver qué pasa. Ve por bloques y
prueba cada uno con el monitor serial del Arduino IDE a **9600 baudios**.

| Paso | Qué conectas | Cómo sabes que quedó |
| :---: | :--- | :--- |
| 1 | Solo la placa por USB | En el monitor sale `SmartEgg: iniciando planificador` |
| 2 | LCD | Muestra `SmartEgg IOT / INICIANDO ...` y luego rota entre 3 pantallas |
| 3 | DHT11 | El JSON del serial trae `temperatura` y `humedad` con valores reales, no `nan` |
| 4 | Botón | Al presionarlo el LCD cambia a `SISTEMA: APAGADO` y `sistema_encendido` pasa a `0` |
| 5 | Los 6 finales de carrera | `espacios_libres` baja de 6 a 5 al presionar uno con el dedo |
| 6 | Buzzer | Suena si tapas el DHT con la mano hasta pasar 42 °C, o si desconectas el sensor |
| 7 | Módulo de relés **sin la carga** | Chasquean según la temperatura: foco bajo 37 °C, ventilador sobre 38 °C |
| 8 | La carga del relé (foco, ventilador) | Encienden con el chasquido |
| 9 | **Fuente externa + tierra común**, y recién ahí los servos | La bandeja se mueve ±45° cada 2 min; para probar sin esperar, baja `ROTATION_INTERVAL_MS` a `10000` en `actuators.cpp` y súbelo de nuevo al terminar |
| 10 | Lector RFID | Al pasar una tarjeta sale `{"evento":"tarjeta_no_registrada","uid":"..."}` |

Después del paso 10, **anota los dos UID que imprime el serial** y pásaselos a
Integrante 1 — los necesita para la tabla `OPERADORES`.

---

## 6. Constantes que quizá haya que ajustar en el banco

| Constante | Archivo | Valor actual | Cuándo la cambias |
| :--- | :--- | :---: | :--- |
| `RELAY_ACTIVE_LOW` | `actuators.h` | `true` | Si los relés arrancan pegados |
| Dirección I2C | `lcd_display.cpp:6` | `0x27` | Si el LCD queda en blanco |
| `ROTATION_INTERVAL_MS` | `actuators.cpp` | `120000` (2 min) | Solo para probar; devuélvela a 120000 |
| `SERVO_ROTATION_OFFSET` | `actuators.cpp` | `45` | Si la bandeja pega con la carcasa |
| `CERRADURA_ANGULO_BLOQUEADA` / `_DESBLOQUEADA` | `puerta.cpp` | `0` / `90` | Según cómo quede montado el pestillo |
| `OPERADORES[]` | `puerta.cpp` | vacía | Con los UID reales (lo hace Integrante 1) |

---

## 7. Si algo no funciona

| Síntoma | Causa más probable |
| :--- | :--- |
| El servo tiembla o no se mueve | Falta la tierra común entre la fuente y el Arduino |
| El Arduino se reinicia solo al moverse un servo | Los servos están colgados del 5 V del Arduino |
| El LCD se corrompe cuando arranca un relé o un servo | Falta el capacitor, o la carga comparte tierra con las señales |
| El lector no responde nunca | 5 V en vez de 3.3 V (muy probablemente ya está quemado), o los finales de carrera cableados en 50–53 |
| El lector lee 1 de cada 10 tarjetas | Soldaduras frías en las cabeceras, o cables de más de 20 cm en el SPI |
| Todas las tarjetas salen `tarjeta_no_registrada` | Normal: falta registrar los UID en `puerta.cpp` |
| `espacios_libres` siempre en 6 | Los switches están en NC, o el molde no alcanza a presionarlos |
| `espacios_libres` siempre en 0 | Los switches están cableados al revés (COM a GND y NO al pin) |
| `temperatura: nan` | Falso contacto en el DHT, o falta la resistencia de 10 kΩ en el sensor pelado |
| El buzzer nunca suena | Es un buzzer pasivo, hay que cambiarlo por uno activo |
| El backend no ve el puerto | Hay algo cableado en los pines 0 o 1 |
