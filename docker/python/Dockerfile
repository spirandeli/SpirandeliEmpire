FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Instala dependências de compilação mínimas + FFmpeg nativo e fontes para legendas .ass
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivos de dependência
COPY backend-python/pyproject.toml backend-python/README.md /app/

# Instala dependências Python
RUN pip install --upgrade pip && \
    pip install ".[dev]"

# Copia o código fonte
COPY backend-python /app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

