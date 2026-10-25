#!/usr/bin/env bash
set -euo pipefail
: "${1:?Uso: subir_web_s3.sh NOMBRE_BUCKET IP_PUBLICA}"
: "${2:?Falta IP pública de EC2}"
: "${MQTT_USER:=smartegg}" "${MQTT_PASS:?Exporte MQTT_PASS}"
export MQTT_USER MQTT_PASS
bucket=$1
ip=$2
region=${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}
raiz=$(cd "$(dirname "$0")/../.." && pwd)
if ! aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
    if [[ "$region" == us-east-1 ]]; then
        aws s3api create-bucket --bucket "$bucket" --region "$region"
    else
        aws s3api create-bucket --bucket "$bucket" --region "$region" --create-bucket-configuration "LocationConstraint=$region"
    fi
fi
# También falla si el bucket pertenece a otra cuenta.
aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration 'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false'
aws s3api put-bucket-website --bucket "$bucket" --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'
politica=$(python3 - "$bucket" <<'PY'
import json, sys
print(json.dumps({'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': '*', 'Action': 's3:GetObject', 'Resource': f'arn:aws:s3:::{sys.argv[1]}/*'}]}))
PY
)
aws s3api put-bucket-policy --bucket "$bucket" --policy "$politica"
aws s3 sync "$raiz/web/" "s3://$bucket/" --region "$region"
endpoint=$(aws s3api get-bucket-location --bucket "$bucket" --query LocationConstraint --output text)
[[ "$endpoint" == None ]] && endpoint=us-east-1
[[ "$endpoint" == EU ]] && endpoint=eu-west-1
python3 - "$bucket" "$endpoint" "$ip" <<'PY'
import os, sys
from urllib.parse import urlencode
bucket, region, ip = sys.argv[1:]
guion = region in ('us-east-1', 'us-west-1', 'us-west-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'eu-west-1', 'sa-east-1')
url = f'http://{bucket}.s3-website{"-" if guion else "."}{region}.amazonaws.com'
print(url + '/?' + urlencode({'url': f'ws://{ip}:9001', 'user': os.environ['MQTT_USER'], 'pass': os.environ['MQTT_PASS'], 'node': os.getenv('NODE_ID', 'incubadora-01')}))
PY
