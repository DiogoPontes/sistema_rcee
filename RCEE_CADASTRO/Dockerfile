FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# deps do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install first to leverage cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY . /app

# Create uploads folder (ajuste caminho conforme seu app)
RUN mkdir -p /app/app/static/uploads && chown -R root:root /app/app/static/uploads

EXPOSE 5000

# Healthcheck (opcional) — garanta que sua app implemente /health
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD curl -f http://localhost:5000/health || exit 1

# Start with Waitress (ajuste module:app se necessário)
CMD ["python", "-m", "waitress", "--listen=0.0.0.0:5000", "run:app"]