# Manual de usuario — SmartEgg Fase 3

Este manual explica cómo operar la incubadora SmartEgg con las funciones de la Fase 3: el panel interactivo en la nube, el módulo de visión y el bloqueo, las alertas del modelo de machine learning, el consumo eléctrico y los dashboards de Grafana.

El detalle panel por panel de Grafana y de la página está en [`manual-usuario-dashboards.md`](manual-usuario-dashboards.md). El uso del frontend web de la Fase 2 (lotes, historial, reportes PDF, operadores) está en [`manual-usuario.md`](manual-usuario.md).

---

## 1. Qué usa el operador

| Herramienta | Para qué sirve | Dónde está |
| :--- | :--- | :--- |
| **Panel interactivo (p5.js)** | Ver la incubadora en vivo, iniciar y detener el ciclo, accionar actuadores y desbloquear | Bucket S3 (ver sección 2) |
| **Grafana** | Ver gráficas, historial, eventos de bloqueo, resultados de visión y ML, consumo y alertas | EC2, puerto 3000 |
| **Incubadora física** | Arduino con sensores, foco, ventilador, servo, buzzer, luz de bloqueo y cámara | Junto a la PC del puente |
| **PC del puente** | Lleva los datos del Arduino y de la cámara a la nube | La computadora conectada por USB al Arduino y a la cámara |
| **Frontend web (Fase 2)** | Lotes, historial, reportes PDF y administración de operadores | [`manual-usuario.md`](manual-usuario.md) |
| **App móvil** | Abrir y cerrar la puerta por Bluetooth | Teléfono Android con la app SmartEgg |

Todas las órdenes que cambian el estado de la incubadora (iniciar ciclo, encender un actuador, desbloquear) viajan por el broker MQTT. Ninguna pantalla manda órdenes por otra vía.

---

## 2. Acceso al sistema en la nube

| Servicio | Dirección |
| :--- | :--- |
| Panel interactivo | `http://acye2-frontend.s3-website.us-east-2.amazonaws.com/?url=ws://18.221.230.97:9001&user=smartegg&pass=<contraseña>&node=incubadora-01` |
| Grafana | `http://18.221.230.97:3000/grafana/` |
| Dashboard de la Fase 3 | `http://18.221.230.97:3000/grafana/d/smartegg-fase3` |
| Documentación de la API (solo consulta) | `http://18.221.230.97:5000/api/docs` |
| Broker MQTT | `18.221.230.97:1883` (MQTT) y `ws://18.221.230.97:9001` (WebSocket) |

- El panel necesita la contraseña del broker en la dirección. El script `infra/nube/subir_web_s3.sh` imprime la dirección completa al publicar la página.
- Grafana pide iniciar sesión: usuario `admin` y la contraseña definida al instalar la EC2 (`GRAFANA_ADMIN_PASSWORD` en `infra/.env`). Con `GRAFANA_ANON_ENABLED=true` los dashboards también se ven sin sesión, solo para lectura.
- Si la página dice **"Sin conexión"**, la dirección del broker o la contraseña son incorrectas, o la EC2 está apagada.

---

## 3. Puesta en marcha

1. **Conectar la incubadora.** Enchufar la fuente de 5 V de los servos y el cable USB del Arduino a la PC. Conectar la cámara USB.
2. **Encender el sistema** con el botón físico de la incubadora. La pantalla LCD muestra temperatura y humedad.
3. **Iniciar el puente** en la PC, desde `Proyecto_2/infra`:

   ```bash
   MQTT_HOST=18.221.230.97 ./plataforma.sh puente
   ```

   o, para abrir de una vez el puente, la vista de la cámara y el túnel a la base:

   ```bash
   ./plataforma.sh nube
   ```

   El puente debe estar cerrado si se va a subir firmware con el Arduino IDE: los dos no pueden usar el puerto serial al mismo tiempo.
4. **Abrir el panel.** La insignia de arriba a la derecha debe decir **"Conectado al broker"** y en pocos segundos aparecen la temperatura, la humedad y el consumo.
5. **Abrir Grafana** y entrar al dashboard **SmartEgg - Fase 3**. El panel "Estado del sistema" debe decir **NORMAL**.

