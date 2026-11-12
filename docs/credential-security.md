# Segurança e Criptografia de Credenciais (SpirandeliEmpire OS 3.2)

## Criptografia em Repouso
- Todas as API Keys em `ai_provider_credentials.encrypted_api_key` são protegidas com **AES-256-GCM** autenticado ([security.py](file:///home/spira/spirandeliempire/backend/app/core/security.py)), no formato versionado `gcm:<versão>:<nonce_b64>:<ciphertext_b64>`.
- A chave mestra (`ENCRYPTION_MASTER_KEY`) permanece fora do banco de dados, em variáveis de ambiente/secret manager.
- Tokens legados em Fernet continuam sendo descriptografados de forma transparente para preservar credenciais existentes.

## Rotação de Chave Mestra
1. Defina a chave antiga em `PREVIOUS_ENCRYPTION_MASTER_KEY`.
2. Defina a nova chave em `ENCRYPTION_MASTER_KEY` e incremente `ENCRYPTION_KEY_VERSION` (ex.: `v2`).
3. Utilize `rotate_encrypted_secret(encrypted_api_key, "v2")` para re-criptografar registros salvos sem downtime.
4. Após validar que todos os registros foram migrados, remova `PREVIOUS_ENCRYPTION_MASTER_KEY`.

