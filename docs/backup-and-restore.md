# Estratégia de Backup e Recuperação de Desastres

Conforme estipulado na Seção 16 da especificação, backups não são considerados válidos sem testes reais de restauração e integridade.

---

## 1. Estratégia de Backup

O script `scripts/backup.sh` executa as seguintes etapas:
1. **Dump do Banco de Dados:** Executa `pg_dump` no container `empire_postgres`.
2. **Arquivamento de Conteúdos:** Compacta todos os arquivos persistentes em `storage/businesses/` e a cópia de configuração `.env`.
3. **Checksum Criptográfico:** Gera automaticamente um arquivo `.sha256` para validação de integridade.
4. **Política de Retenção:** Remove backups locais com mais de 14 dias de existência para preservar o espaço em disco da VPS.

### Agendamento no Cron (Diário às 03:00)
```bash
0 3 * * * /caminho/do/projeto/scripts/backup.sh >> /var/log/empire_backup.log 2>&1
```

---

## 2. Procedimento de Restauração

Para restaurar um backup existente:
```bash
./scripts/restore.sh /var/spirandeli/backups/empire_backup_YYYYMMDD_HHMMSS.tar.gz
```
O script verifica o hash SHA256 antes da extração, solicita confirmação para evitar sobreescrita acidental e restaura as tabelas do PostgreSQL e os arquivos dos negócios.