---

## 4. Operación del ciclo y de los actuadores

### 4.1. Iniciar y detener el ciclo

| Botón | Qué hace | Cómo se confirma |
| :--- | :--- | :--- |
| **Iniciar ciclo** | Publica `sistema/cmd` con `accion: iniciar`. Reinicia el contador de energía del ciclo y activa la vigilancia de la cámara | La etiqueta cambia a "Ciclo en marcha" y Grafana muestra "EN MARCHA" |
| **Detener ciclo** | Publica `accion: detener` | La etiqueta cambia a "Ciclo detenido" |

Antes de iniciar el ciclo hay que revisar que en la bandeja solo haya huevos. Con el ciclo en marcha, cualquier objeto extraño bloquea el sistema (sección 6).

Si el sistema está bloqueado, el ciclo no se puede iniciar hasta desbloquearlo.

### 4.2. Accionar actuadores manualmente

| Botón | Efecto en la incubadora |
| :--- | :--- |
| **Calefacción** | Enciende o apaga el foco |
| **Ventilación** | Enciende o apaga el ventilador |
| **Volteo** | Solo funciona en modo simulación. Con el Arduino real el volteo es automático cada 2 minutos y el comando se registra, pero no se ejecuta |

- La orden manual dura **30 segundos**. Después el control vuelve a los umbrales automáticos (foco bajo 37 °C, ventilador sobre 38 °C). Esto evita que un actuador quede encendido por error.
- La página no cambia el botón por su cuenta: espera la confirmación del Arduino. El botón se pone verde cuando llega el nuevo estado.
- Con el sistema bloqueado, el Arduino ignora todas las órdenes de actuadores.

---

## 5. Módulo de visión por computadora

### 5.1. Cómo funciona

La cámara toma una foto de la bandeja cada 1.5 segundos. El servicio de visión en la nube recorta la zona de la bandeja (ROI) y la clasifica en una de tres clases:

| Clase | Qué ve | Color en la página | Color en Grafana |
| :--- | :--- | :--- | :--- |
| `huevo` | Uno o más huevos | Huevos normales | Verde |
| `objeto_extrano` | Algo que no es un huevo, solo o junto a huevos | Huevos en rojo | Rojo |
| `vacio` | Bandeja sin nada | Huecos vacíos | Azul |

Cada resultado trae su **confianza** (0 a 1). Se muestra en la página junto a la clase y en el panel "Confianza de la visión" de Grafana.

### 5.2. Recomendaciones para que clasifique bien

- **No mover la cámara.** El recorte de la bandeja está calibrado para la posición actual. Si la cámara se mueve, cerrar el puente y recalibrar con `./plataforma.sh roi` (arrastrar con el mouse el rectángulo sobre la bandeja). Para reposicionarla se puede usar la guía de `./plataforma.sh camara` (tecla `g`).
- **Iluminación.** El modelo se entrenó con luz blanca intensa, penumbra con luz cálida y luz mixta. Evitar que un reflejo fuerte o una sombra tape la bandeja.
- **Nada encima de la bandeja** durante el ciclo, ni siquiera la mano por mucho tiempo: si la cámara la ve en 3 fotos seguidas con confianza alta, el sistema se bloquea.
- Una lectura aislada de `objeto_extrano` no bloquea. Hacen falta **3 fotogramas seguidos** con confianza de al menos 0.80 (unos 4.5 s).

### 5.3. Revisar lo que vio la cámara

- En Grafana, la tabla **"Visión reciente"** muestra las últimas clasificaciones con su hora y confianza.
- En la EC2, `vision/evidencias/` guarda cada 15 s por clase el fotograma completo y el recorte que vio el modelo.

---

## 6. Bloqueo y desbloqueo

### 6.1. Qué pasa al bloquearse

Si el ciclo está en marcha y la cámara detecta un objeto extraño en 3 fotogramas seguidos:

