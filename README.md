# Arquitectura de Computadores y Ensambladores 2

## Grupo 12

| Nombre | Carné |
|---|---|
| Emily Maritza Tepeu Guacamaya | 202402955 |
| Juan Manuel Ordóñez Sandoval | 202400006 |
| Héctor Alexander Pérez Natareno | 202406223 |
| Jhonatan José Acalón Ajanel | 202401478 |
| Jennifer Michelle Rosales Juárez | 	202400063 |
| Diego Fernando Curtidor Sagui | 202404402 |

---

## Práctica 1

**SmartEgg: Incubadora Inteligente IoT, maqueta física.**

La Facultad de Ciencias Agronómicas de la USAC pidió un sistema de incubación inteligente para apoyar a pequeños avicultores, que hoy pierden entre el 30 % y el 40 % de sus incubaciones por controlar mal la temperatura y la humedad, girar los huevos a mano, no poder monitorear en tiempo real y no llevar registros digitales. En esta práctica se construyó el nodo físico de la incubadora, que es la base de todo el proyecto.

La incubadora mantiene la temperatura entre 37 y 38 °C y la humedad entre 50 y 65 % de forma automática. Si la temperatura baja del mínimo enciende la fuente de calor, y si sube del máximo enciende el ventilador. Un servomotor simula el giro periódico de los huevos, un buzzer suena ante condiciones críticas como sobrecalentamiento o humedad fuera de rango, y una pantalla LCD muestra en tiempo real la temperatura, la humedad y el estado del sistema. El sistema también cuenta cuántos espacios quedan libres para colocar más huevos.

Todo funciona con un microcontrolador programado en C++ con FreeRTOS y envía las lecturas a la computadora por comunicación serial. Además se hizo una carcasa impresa en 3D para ocultar los cables y dejar el dispositivo presentable, un diagrama de conexiones del circuito y una primera versión del software: una API REST con base de datos, un frontend web con la ficha de identificación de los huevos y la generación de reportes en PDF.

## Proyecto 1

**SmartEgg: Plataforma IoT distribuida.**

Se convierte en un servicio completo que se puede monitorear y controlar desde cualquier dispositivo. El nodo físico se mantiene igual y se le construye alrededor una arquitectura distribuida con varios componentes que se comunican entre sí.

El backend lee continuamente los datos del puerto serial, expone una API REST y publica la telemetría y las alarmas en un broker MQTT, que reparte la información en tiempo real. Los datos se guardan en una base de datos que conserva todo el historial de lecturas, alarmas, lotes de huevos, operadores y aperturas de la puerta. Grafana se conecta al broker para mostrar paneles en tiempo real y a la base de datos para mostrar la analítica histórica como tendencias, mínimos, máximos y promedios.

El frontend web consume la API y recibe las alarmas al instante, sin recargar la página. Permite registrar los huevos y lotes, descargar reportes en PDF, ver los datos con gráficos y visualizaciones interactivas hechas con p5.js y Three.js, y tener perfiles para cada operador y para el administrador. Se agregó un control de acceso en el que solo dos operadores registrados pueden abrir y cerrar la incubadora, para evitar que los avicultores mezclen sus huevos. También se hizo un análisis comparativo entre HTTP y MQTT, y todos los servicios se levantan juntos con Docker.

## Proyecto 2

**SmartEgg: Fase 3, inteligencia artificial y nube.**

La fase final le agrega inteligencia a la incubadora y la lleva a la nube. Hasta el proyecto anterior el sistema solo reaccionaba cuando una lectura ya estaba fuera de rango, no tenía forma de saber qué había realmente dentro de la incubadora y funcionaba únicamente de forma local.

Se entrenó un modelo de machine learning con el historial de lecturas de las fases anteriores, que aprende cómo se ve el funcionamiento normal y avisa cuando los sensores y actuadores se comportan de forma extraña. También se instaló una cámara dentro de la incubadora y se entrenó un modelo de visión por computadora con fotos propias, que clasifica cada imagen en huevo, objeto extraño o vacío. Si el ciclo está iniciado y la cámara detecta algo que no es un huevo, suena la alarma, se enciende una luz y se bloquean el sistema y la página hasta que un administrador lo desbloquee. Además, el sistema monitorea el consumo eléctrico en tiempo real y genera alertas cuando el consumo es anormal.

Ttodo se migró a la nube: el broker MQTT, la base de datos y Grafana corren en un servidor virtual, y la página web está alojada en un bucket. En esta fase la comunicación para controlar sensores y actuadores es únicamente por MQTT. Se montaron dos interfaces de monitoreo: un dashboard de Grafana con alertas activas y una página interactiva hecha con p5.js.
