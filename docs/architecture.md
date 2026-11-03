# SpirandeliEmpire OS — Arquitetura de Sistema v2.0

## 1. Visão Geral Arquitetural

O **SpirandeliEmpire OS** é concebido como um centro de comando unificado para múltiplos negócios digitais independentes. A plataforma opera sobre três premissas fundamentais:
1. **Núcleo Administrativo Central (Core):** Responsável por autenticação, governança financeira, dashboard unificada e monitoramento da infraestrutura.
2. **Agente Orquestrador Central (Jeffrey):** Assistente executivo de IA que coordena agentes especializados e planeja operações com suporte multi-provedor (Google Gemini, OpenAI e Llama Local).
3. **Múltiplos Negócios Independentes (Businesses):** Instâncias totalmente isoladas com volumes, configurações, orçamentos e logs próprios.

```mermaid
flowchart TD
    User["Proprietário (Comandante)"] --> Caddy["Caddy Reverse Proxy (HTTPS/TLS)"]
    Caddy --> Vue["Frontend Vue 3 (Dashboard Central)"]
    Caddy --> Laravel["Core Backend (Laravel 11 / PHP 8.3)"]
    
    Laravel --> DB[("PostgreSQL 16")]
    Laravel --> Redis[("Redis 7 (Filas & Cache)")]
    
    Laravel --> Gateway["AI Gateway Multi-Provedor"]
    Gateway --> Gemini["1º: Google Gemini (Free Tier / Créditos)"]
    Gateway --> OpenAI["2º: OpenAI GPT-4o-mini (Créditos/Planos)"]
    Gateway --> Ollama["3º: Llama Local via Ollama (100% Free & Offline)"]
    
    Laravel --> Jeffrey["Jeffrey Orchestrator & Workers"]
    Jeffrey --> Gateway
    Jeffrey --> Piper["Piper TTS (Voz Neural Local)"]
    Jeffrey --> FFmpeg["FFmpeg Video Engine"]
    
    Jeffrey --> Gatekeeper{"Security & Budget Gatekeeper (R$ 200/mês)"}
    Gatekeeper --> Biz1["Negócio: RISADA.exe (YouTube Dark)"]
    Gatekeeper --> Biz2["Negócio: KDP Factory"]
    Gatekeeper --> Biz3["Negócio: Digital Products"]
    Gatekeeper --> Biz4["Negócio: Printable Factory"]
```

## 2. Princípios de Isolamento e Segurança
- **Independência de Falhas:** O encerramento, falha ou remoção de um negócio jamais afeta o Core ou os demais negócios.
- **Isolamento de Armazenamento:** Cada negócio grava exclusivamente em seu subdiretório `storage/businesses/<slug>`.
- **Governança Orçamentária:** Teto máximo de R$ 200,00 mensais com alerta automático aos 80% e bloqueio de novas despesas sem aprovação humana.
- **Gateway Híbrido de IA:** Prioriza cotas gratuitas do Google AI Studio (15 RPM a R$ 0,00) e créditos OpenAI; caso qualquer um atinja limites ou fique indisponível, aciona automaticamente o Llama local no Ollama sem interrupção de serviço.
