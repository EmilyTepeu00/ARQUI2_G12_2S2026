#!/usr/bin/env bash
# Crea (o completa) el grupo de seguridad de la EC2 con solo los puertos necesarios.
# Uso: bash crear_puertos_aws.sh ID_INSTANCIA      (ej. i-0abc123...)
set -euo pipefail
instancia=${1:?Uso: crear_puertos_aws.sh ID_INSTANCIA}
nombre=${SG_NOMBRE:-smartegg-fase3}
mi_ip=$(curl -fsS https://checkip.amazonaws.com)/32

vpc=$(aws ec2 describe-instances --instance-ids "$instancia" --query 'Reservations[0].Instances[0].VpcId' --output text)
sg=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$nombre" "Name=vpc-id,Values=$vpc" \
     --query 'SecurityGroups[0].GroupId' --output text)
if [[ "$sg" == None ]]; then
    sg=$(aws ec2 create-security-group --group-name "$nombre" --description "SmartEgg Fase 3" --vpc-id "$vpc" \
         --query GroupId --output text)
fi

abrir() {  # puerto origen; ignora la regla si ya existe
    aws ec2 authorize-security-group-ingress --group-id "$sg" --protocol tcp --port "$1" --cidr "$2" >/dev/null 2>&1 \
        && echo "abierto $1 <- $2" || echo "ya existía $1 <- $2"
}
abrir 22 "$mi_ip"        # SSH solo desde esta PC
abrir 1883 0.0.0.0/0     # MQTT (puente del Arduino); exige usuario y contraseña
abrir 9001 0.0.0.0/0     # MQTT WebSocket (página del bucket)
abrir 3000 0.0.0.0/0     # Grafana en /grafana/
abrir 5000 0.0.0.0/0     # API de consulta y Swagger

# Agrega el grupo a la instancia sin quitarle los que ya tenga.
actuales=$(aws ec2 describe-instances --instance-ids "$instancia" \
           --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' --output text)
aws ec2 modify-instance-attribute --instance-id "$instancia" --groups $(echo "$actuales $sg" | tr ' \t' '\n\n' | sort -u)
echo "Grupo $sg aplicado a $instancia. MongoDB (27017) queda cerrado."
