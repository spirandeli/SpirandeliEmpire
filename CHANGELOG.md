# Changelog - SpirandeliEmpire OS

## [2.0.0] - 2026-11-03
### Added
- Especificação Mestre de Arquitetura implementada integralmente.
- Orquestrador Central Jeffrey e catálogo de 11 agentes especializados.
- Core Backend em Laravel 11 com migrations, seeders, models, policies e controllers API.
- Dashboard Vue 3 + Tailwind CSS com suporte a visualização de métricas e chat com Jeffrey.
- Suporte a distribuição estática pré-compilada em `core/frontend/dist/index.html`.
- Suporte a Docker Compose multi-serviço (Caddy, Backend, Workers, Postgres 16, Redis 7, Ollama, Uptime Kuma).
- Scripts de infraestrutura para VPS: `install.sh`, `update.sh`, `backup.sh`, `restore.sh`, `healthcheck.sh`, `uninstall.sh`.
- AI Engine local com Ollama (`qwen2.5:3b`), Piper Neural TTS (voz brasileira) e FFmpeg.
- Guardrails orçamentários rígidos com teto de R$ 200/mês.
- Templates iniciais para RISADA.exe, KDP Factory, Digital Products e Printable Factory.

