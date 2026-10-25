#!/bin/sh
set -eu
: "${MQTT_USER:?Falta MQTT_USER}" "${MQTT_PASS:?Falta MQTT_PASS}"
umask 077
mosquitto_passwd -b -c /mosquitto/data/passwd "$MQTT_USER" "$MQTT_PASS"
chown mosquitto:mosquitto /mosquitto/data/passwd
exec /docker-entrypoint.sh /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
