# Guia de Instalação em VPS Linux Limpa

Este guia descreve como implantar o **SpirandeliEmpire OS v2.0** a partir de um repositório Git em uma VPS limpa rodando **Ubuntu Server 24.04 LTS** (ou Debian 12).

---

## 1. Requisitos Mínimos Recomendados

- **Processador:** 2 a 4 vCPUs
- **Memória RAM:** 4 GB a 8 GB (mínimo de 4 GB com 2 GB de Swap)
- **Disco:** 40 GB a 100 GB SSD/NVMe
- **Portas Liberadas:** 80 (HTTP), 443 (HTTPS), 22 (SSH)
- **Orçamento Mensal da VPS:** Até R$ 60 a R$ 120/mês (dentro do teto global de R$ 200/mês)

---

## 2. Passo a Passo de Implantação

### Passo 1 — Conectar na VPS via SSH
```bash
ssh root@seu-ip-da-vps
```

### Passo 2 — Clonar o Repositório
```bash
git clone <URL_DO_SEU_REPOSITORIO_GIT> spirandeli-empire-os
cd spirandeli-empire-os
```

### Passo 3 — Configurar o Arquivo de Ambiente
Copie o template e edite suas variáveis:
```bash
cp .env.example .env
nano .env
```
> **Atenção:** Configure o `DOMAIN` com o domínio que aponta para o IP da VPS e ajuste a senha do PostgreSQL e do Redis.

### Passo 4 — Executar o Instalador Automatizado
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

O script cuidará de:
1. Verificar e instalar Docker e Docker Compose plugin caso não existam.
2. Criar a estrutura de diretórios e permissões do storage.
3. Subir todos os containers via Docker Compose.
4. Executar migrations e seeds do banco de dados PostgreSQL.
5. Baixar o modelo local `qwen2.5:3b` no Ollama.
6. Executar diagnósticos de saúde (healthcheck).
7. Exibir a URL de acesso com SSL automático gerenciado pelo Caddy.

---

## 3. Comandos Úteis no Dia a Dia

- **Verificar status dos serviços:**
  ```bash
  ./scripts/healthcheck.sh
  ```
- **Atualizar o sistema com backup prévio:**
  ```bash
  ./scripts/update.sh
  ```
- **Gerar backup manual:**
  ```bash
  ./scripts/backup.sh
  ```
- **Ver logs em tempo real:**
  ```bash
  docker compose logs -f
  ```

