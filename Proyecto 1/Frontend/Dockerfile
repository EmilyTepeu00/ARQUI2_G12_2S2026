# Etapa 1: build
FROM node:20-alpine AS build
WORKDIR /app

# Se copian solo los manifiestos primero para que la capa de dependencias se
# reutilice mientras package.json y el lock no cambien.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# No se pasan URLs de API ni de broker a proposito: el codigo usa rutas
# relativas (/api, /mqtt) y las resuelve el proxy en tiempo de ejecucion. Asi la
# misma imagen sirve en local y detras del tunel publico, sin recompilar.
# Estas dos si son de compilacion porque tienen que calzar con el backend.
ARG VITE_MQTT_TOPIC_PREFIX=smartegg
ARG VITE_MQTT_NODE_ID=incubadora-01
ENV VITE_MQTT_TOPIC_PREFIX=${VITE_MQTT_TOPIC_PREFIX} \
    VITE_MQTT_NODE_ID=${VITE_MQTT_NODE_ID}

RUN npm run build

# Etapa 2: servir con Nginx
FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
