# Bitácora de desarrollo — SmartEgg Fase 3

Grupo 12 · Arquitectura de Computadores y Ensambladores 2 · Segundo semestre 2026

Registro del trabajo de la Fase 3, del 14 al 23 de octubre de 2026. Cada entrada indica quién trabajó, qué se hizo, qué se decidió, qué problemas aparecieron y cómo se resolvieron. La columna de evidencia remite al commit del repositorio.

---

## 1. Distribución del trabajo

| Integrante | Módulo | Carpetas |
| :--- | :--- | :--- |
| Héctor Alexander Pérez Natareno | Capa física: comandos por serial, bloqueo en el firmware | `IoT/main/` |
| Diego Fernando Curtidor Sagui | Backend: ingesta MQTT, política de bloqueo, consumo eléctrico, colecciones de MongoDB | `Backend/` |
| Emily Maritza Tepeu Guacamaya | Dashboards: página p5.js, dashboard y alertas de Grafana de la Fase 3, manual de dashboards | `web/`, `Grafana/`, `Docs/` |
| Jennifer Michelle Rosales Juárez | Visión: primera versión del módulo (captura, preprocesamiento, servicio MQTT) | `vision/` |
| Juan Manuel Ordóñez Sandoval | ML, puente serial/cámara, dataset y modelo de visión, compose y scripts de despliegue, documentación | `ml/`, `gateway/`, `vision/`, `infra/` |
| Jhonatan José Acalón Ajanel | Nube: instancia EC2, grupo de seguridad, despliegue del stack y bucket S3 de la página | AWS (EC2, S3) |

---

## 2. Cronología

### 19/09/2026 — Inicio de la fase

- **Actividad:** publicación del enunciado y de la rúbrica de la Fase 3; inicio del período de lectura.
- **Decisiones:** el trabajo se dividió en seis módulos (capa física, ML, visión, nube, backend y dashboards) para avanzar en paralelo, con los topics MQTT como contrato entre módulos.

### 14/10/2026 — Carpeta del proyecto

- **Integrantes:** Juan, Héctor.
- **Actividad:** se creó `Proyecto_2/` a partir de la Fase 2 (backend, frontend, firmware, app, Grafana, infra) para trabajar la Fase 3 sin tocar la entrega anterior.
- **Evidencia:** `7bb0cdc`, `3de5b2b`, `7d9acd6`, `e4e16f7`.

### 16/10/2026 — Firmware: comandos y bloqueo

- **Integrante:** Héctor.
- **Actividad:** `comandos.cpp` lee líneas JSON por serial con ArduinoJson. Se agregaron el estado `bloqueado` en `estado_compartido`, el apagado de actuadores al bloquear y el comando manual de calefacción y ventilador.
- **Decisiones:**
  - No tocar `logica_umbrales.cpp`: la rúbrica exige conservar la lógica de umbrales de la Fase 2.
  - El comando manual de un actuador dura 30 s y luego vuelve el control automático, para que una orden olvidada no deje el foco encendido.
  - Con el sistema bloqueado, el firmware ignora los comandos de actuadores.
- **Evidencia:** `081c4d3`, `7255bb8`.

### 17/10/2026 — Backend MQTT, bloqueo y energía

- **Integrante:** Diego.
- **Actividad:** ingesta de todos los topics `smartegg/{id}/#`, persistencia en colecciones nuevas (`vision_resultados`, `ml_anomalias`, `sistema_eventos`, `estado_sistema`, `energia_consumo`, `estado_energia`), política de bloqueo por visión, cálculo de energía por actuador y por ciclo, scripts `inicializar_mongodb_fase3.js` y `consultas_fase3.mongodb.js`.
- **Decisiones:**
  - El backend decide el bloqueo, no el servicio de visión: el servicio solo clasifica y el backend aplica la regla de fotogramas seguidos, así la regla se ajusta sin tocar el modelo.
  - `sistema/estado` se publica retenido para que el Arduino y la página recuperen el bloqueo al reconectarse.
  - Se mantuvo MongoDB con la autorización del auxiliar.
- **Problemas y solución:**
  - Al reiniciar el backend, los mensajes retenidos se procesaban como nuevos: se duplicaban lecturas y un resultado viejo de visión podía bloquear el sistema. Se separó el manejo de retenidos: se guardan como snapshot pero no disparan acciones ni alarmas.
  - Los módulos usaban nombres distintos (`temp`/`temperatura`, `ventilador`/`ventilacion`). Se aceptaron alias en la ingesta.
- **Evidencia:** `cb8be68`, `3c4e6cd`, `35bcf14`.

### 19/10/2026 — Página p5.js y dashboard de Grafana

- **Integrante:** Emily.
- **Actividad:** página `web/` con p5.js y MQTT.js por WebSocket: dibujo de la incubadora, tarjetas de temperatura, humedad y consumo, botones de control y pantalla de bloqueo. Endpoints de lectura `/api/fase3/*` y dashboard "SmartEgg - Fase 3".
- **Decisiones:**
  - La página no cambia su estado al pulsar un botón: espera la confirmación por MQTT, así lo que se ve es siempre el estado real.
  - Para el dashboard de la Fase 3 se usó Infinity sobre endpoints de solo lectura del backend, porque el datasource MQTT de Grafana no guarda historial ni permite tablas de eventos.
