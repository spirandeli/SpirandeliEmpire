FROM python:3.11-slim

# Install system utilities, multimedia & anti-ban tools (ffmpeg + exiftool)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libimage-exiftool-perl \
    curl \
    git \
    build-essential \
    libpq-dev \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS binary (fast local lightweight neural TTS)
RUN curl -L https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_x86_64.tar.gz | tar -xz -C /usr/local/bin --strip-components=1 piper/piper || true

WORKDIR /app

# Install Python dependencies (core orchestrator + telegram bot)
COPY jeffrey/core/requirements.txt /tmp/core_requirements.txt
COPY jeffrey/telegram/requirements.txt /tmp/telegram_requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/core_requirements.txt \
    -r /tmp/telegram_requirements.txt

# Create models directory
RUN mkdir -p /opt/ai-engine/models

CMD ["python", "-u", "/app/jeffrey/core/orchestrator_worker.py"]

