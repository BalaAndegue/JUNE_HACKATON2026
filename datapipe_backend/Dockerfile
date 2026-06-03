FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build deps (pandas/duckdb wheels usually suffice; build-essential is a safety net)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent dirs (mounted as volumes in docker-compose)
RUN mkdir -p /app/instance /app/uploads

EXPOSE 5000

# Production server. run.py exposes `app = create_app()`.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "run:app"]
