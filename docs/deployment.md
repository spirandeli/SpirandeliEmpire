# Guia de Deploy & Operação na VPS — SpirandeliEmpire OS 3.1

## 1. Requisitos de Infraestrutura
- Ubuntu VPS 22.04 LTS ou 24.04 LTS
- Docker & Docker Compose v2
- Mínimo de 2 vCPU e 2GB RAM (sem GPU necessária)

## 2. Inicialização Rápida via Docker Compose

```bash
# 1. Clone ou acesse o repositório
cd /home/spira/spirandeliempire

# 2. Crie e configure o arquivo de ambiente
cp .env.example .env

# 3. Suba todos os containers com Docker Compose
docker compose up -d --build
```

## 3. Serviços em Execução

| Serviço | Container | Porta Interna | Porta Exposta |
|---|---|---|---|
| Nginx Reverse Proxy | `spirandeli-nginx` | 80 | `8080` (ou `80`) |
| FastAPI Backend | `spirandeli-backend` | 8000 | - |
| Celery Worker | `spirandeli-worker` | - | - |
| Frontend React PWA | `spirandeli-frontend` | 80 | - |
| PostgreSQL 16 | `spirandeli-postgres` | 5432 | `5432` |
| Redis 7 | `spirandeli-redis` | 6379 | `6379` |

## 4. Testes e Validação Automatizada

```bash
cd backend
uv run pytest
```

