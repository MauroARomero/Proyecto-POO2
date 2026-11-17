# Imagen de la API "Tienda" (FastAPI + PostgreSQL)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY db ./db

RUN useradd --system --uid 10001 appuser
USER appuser

EXPOSE 8000

# Un solo worker por contenedor/pod: la escalabilidad horizontal se logra
# aumentando réplicas, no procesos dentro del contenedor.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY} --no-access-log"]
