# AI Model Manager (SpirandeliEmpire OS 3.2)

Acessível em **AI Model Manager** no painel ou via `/api/v1/ai-settings/`:

1. **Seleção Global:** Define provedor, conexão e modelo padrão do usuário. Nenhum provedor/modelo é imposto globalmente.
2. **Seleção Individual dos 14 Agentes:** Tabela para configurar cada agente (`Jeffrey`, `Fonseca`, `Balsini`, `Jarvis`, `Noé`, `Ford`, `Murphy`, `Script Agent`, `Voice Agent`, `Subtitle Agent`, `Clipador Agent`, `News Agent`, `Designer Agent`, `Video Agent`) com provedor, conexão e modelo independentes.
3. **Perfis por Tipo de Tarefa:** `complex_planning`, `reasoning`, `coding`, `code_review`, `research`, `writing`, `summarization`, `image_analysis`, `transcription`, `fast_tasks`, `cost_efficient`.
4. **Fallback Configurável:** Desabilitado por padrão. Quando habilitado, segue exatamente a ordem definida pelo usuário e registra a falha original e o modelo utilizado em `ai_usage_records`.
5. **Consumo e Tokens (`/api/v1/ai-usage/`):** Rastreamento de tokens de entrada, saída, cache, latência e falhas por agente, modelo e provedor.

