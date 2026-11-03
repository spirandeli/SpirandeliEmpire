# Política de Segurança — SpirandeliEmpire OS

## Relato de Vulnerabilidades
Se você identificar qualquer vulnerabilidade de segurança neste sistema, por favor não abra uma issue pública. Entre em contato diretamente com o administrador do sistema pelo email configurado em `ADMIN_EMAIL`.

## Práticas Obrigatórias
- Nunca commite o arquivo `.env` com senhas ou chaves reais para o Git.
- Mantenha a autenticação SSH por chave e desative o login root por senha na VPS.
- Restrinja o acesso externo a portas internas (Postgres, Redis, Ollama).

