# Grafana

Carpeta montada por `infra/docker-compose.yml` en `/etc/grafana/provisioning`.
Todo lo de aca se carga **solo** al levantar el stack: no hay que dar de alta
nada a mano en la interfaz.

Se entra por <http://localhost:8080/grafana/>. Ojo: `localhost:3000` a secas da
404, porque Grafana esta configurada para servirse bajo la subruta `/grafana/`.

## Que hay

```
provisioning/
  datasources/datasources.yml       los dos origenes de datos
  dashboards/dashboards.yml         el proveedor que carga los .json
  dashboards/smartegg-tiempo-real.json
  dashboards/smartegg-historico.json
```

## Los dos datasources, y por que son dos

**SmartEgg MQTT** (`grafana-mqtt-datasource`) se conecta al broker en
`tcp://mosquitto:1883`. Queda configurado para explorar topicos a mano, pero
**ningun dashboard lo usa**, por lo que se explica abajo.

**SmartEgg API** (`yesoreyeram-infinity-datasource`) consulta
`http://backend:5000/api/historico/*`. Este es el rodeo importante: **MongoDB no
tiene datasource gratuito en Grafana** — el oficial es solo de la version
Enterprise. Asi que el historico no sale de la base directamente, sino de la API
REST, que devuelve los datos **ya agregados por Mongo** (promedios por bloque de
tiempo, conteos por dia, totales por operador). El navegador recibe decenas de
puntos en vez de miles de lecturas crudas.

Esos endpoints son publicos de solo lectura, asi que Grafana no maneja tokens.

Los host son **nombres de servicio de Docker** (`mosquitto`, `backend`), no
`localhost`: dentro de la red de contenedores, `localhost` para Grafana es el
propio contenedor de Grafana.

## Los dos dashboards

| Dashboard | Origen | Refresco | Para que |
| :-- | :-- | :-- | :-- |
| SmartEgg - Tiempo real | API REST | 5 s | Temperatura, humedad y espacios libres ahora, actuadores, ultimos 15 min, alarmas y accesos |
| SmartEgg - Historico | API REST | 1 min | Series por intervalo, alarmas por tipo, actividad por operador y resumen diario |

## Por que el dashboard de tiempo real no usa MQTT

Deberia usarlo, y de hecho estuvo escrito asi. Pero el plugin
`grafana-mqtt-datasource` **tiene un bug en la suscripcion**: conecta bien al
broker (se ve el cliente `grafana_...` en el log de mosquitto) y su
"Save & test" pasa, pero cuando un panel se suscribe a un topico responde:

    invalid orgId supplied in request

Ese mensaje sale del **binario del propio plugin** (`gpx_mqtt_linux_amd64`), no
de Grafana. Se reprodujo con las versiones 1.2.1, 1.3.0, 1.3.5 y 1.3.6 del
plugin, sobre Grafana 11.6.11 y 12.2.5, y tanto con el datasource
aprovisionado por archivo como creado desde la API. No es un problema de
configuracion de este repositorio y no se puede arreglar desde afuera.

Asi que el dashboard lee la API, que sirve **la misma lectura** que el backend
acaba de recibir por el puerto serial: con refresco de 5 segundos, la latencia
entre que el nodo mide y esto lo muestra es de segundos.

El tiempo real por MQTT **si funciona** y se demuestra en otros dos lados:

* El frontend se conecta al broker por WebSocket (`/mqtt`) y recibe las
  alarmas sin recargar la pagina.
* `docker compose exec -T mosquitto mosquitto_sub -h localhost -t 'smartegg/#' -v`

Si el plugin se arregla en una version futura, volver a MQTT es cambiar el
`datasource` de los paneles del `.json`; el datasource ya esta configurado.

El de historico tiene dos variables arriba: **Agrupar cada** (1 a 60 min) y
**Dias del resumen**. El selector de tiempo de Grafana tambien filtra: los
paneles le pasan el rango a la API en `desde` y `hasta`.

## Como editar y que el cambio no se pierda

`allowUiUpdates` esta en `true`, asi que se pueden editar los paneles desde la
interfaz. **Pero esos cambios viven en el volumen `smartegg_grafana_data`, no en
el repositorio.** Para versionar un cambio:

1. Editar el panel en la interfaz.
2. Dashboard → Share → Export → **Save to file**.
3. Reemplazar el `.json` correspondiente en `provisioning/dashboards/`.
4. Commitear.

Un `docker compose down -v` borra ese volumen y con el los dashboards, los
datasources dados de alta a mano **y la clave de admin**. Lo provisionado vuelve
solo; lo que no se exporto, no.

## Si algo no se ve

**Los paneles de tiempo real estan vacios.** No hay lecturas llegando. Hace
falta que el Arduino este conectado, o el simulador corriendo. Se comprueba
con:

    curl -s http://localhost:8080/api/sensores/estado

`ultima_lectura_recibida` no puede ser `null`.

**Los paneles del historico estan vacios.** Revisar que el rango de tiempo de
arriba a la derecha cubra fechas donde haya datos. Se comprueba con:

    curl -s "http://localhost:8080/api/historico/diario?dias=30"

**Aparece "It looks like you are trying to access MongoDB over HTTP".** Es que
algo esta apuntando al puerto 27017 por HTTP. El 27017 habla el protocolo nativo
de Mongo, no HTTP; el historico se consulta por la API, no contra la base.

**La clave de admin no funciona.** `GRAFANA_ADMIN_PASSWORD` del `.env` solo se
aplica la **primera** vez que Grafana crea su base interna. Si se cambio desde la
interfaz, manda esa. Para resetearla:

    docker compose exec grafana grafana cli admin reset-admin-password 'nueva'

Grafana ademas bloquea al usuario 5 minutos despues de 5 intentos fallidos.
