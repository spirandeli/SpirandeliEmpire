# Guia de Resolução de Problemas (Troubleshooting)

### 1. Portas 80 ou 443 já em uso
Se você já tinha um Apache ou Nginx rodando no host antes de instalar o Docker:
```bash
sudo systemctl stop nginx apache2
sudo systemctl disable nginx apache2
docker compose restart caddy
```

### 2. Permissões de escrita no storage
Se o backend reportar erro ao gravar logs ou uploads:
```bash
sudo chmod -R 775 storage
```

### 3. Modelo do Ollama não baixou
Para forçar o download manual do modelo leve:
```bash
docker compose exec -T ollama ollama pull qwen2.5:3b
```

### 4. Redis ou Postgres não sobem
Inspecione os logs detalhados:
```bash
docker compose logs postgres
docker compose logs redis
```
Certifique-se de que o disco não está 100% cheio com `df -h`.

