# Simple, reliable image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

# PROM_URL is injected by Kubernetes
ENV PROM_URL="http://localhost:9090"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
