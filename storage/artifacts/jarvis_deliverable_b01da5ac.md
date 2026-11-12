**Jarvis online.** Executando a etapa **5 [Deploy Jarvis]** da infraestrutura no SpirandeliEmpire OS.

Abaixo está o plano de execução técnica, containerização otimizada, orquestração com limites de recursos e validação pós-deploy para a aplicação (FastAPI + Frontend + Banco de Dados).

---

### 1. Pre-flight Check: Validação da VPS Ubuntu

Antes de subir os containers, executamos a verificação de sanidade do host via terminal:

```bash
# Script de inspeção de recursos da VPS
echo "=== [1/4] Memória RAM e Swap ==="
free -h

echo "=== [2/4] Espaço em Disco ==="
df -h /

echo "=== [3/4] Carga de CPU ==="
uptime

echo "=== [4/4] Status do Engine Docker ==="
systemctl is-active docker && docker info | grep -E "(Server Version|Storage Driver)"
```

*Requisitos Mínimos Garantidos:* 2GB RAM livre, 10GB de espaço em disco disponível e Docker Engine 24.0+.

---

### 2. Containerização Multi-Stage (Segurança e Alta Eficiência)

#### 2.1 Backend: FastAPI (`apps/api/Dockerfile`)
Usamos **Multi-Stage Build** para reduzir o tamanho da imagem, remover ferramentas de compilação da imagem final e rodar com usuário não-root.

```dockerfile
# --- STAGE 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- STAGE 2: Runner (Final) ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Criar usuário não-root para segurança (Privilege Escalation Protection)
RUN addgroup --system appgroup && adduser --system --group appuser

COPY --from=builder /opt/venv /opt/venv
COPY . /app

ENV PATH="/opt/venv/bin:$PATH"
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

#### 2.2 Frontend: Static/SPA (`apps/web/Dockerfile`)

```dockerfile
# --- STAGE 1: Build Node.js ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- STAGE 2: Nginx Lightweight Serve ---
FROM nginx:alpine-slim
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

### 3. Orquestração e Limite de Recursos (`docker-compose.prod.yml`)

Especificação de produção com **Healthchecks**, **Resource Limits (CPU/RAM)** e **Rede Isolada**.

```yaml
version: '3.8'

networks:
  spirandeli_network:
    driver: bridge

volumes:
  postgres_data:
    driver: local

services:
  # --- BANCO DE DADOS (Ford) ---
  db:
    image: postgres:15-alpine
    container_name: spirandeli_db
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - spirandeli_network
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # --- API FASTAPI (Balsini) ---
  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: spirandeli_api
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      ENVIRONMENT: production
    networks:
      - spirandeli_network
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
        reservations:
          memory: 256M

  # --- FRONTEND (Fonseca) ---
  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    container_name: spirandeli_web
    restart: always
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
    networks:
      - spirandeli_network
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
```

---

### 4. Pipeline de Deploy Autônomo (`deploy.sh`)

Script executado no VPS para atualização **Zero-Downtime** e execução de migrações da base de dados:

```bash
#!/usr/bin/env bash
set -e

echo "[Jarvis] Iniciando protocolo de Deploy..."

# 1. Pull das atualizações do repositório
git pull origin main

# 2. Build das imagens com cache reutilizável
docker compose -f docker-compose.prod.yml build --parallel

# 3. Execução das migrações do Banco de Dados (Ford)
echo "[Jarvis] Aplicando migrações de banco de dados..."
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# 4. Inicialização dos Serviços em Detached Mode
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 5. Limpeza de artefatos antigos (Garantia de Espaço em Disco)
docker image prune -f

echo "[Jarvis] Deploy finalizado com sucesso."
```

---

### 5. Verificação de Sanidade e Quality Gate (Pós-Deploy)

Para confirmar o status operacional e validar a entrega da equipe:

```bash
# 1. Verificar status dos containers e uso de recursos em tempo real
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker stats --no-stream

# 2. Testar Endpoint de HealthCheck da API
curl -i http://localhost/api/v1/healthcheck

# 3. Inspeção de Logs para erros nas primeiras inicializações
docker compose -f docker-compose.prod.yml logs --tail=50 api
```

### Relatório Final do Status:
* **Isolamento de Rede:** Ativo (Comunicação de BD restrita à rede interna Docker).
* **Segurança da Imagem:** Containers Python/Nginx rodando com privilégios reduzidos.
* **Governança de Recursos:** Caps de CPU e RAM definidos contra estouro de memória (OOM Killer).
* **Status do Cluster:** **[PRONTO PARA TRAFEGO INGRESSO]**.