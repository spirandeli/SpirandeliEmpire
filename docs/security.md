# Políticas e Diretrizes de Segurança — SpirandeliEmpire OS

A segurança e a governança operacional são prioridades fundamentais (Seção 2 e Seção 15 da especificação mestre).

---

## 1. Hardening do Servidor (VPS)

1. **Acesso SSH:**
   - Autenticação obrigatória por chave criptográfica Ed25519 ou RSA 4096.
   - Desativação do login por senha no `/etc/ssh/sshd_config` (`PasswordAuthentication no`).
2. **Firewall (UFW):**
   - Script automatizado em `infrastructure/security/ufw-setup.sh`.
   - Apenas portas 22 (SSH), 80 (HTTP) e 443 (HTTPS) expostas publicamente.
   - Banco de dados PostgreSQL (5432), Redis (6379), Ollama (11434) e Uptime Kuma (3001) ficam restritos à rede interna do Docker (`empire-network`).
3. **Fail2ban:**
   - Proteção contra força bruta em SSH configurada em `infrastructure/security/fail2ban-jail.local`.

---

## 2. Proteção dos Agentes e de Jeffrey

1. **Sem Comandos Arbitrários:** O orquestrador não possui permissão para executar chamadas livres ao shell do host.
2. **Gatekeeper de Permissões:** Todas as ações que envolvam custos financeiros, publicação de mídias ou exclusão de dados exigem autorização humana no painel.
3. **Memória Limpa:** Nenhum token de acesso, credencial ou senha é registrado na memória operacional persistente ou nos prompts dos agentes.
4. **Isolamento de Negócios:** Os contextos de geração e armazenamento de cada negócio permanecem estritamente separados em diretórios dedicados.

