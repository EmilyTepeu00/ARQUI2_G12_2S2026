FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline.py service.py ./
COPY modelo/ modelo/
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "service.py"]