- **Evidencia:** `14fb282`, `c647d46`.

### 20/10/2026 — Alertas, visión y modelo de ML

- **Integrantes:** Emily, Michelle, Juan.
- **Actividad:**
  - Emily: reglas de alerta de Grafana (bloqueo por visión, anomalía del ML, consumo) y manual de dashboards con capturas.
  - Michelle: primera versión del módulo de visión: `common.py`, `capture_dataset.py`, `train.py`, `service.py`, Dockerfile.
  - Juan: notebook de ML con el histórico de la Fase 2 (27 537 lecturas), comparación de Isolation Forest y LOF, servicio `ml` y simulador de anomalías.
- **Decisiones (ML):**
  - Enfoque no supervisado entrenado solo con lecturas normales, porque el histórico casi no tiene fallas reales.
  - Se eligió LOF (F1 0.913) sobre Isolation Forest (F1 0.667): Isolation Forest no detectaba fallas que combinan variables, como la temperatura baja con el foco apagado.
  - Umbral 1.63 elegido en validación por F1 y 3 lecturas atípicas seguidas para alertar.
- **Problemas y solución:**
  - El histórico tenía dos comportamientos normales: incubación (36.5–38.5 °C) y precalentamiento (20–35 °C con el foco encendido). Con solo temperatura y humedad, el precalentamiento salía como anomalía. Se agregaron como features el estado de los actuadores y las derivadas de temperatura y humedad.
  - Había pocas fallas reales para evaluar. Se simularon fallas sobre lecturas reales (foco pegado, foco quemado, humedad fuera de rango, saltos, actuadores incoherentes), solo para validación y prueba.
- **Evidencia:** `c93ad22`, `2387c38`, `2795dca`; modelo y log de prueba del 20/10 en `ml/modelo/` y `ml/evidencias/alerta_simulada.log`.

### 22/10/2026 — Dataset de visión, puente, infraestructura y nube

- **Integrante:** Juan. El trabajo de los días 20 a 22 se subió al repositorio el 22/10 por módulo.
- **Actividad:**
  - **Dataset:** 1 592 fotos propias con la cámara instalada, en 5 sesiones con luz distinta (11:44–12:59).
  - **Modelo de visión:** MobileNetV3-small con *transfer learning*, exportado a ONNX. Exactitud en prueba: 97.2 %.
  - **Puente** `gateway/bridge.py`: lee el serial del Arduino y la cámara y publica en el broker de la nube; traduce `sistema/estado` y `actuadores/cmd` a comandos seriales. Pruebas unitarias y de integración con Mosquitto real.
  - **Firmware:** buzzer con `tone()` a 2 kHz.
  - **Backend:** corrección del cálculo de consumo.
  - **Infraestructura:** autenticación en Mosquitto, servicios `ml` y `vision` en el compose, `plataforma.sh` y `probar_bloqueo.sh`.
  - **Nube:** scripts `instalar_vm.sh`, `crear_puertos_aws.sh` y `subir_web_s3.sh`.
- **Decisiones:**
  - El backend deja de leer el serial (`SERIAL_ENABLED=false`): en la nube el Arduino no está conectado a la EC2. El puente corre en la PC y habla directo con el broker de la nube.
  - Los fotogramas viajan por MQTT como JPEG de 320 px calidad 70 cada 1.5 s: es suficiente para clasificar y no satura el enlace.
  - Train, validación y prueba se separan por sesión, no por foto.
  - La ROI vive en `vision/models/config.json`, montado como volumen: si la cámara se mueve se recalibra sin reconstruir la imagen.
  - MongoDB sin puerto público; se revisa por túnel SSH.
- **Problemas y solución:**
  - Las fotos consecutivas de una sesión son casi iguales; si se reparten al azar entre train y prueba, la prueba mide memoria y no generalización. Se separó por sesión y `train.py` exige al menos 3 sesiones por clase.
  - El índice `/dev/videoN` de la cámara cambiaba entre arranques, y con un índice fijo el puente podía abrir la webcam integrada de la laptop. Se usa la ruta estable `/dev/v4l/by-id/usb-046d_HD_Webcam_C615_...`.
  - En la red de la USAC los DNS que usa Docker están bloqueados y fallaban `pip` y `npm` dentro de los builds. Las imágenes se construyen desde otra red; con la caché ya construida el stack levanta igual.
  - Con un buzzer pasivo, `digitalWrite` solo producía un clic. Se cambió a `tone()`, que suena con buzzer activo y pasivo.
  - Los huecos entre sesiones de prueba se integraban como si el foco hubiera estado encendido todo ese tiempo. Los intervalos de más de 5 min sin datos ya no se cuentan (`ENERGY_MAX_GAP_S`).
  - El broker aceptaba conexiones anónimas, lo que en la nube permitía que cualquiera desbloqueara el sistema. Se activó `allow_anonymous false` con usuario y contraseña generados desde `.env`.
  - La EC2 de 2 GB se quedaba sin memoria al compilar las imágenes. `instalar_vm.sh` agrega 2 GB de swap.
  - El Arduino IDE y el puente no pueden usar el puerto serial a la vez. Se documentó cerrar el puente antes de subir firmware.
  - El modelo usa la clase `objeto` y el contrato MQTT dice `objeto_extrano`. El servicio de visión hace el mapeo al publicar.