| Dónde | Qué se ve |
| :--- | :--- |
| Incubadora | Se apagan el foco, el ventilador y el volteo; suena el buzzer y se enciende la luz de bloqueo |
| Panel p5.js | La escena parpadea en rojo con "SISTEMA BLOQUEADO", aparece el motivo y se deshabilitan todos los botones |
| Grafana | "Estado del sistema" pasa a **BLOQUEADO**, el evento aparece en "Bloqueos y alarmas" y se dispara la alerta "Sistema bloqueado por visión" |
| Base de datos | Se registra el bloqueo con fecha, hora, clase detectada, confianza y fotogramas |

El bloqueo se mantiene aunque se recargue la página, se reinicie el Arduino o se corte la conexión: al reconectarse, todos reciben de nuevo el estado bloqueado.

### 6.2. Cómo desbloquear

1. Retirar el objeto extraño de la incubadora.
2. Revisar que los huevos estén bien colocados y que no haya daños.
3. Un **administrador** pulsa **"Desbloquear (administrador)"** en el panel.
4. El sistema vuelve a **NORMAL**: se apagan el buzzer y la luz de bloqueo, el control por umbrales se reanuda y los botones se habilitan.

Si al desbloquear el objeto sigue en la bandeja y el ciclo continúa en marcha, el sistema se vuelve a bloquear a los pocos segundos.

Solo se aceptan desbloqueos con rol de administrador. Los intentos rechazados quedan registrados en la base de datos.

---

## 7. Alertas del modelo de machine learning

### 7.1. Qué detecta

El modelo aprendió cómo se ve el funcionamiento normal de la incubadora a partir de un mes de lecturas reales. En cada lectura compara la temperatura, la humedad, el estado de los actuadores y la velocidad a la que cambian temperatura y humedad. Marca como anomalía lo que no se parece a nada de lo que vio en operación normal, aunque los valores estén dentro de los umbrales del Arduino. Por ejemplo:

- La temperatura sube con el foco apagado.
- La temperatura baja con el foco encendido (foco quemado).
- El foco sigue encendido con la temperatura ya alta (relé pegado).
- Un salto brusco de temperatura o humedad (sensor suelto o puerta abierta).
- El ventilador encendido con la incubadora fría.

### 7.2. Cómo se ve una alerta

| Dónde | Indicador |
| :--- | :--- |
| Panel p5.js | La etiqueta cambia a **"Modelo ML: anomalía"** y aparece en "Última alarma" |
| Grafana | El panel "Modelo ML" pasa a **ANOMALÍA**, aparece una barra roja en "Modelo ML: anomalías" y se dispara la alerta "Anomalía detectada por el modelo ML" |
| Base de datos | Se guarda el resultado en `ml_anomalias` y la alarma en `sistema_eventos` |

### 7.3. Cómo interpretarla

Cada resultado trae estos datos (se ven en la tabla "Bloqueos y alarmas" de Grafana y en MQTT):

| Campo | Significado |
| :--- | :--- |
| `puntaje` | Qué tan rara es la lectura. Por debajo de `umbral` (1.63) es normal; cuanto más alto, más rara |
| `lecturas_atipicas_seguidas` | El modelo alerta a partir de 3 lecturas raras seguidas, para no reaccionar a una sola lectura con ruido |
| `variable_principal` | La variable más alejada de lo normal. Indica qué revisar primero |
| `lectura` | Los valores que se evaluaron |

**Qué revisar según la variable principal:**

| Variable principal | Posible causa | Qué hacer |
| :--- | :--- | :--- |
| `temperatura` | Foco quemado o relé pegado, puerta abierta | Revisar el foco y el relé; cerrar la puerta |
| `humedad` | Falta de agua, sensor mojado o suelto | Revisar el recipiente de agua y el DHT11 |
| `d_temp` / `d_hum` | Cambio brusco | Revisar si se abrió la puerta o si el sensor se movió |
| `calefaccion` / `ventilacion` | El actuador no hace lo que esperaría por la temperatura | Revisar el relé y el cableado |

La alerta se apaga sola cuando las lecturas vuelven a ser normales. La alerta del ML **no bloquea** el sistema: avisa para que el operador revise.

---

## 8. Consumo eléctrico

