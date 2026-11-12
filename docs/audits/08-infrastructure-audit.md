# 08 — Auditoria de Infraestrutura, Docker, VPS, Backup e Restore

**Data da Auditoria:** 2026-11-12  
**Escopo:** Prompt 08 — Docker, Docker Compose, Ubuntu VPS, Nginx/HTTPS, Backup, Restore Controlado, Deploy e Segurança.

---

## 1. Resumo Executivo

A auditoria inicial de infraestrutura identificou que `infrastructure/scripts/` estava vazio (sem backup, restore ou deploy), `backend/Dockerfile` não copiava `alembic/` nem `alembic.ini`, `postgres` e `redis` estavam expostos em `0.0.0.0`, `worker` não recebia `ENCRYPTION_MASTER_KEY` nem `APP_KEY`, e `nginx.conf` não possuía compressão `gzip`, headers de segurança nem rota `/health`.

Todos os problemas foram corrigidos e validados com deploy completo (`deploy.sh`), backup real (`backup.sh`) e **restore controlado em banco separado (`spirandeliempire_restore_test`)**.

---

## 2. Problemas Encontrados e Correções Aplicadas

### 2.1. Docker & Docker Compose ([docker-compose.yml](file:///home/spira/spirandeliempire/docker-compose.yml), [backend/Dockerfile](file:///home/spira/spirandeliempire/backend/Dockerfile))
- Copiados `alembic.ini` e `alembic/` no `backend/Dockerfile` para permitir migrations dentro do container.
- Restringido bind de `postgres` (`127.0.0.1:5432:5432`) e `redis` (`127.0.0.1:6379:6379`) para evitar exposição pública na VPS.
- Adicionadas variáveis `ENCRYPTION_MASTER_KEY`, `ENCRYPTION_KEY_VERSION`, `APP_KEY`, `INITIAL_ADMIN_*`, `REGISTRATION_MODE` e `COOKIE_SECURE` ao `backend` e `worker`.
- Adicionado `healthcheck` no `backend` (`curl -fsS http://localhost:8000/health`), `condition: service_healthy` nas dependências, rotação de logs (`json-file`, `max-size: 10m`, `max-file: 3`) e limites de memória (`mem_limit`: `1536m` backend/worker, `256m` frontend, `128m` nginx).

### 2.2. Nginx & HTTPS ([nginx.conf](file:///home/spira/spirandeliempire/infrastructure/nginx/nginx.conf), [nginx-ssl.conf.example](file:///home/spira/spirandeliempire/infrastructure/nginx/nginx-ssl.conf.example))
- Adicionado `gzip on;` para assets estáticos e JSON.
- Adicionados headers de segurança (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`).
- Adicionada rota `location = /health` apontando para `backend_api/health` e `proxy_read_timeout 120s` em `/api/`.
- Criado template completo de produção HTTPS/TLS com Certbot/Let's Encrypt em [nginx-ssl.conf.example](file:///home/spira/spirandeliempire/infrastructure/nginx/nginx-ssl.conf.example).

### 2.3. Scripts de Backup, Restore e Deploy (`infrastructure/scripts/`)
- [backup.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/backup.sh): Executa `pg_dump -Fc` e compacta `storage/` (`artifacts` + `checkpoints`) com permissão `600`, **sem incluir `.env` em texto claro**.
- [restore.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/restore.sh): Restaura dump PostgreSQL (`pg_restore --clean --if-exists --no-owner`) e `storage/` em banco e diretório alvo configuráveis.
- [deploy.sh](file:///home/spira/spirandeliempire/infrastructure/scripts/deploy.sh): Executa `docker compose up -d --build`, `docker compose exec -T backend alembic upgrade head` e valida `/health`.

---

## 3. Evidências de Execução

### 3.1. Recursos da VPS Ubuntu Observados
- Memória RAM: `17Gi` total (`7.1Gi` disponível), Swap `5.0Gi`.
- Disco (`/`): `1007G` total, `333G` usados (`35%`), `624G` livres.
- Containers ativos: `spirandeli-postgres` (healthy), `spirandeli-redis` (healthy), `spirandeli-backend` (healthy), `spirandeli-worker` (up), `spirandeli-frontend` (up), `spirandeli-nginx` (up na porta `8086`).

### 3.2. Deploy e Migrations (`./infrastructure/scripts/deploy.sh`)
- Build das imagens `backend`, `worker` e `frontend` concluído com exit code `0`.
- `alembic upgrade head` executado dentro do container `spirandeli-backend`.
- `GET http://localhost:8086/health` retornou:
  `{"status":"healthy","system":"SpirandeliEmpire OS","version":"3.2.0","environment":"development","dependencies":{"database":"ok","redis":"ok"}}`.

### 3.3. Backup e Restore Controlado (`PASS`)
- Executado `./infrastructure/scripts/backup.sh /tmp/spirandeli_backups` → gerado `spirandeli_backup_20261112_120025.tar.gz`.
- Executado `./infrastructure/scripts/restore.sh ... spirandeliempire_restore_test /tmp/spirandeli_restore_test`.
- Validação de integridade no banco restaurado `spirandeliempire_restore_test`:
  - `users`: **16** | `agents`: **14** | `projects`: **3** | `workflows`: **30** | `creds`: **4** | `models`: **65**.
- Ambiente temporário de teste (`spirandeliempire_restore_test` e `/tmp/spirandeli_*`) removido após validação.