- **Evidencia:** `03986ca`, `4b79a6b`, `0530950`, `0b4cc79`, `c06ec4f`, `adbc84e`, `189b789`, `79a866d`, `477a141`, `1186943`, `b2a011b`.

### 22–23/10/2026 — Despliegue en AWS

- **Integrante:** Jhonatan.
- **Actividad:** creación de la instancia EC2 (Ubuntu, región us-east-2) y de su grupo de seguridad, instalación de Docker y despliegue del stack con `instalar_vm.sh` (Mosquitto, MongoDB, backend, ml, vision y Grafana). Creación del bucket S3 `acye2-frontend` con hosting estático y publicación de la página p5.js con `subir_web_s3.sh`, apuntando al broker de la EC2 por WebSocket.
- **Decisiones:**
  - Grupo de seguridad con 22 para administración, 1883 y 9001 para el broker, 3000 para Grafana y 5000 para la API de consulta y Swagger. MongoDB (27017) queda cerrado y se revisa por túnel SSH.
  - La base de datos va en un contenedor de la misma EC2 con volumen persistente, en lugar de RDS: no tiene costo extra y el histórico de la Fase 2 ya estaba en MongoDB.
- **Resultado:** el puente de la PC publica y recibe por el broker de la nube (`18.221.230.97:1883`) y la página del bucket se conecta por `ws://18.221.230.97:9001`.

### 23/10/2026 — Ajustes finales y documentación

- **Integrante:** Juan.
- **Actividad:** la bandeja de la página se inclina igual que el servo real (±45°); se mejoró el dibujo. Documento técnico de la Fase 3 (README), manual de usuario de la Fase 3 y esta bitácora. Modo `nube` de `plataforma.sh` (puente, cámara, MQTTX y túnel a MongoDB contra la EC2).
- **Pruebas en la nube:** la EC2 responde (`/health`: backend, base de datos y MQTT en `ok`), la página del bucket conecta por WebSocket y `/api/fase3/estado` refleja ciclo, visión, ML y consumo en vivo.
- **Evidencia:** `b231c1f`.

---

## 3. Resumen de problemas y soluciones

| Fecha | Módulo | Problema | Solución |
| :--- | :--- | :--- | :--- |
| 17/10 | Backend | Retenidos procesados como nuevos al reconectar | Se guardan como snapshot y no disparan acciones |
| 17/10 | Backend | Nombres de campos distintos entre módulos | Alias en la ingesta |
| 19/10 | Grafana | El datasource MQTT no da historial | Endpoints de lectura `/api/fase3/*` con Infinity |
| 20/10 | ML | Precalentamiento detectado como anomalía | Features de actuadores y derivadas |
| 20/10 | ML | Pocas fallas reales para evaluar | Fallas simuladas sobre lecturas reales, solo en validación y prueba |
| 20/10 | ML | Isolation Forest no detectaba fallas combinadas | LOF |
| 22/10 | Visión | Fotos casi iguales dentro de una sesión | División por sesión |
| 22/10 | Visión | Índice de cámara cambiante | Ruta `/dev/v4l/by-id` |
| 22/10 | Visión | Cambiar la ROI obligaba a reconstruir la imagen | `models/` montado como volumen |
| 22/10 | Infra | DNS bloqueados en la red de la USAC | Construir imágenes desde otra red |
| 22/10 | Infra | Broker anónimo | Autenticación obligatoria |
| 22/10 | Nube | El backend no puede leer el serial desde la EC2 | Puente en la PC hacia el broker de la nube |
| 22/10 | Nube | Falta de memoria al compilar | 2 GB de swap |
| 22/10 | Firmware | Buzzer pasivo solo hacía clic | `tone()` a 2 kHz |
| 22/10 | Backend | Huecos sin datos contados como consumo | `ENERGY_MAX_GAP_S` = 300 s |

---

## 4. Estado al cierre

| Componente | Estado |
| :--- | :--- |
| Incubadora física con lógica de umbrales de la Fase 2 | Operativa |
| Puente serial y cámara → broker en la nube | Operativo |
| Modelo de ML integrado (`ml/anomalia`) | Operativo |
| Visión en vivo (`vision/resultado`) | Operativa |
| Bloqueo físico, en la página y en Grafana | Operativo |
| EC2 con Mosquitto, MongoDB, backend, ml, vision y Grafana | Desplegada |
| Página p5.js en S3 | Publicada |
| Dashboards y alertas de Grafana | Provisionados desde el repositorio |
