# ==============================================================================
# MULTI-STAGE DOCKERFILE FOR ORDERS-API (FASTAPI)
# Diseño optimizado y liviano para producción y desarrollo en microservicios
# ==============================================================================

# Stage 1: Constructor de dependencias
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Imagen final de ejecución (Ligera y segura)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias ya compiladas del usuario del builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Añadir .local/bin al PATH para acceder a uvicorn
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
