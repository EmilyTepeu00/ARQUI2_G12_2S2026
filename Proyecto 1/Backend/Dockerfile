# Backend SmartEgg: API REST + cliente MQTT + lector serial
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Primero las dependencias, para aprovechar la cache de capas de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario sin privilegios. El grupo dialout es el que da acceso a /dev/ttyUSB0
# cuando se pasa el nodo fisico al contenedor con `devices:`.
RUN groupadd -r smartegg \
    && useradd -r -g smartegg -G dialout smartegg \
    && chown -R smartegg:smartegg /app
USER smartegg

EXPOSE 5000

# El healthcheck usa Python en vez de curl: asi la imagen no necesita apt-get
# y se construye sin depender de los mirrors de Debian.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health', timeout=3).status == 200 else 1)"]

# IMPORTANTE: 1 solo worker.
# create_app() levanta el hilo del serial y el cliente MQTT; con varios workers
# habria N lectores peleando por el mismo puerto y N clientes MQTT publicando
# duplicado. La concurrencia se resuelve con hilos, no con procesos.
# El manejo de senales lo aporta Docker con `init: true` en el compose.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", \
     "--workers", "1", "--threads", "8", \
     "--timeout", "120", "--graceful-timeout", "30", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "run:app"]
