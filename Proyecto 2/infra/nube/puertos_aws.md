# Grupo de seguridad EC2

Lo más fácil: desde una PC con AWS CLI configurado (`aws configure`):

```bash
bash infra/nube/crear_puertos_aws.sh i-XXXXXXXXXXXX   # ID de la instancia
```

Reglas TCP de entrada que crea (o, si lo hace a mano en la consola, las mismas):

| Puerto | Origen | Uso |
| --- | --- | --- |
| 22 | IP de su PC/32 | SSH |
| 1883 | 0.0.0.0/0 | MQTT: puente del Arduino y servicios |
| 9001 | 0.0.0.0/0 | MQTT sobre WebSocket: página del bucket |
| 3000 | 0.0.0.0/0 | Grafana en `/grafana/` |
| 5000 | 0.0.0.0/0 | API de consulta del backend y Swagger (`/api/docs`); no controla actuadores |

No abra 27017 (MongoDB), 5173 (frontend React) ni 8080 (Caddy): no se usan desde fuera de la VM. MongoDB se revisa por túnel SSH. 1883 y 9001 están abiertos a cualquier IP para que la calificación funcione desde cualquier red, pero el broker exige usuario y contraseña (`allow_anonymous false`). Use una Elastic IP para que la IP pública no cambie al reiniciar la instancia.

HTTP/MQTT/WS no cifran el tráfico y la URL del panel lleva la contraseña: use una contraseña solo para la demo y cámbiela al terminar.