- **Potencia actual (W):** suma de lo que consumen los actuadores encendidos en este momento. El foco es la mayor parte (60 W).
- **Energía del ciclo (kWh):** energía acumulada desde que se pulsó "Iniciar ciclo".
- **Límite por ciclo:** al superarlo se genera una alarma de consumo y se dispara la alerta "Consumo del ciclo sobre el umbral" en Grafana. Para la demostración el límite es 0.01 kWh (unos 10 minutos de foco encendido).

En Grafana, la gráfica "Energía del ciclo vs. límite" muestra la energía acumulada (línea verde) contra el límite (línea roja). Si el consumo sube más rápido de lo normal, revisar si la puerta quedó abierta o si el foco no se apaga al llegar a 38 °C.

---

## 9. Grafana en la nube

1. Abrir `http://18.221.230.97:3000/grafana/` e iniciar sesión con el usuario `admin`.
2. Ir a **Dashboards → SmartEgg** y elegir:
   - **SmartEgg - Fase 3:** estado normal/bloqueado, ciclo, visión, ML, consumo, eventos.
   - **SmartEgg - Tiempo real:** actuadores, disponibilidad del nodo, espacios libres y accesos a la puerta.
   - **SmartEgg - Historico:** tendencias, alarmas por tipo y duración, actividad por operador.
3. Ajustar el rango de tiempo arriba a la derecha. Si un panel dice "No data", ampliar el rango.
4. Las alertas están en **Alerting → Alert rules → SmartEgg**. **Firing** (rojo) significa activa; **Normal** (verde), sin problema.

La explicación de cada panel está en [`manual-usuario-dashboards.md`](manual-usuario-dashboards.md).

---

## 10. Consideraciones generales de operación

- **Una sola PC con el puente por incubadora.** No ejecutar dos puentes ni `vision/publish_frames.py` a la vez para el mismo nodo.
- **Cortes de conexión.** Si se cae internet o el Arduino se desconecta, el puente reintenta solo cada 2 s y reenvía el último estado de bloqueo. No hace falta reiniciar nada. Grafana muestra el nodo como `offline` mientras tanto.
- **Reinicios de la nube.** El historial, los dashboards y el estado de bloqueo se conservan aunque se reinicien los contenedores. Para apagar la EC2 sin perder datos se usa `sudo docker compose stop`; nunca `down -v`.
- **Credenciales.** La dirección del panel lleva la contraseña del broker. No compartirla fuera del grupo y cambiarla después de la evaluación (editar `infra/.env` en la EC2 y ejecutar `sudo docker compose up -d --force-recreate`).
- **Umbrales.** Los umbrales de temperatura y humedad del Arduino (37–38 °C, 50–65 %) deben coincidir con los del `.env`. Si se cambian en el firmware, cambiarlos también en el `.env`.
- **Firmware.** Para subir firmware, cerrar primero el puente.

---

## 11. Solución de problemas

| Síntoma | Causa probable | Solución |
| :--- | :--- | :--- |
| El panel dice "Sin conexión" | Contraseña o dirección del broker incorrecta, o EC2 apagada | Revisar la dirección del panel; comprobar con `./plataforma.sh verificar 18.221.230.97` |
| El panel conecta pero no hay temperatura | El puente no está corriendo o el Arduino no está conectado | Iniciar el puente; revisar el cable USB y que el IDE no tenga el puerto abierto |
| La visión dice siempre lo mismo | El puente se inició sin cámara o la cámara cambió de índice | Revisar `CAMARA` en `infra/.env` y reiniciar el puente |
| La visión se equivoca mucho | La cámara se movió | Recalibrar el ROI con `./plataforma.sh roi` |
| El sistema se bloqueó sin objeto | Una mano, sombra o reflejo estuvo varios segundos en la bandeja | Retirar la causa y desbloquear |
| No se puede iniciar el ciclo | El sistema está bloqueado | Desbloquear primero |
| Un actuador vuelve a su estado anterior | La orden manual dura 30 s | Es lo esperado: después manda el control por umbrales |
| Grafana dice "No data" | No hay datos en el rango elegido | Ampliar el rango de tiempo |
| La alerta del ML no se apaga | Las lecturas siguen fuera de lo normal | Revisar la variable principal de la alerta (sección 7.3) |
