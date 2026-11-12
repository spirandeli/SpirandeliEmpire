# 06 — Auditoria de Segurança de Credenciais e Preservação Gemini

**Data:** 2026-11-12

## 1. Criptografia e Armazenamento ([core/security.py](file:///home/spira/spirandeliempire/backend/app/core/security.py))
- **Algoritmo:** `AES-256-GCM` com nonce aleatório de 12 bytes (`os.urandom(12)`), envelope versionado `gcm:<ver>:<nonce_b64>:<ct_b64>` e AAD autenticado.
- **Rotação de Chave:** `rotate_encrypted_secret()` suporta `PREVIOUS_ENCRYPTION_MASTER_KEY` e re-encriptação para `ENCRYPTION_KEY_VERSION` atual (testado em `test_aes256_gcm_encryption_and_key_rotation`).
- **Exposição:** Banco armazena apenas `encrypted_api_key`; APIs retornam exclusivamente `masked_key` (`sk-a****5678`); logs e estado LangGraph não transportam chaves em texto puro; descriptografia ocorre exclusivamente no backend (`ModelDiscoveryService` e `ModelRouter`).

## 2. Preservação da Chave Gemini Existente
- **Origem:** `IntegrationModel(id="gemini")` e variável `.env` preservadas sem modificação ou impressão de segredo.
- **Verificação no PostgreSQL em Execução:**
  - `legacy_integration_gemini_present`: `True`
  - Conta `owner@spirandeliempire.local` (`owner`) possui registro `AIProviderCredentialModel` (`label="Gemini Principal (Migrada)"`, `status="connected"`, `masked="AQ.A****DJ0A"`), descriptografável e validado ao vivo contra a API do Google Gemini (`767ms`, `63` modelos sincronizados).

