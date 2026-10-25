# Backend Fase 3: MQTT, MongoDB y energía

El backend recibe los mensajes bajo `smartegg/{node_id}/#`, persiste los eventos de Fase 3 y publica estado de bloqueo, consumo y alarmas. La lectura serial del backend está deshabilitada por defecto; la entrada de datos debe llegar por MQTT desde el puente o el nodo WiFi. El control de ciclo y actuadores no tiene rutas REST: la interfaz lo envía por MQTT. Se conservan rutas REST heredadas de Fase 2 para consultas y administración, no como canal de control del hardware.

## Topics consumidos

Todos los mensajes de aplicación usan objetos JSON UTF-8. El backend acepta `timestamp` ISO-8601 o epoch; si no viene, asigna la hora UTC de recepción. El `node_id` del topic es la fuente de verdad; si no coincide con el del payload, se registra el dato recibido y se usa el del topic. Para lecturas completas se aceptan `temperatura`/`humedad` o los alias `temp`/`hum`; temperaturas fuera de -40 a 100 °C y humedades fuera de 0 a 100 % se descartan.

| Topic | Campos esperados | Persistencia / acción |
| --- | --- | --- |
| `sensores/lectura` | `temperatura` (o `temp`), `humedad` (o `hum`), estado y `timestamp` | Colección `lecturas`; publica alarma si `alarma` es verdadero. También integra energía si la lectura trae estados de actuadores. |
| `actuadores/estado` | `calefaccion`, `ventilacion`, `rotacion` (booleanos); también acepta el objeto `actuadores` | Guarda el estado y actualiza energía. |
| `ml/anomalia` | `anomalia` o `es_anomalia`, puntaje y detalles | Colección `ml_anomalias`; si es anómalo publica `alarmas/critica`. |
| `vision/resultado` | `clase`, `confianza` | Colección `vision_resultados`; aplica la política de bloqueo. |
| `sistema/cmd` | `accion`: `iniciar`, `detener` o `desbloquear` | Guarda el comando; inicia/detiene ciclo o procesa desbloqueo. |
| `actuadores/cmd` | actuador y acción | Guarda el comando para trazabilidad. |
| `status` | estado de conexión del nodo | Colección `mqtt_eventos`. |

Los mensajes retenidos de sensores se consideran el último snapshot conocido y no se insertan como nuevas muestras históricas al reiniciar o reconectar el backend. Los estados retenidos de actuadores sí se procesan para restaurar el estado de energía. Los comandos `sistema/cmd` y resultados retenidos de ML/visión se guardan para trazabilidad, pero no disparan acciones ni alarmas: un mensaje viejo no debe reiniciar un ciclo o provocar un bloqueo al reconectarse. Los fotogramas `camara/frame` no se guardan en MongoDB porque son binarios y el resultado procesado llega por `vision/resultado`.

## Topics publicados

- `sistema/estado`: estado vigente con `estado`, `bloqueado`, `ciclo_activo`, `motivo` y `timestamp`. Se publica retenido para que el nodo y la página recuperen el bloqueo al reconectarse.
- `energia/consumo`: `potencia_actual_w`, acumulado histórico `energia_kwh`, acumulado del ciclo `energia_ciclo_kwh`, valores por actuador y límite por ciclo.
- `alarmas/critica`: alarmas de umbral, ML, visión o consumo.

Ejemplo de desbloqueo aceptado:

```json
{
  "accion": "desbloquear",
  "autorizado": true,
  "rol": "administrador"
}
```

El rol debe estar en `SYSTEM_UNLOCK_ROLES`. El mensaje JSON por sí solo no prueba la identidad del emisor; la protección está en el broker, que exige usuario y contraseña (`allow_anonymous false` en `infra/mosquitto/mosquitto.conf`), así que solo publica en `sistema/cmd` quien tiene las credenciales.

## Política de bloqueo

El ciclo inicia con `sistema/cmd` y acción `iniciar`. Si el ciclo está activo, se cuentan los resultados consecutivos de clase `objeto_extrano` cuya confianza sea mayor o igual a `VISION_CONFIDENCE_THRESHOLD`. Una clasificación distinta o por debajo del umbral reinicia el contador. Al alcanzar `VISION_CONSECUTIVE_FRAMES`, se persiste el motivo, se marca el sistema como bloqueado y se publica `sistema/estado` retenido. Un comando `desbloquear` no autorizado se registra como rechazado y no cambia el estado.

Valores iniciales configurables: umbral de confianza `0.80` (también acepta escalas de 0 a 100), tres fotogramas consecutivos y roles `admin,administrador`.

## Cálculo de consumo

En cada nuevo estado de actuadores se integra el estado anterior durante el intervalo transcurrido:

```text
kWh = potencia_W × segundos_encendido / 3 600 000
```

El acumulado histórico se guarda por actuador y para el nodo, incluso después de reiniciar el backend. Al recibir `sistema/cmd` con `accion: iniciar`, el contador del ciclo se reinicia sin borrar ese historial. `ENERGY_LIMIT_KWH_PER_CYCLE` (si es mayor que cero) compara el acumulado del ciclo y publica una sola alarma por ciclo al alcanzar el límite. La potencia actual es la suma de los watts configurados para los actuadores encendidos.

`ENERGY_POWER_WATTS` usa los valores nominales de cada componente: foco de 60 W (placa), ventilador de 12 V × 0.42 A ≈ 5 W y servo de 5 V × 0.6 A = 3 W (pico con carga). La justificación completa está en la sección 11 del README de `Proyecto_2`. `ENERGY_LIMIT_KWH_PER_CYCLE` está en 0.01 kWh para la demostración (unos 10 minutos de foco encendido). Si los estados MQTT llegan espaciados, la estimación asume que el estado anterior se mantuvo durante todo el intervalo. Los estados con una marca de tiempo anterior al último estado procesado se descartan para no retroceder el contador.

## Consultas MongoDB para revisión

La persistencia se mantiene en MongoDB de acuerdo con la autorización del auxiliar. `tools/inicializar_mongodb_fase3.js` prepara de forma idempotente las colecciones e índices; se ejecuta desde la carpeta `Proyecto_2/Backend` con `mongosh "mongodb://<host>:27017" tools/inicializar_mongodb_fase3.js`. El backend también crea los índices al iniciar.

`tools/consultas_fase3.mongodb.js` contiene ejemplos listos para ejecutar con `mongosh` sobre la base `smartegg`: lecturas recientes y resumen diario, eventos de actuadores, anomalías, resultados de visión, bloqueos y último consumo por nodo. Los documentos de `energia_consumo` son snapshots acumulados; para el valor actual se consulta el más reciente y no se suman entre sí. El modelo y las colecciones de Fase 3 están documentados en `Proyecto_2/Docs/modelo-de-datos-fase3.md`.

## Colecciones MongoDB

- `lecturas`: telemetría de sensores, compatible con el historial previo.
- `actuadores_estado`, `ml_anomalias`, `vision_resultados`: eventos por tipo.
- `sistema_eventos`: comandos, bloqueos y desbloqueos.
- `estado_sistema`: último estado por `node_id`.
- `energia_consumo`: snapshots publicados de potencia y acumulado.
- `estado_energia`: estado anterior de actuadores y acumulados usado para integrar el siguiente intervalo.
- `mqtt_eventos`: topics auxiliares y estado de conexión.

Las rutas REST históricas quedan para consulta heredada; el control del ciclo y los actuadores de Fase 3 debe viajar por MQTT.
