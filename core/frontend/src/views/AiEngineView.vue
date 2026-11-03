<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          AI Engine — Gateway Multi-Provedor & Governança de Tokens
          <span class="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
            Híbrido Inteligente
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Integração tripla com delimitação por volume de tokens: Google Gemini (créditos gratuitos), OpenAI e Llama Local no Ollama (100% livre)
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="fetchEngineStatus"
          :disabled="loadingStatus"
          class="px-3 py-1.5 text-xs font-mono text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{'animate-spin': loadingStatus}">↻</span> Atualizar Status
        </button>
      </div>
    </div>

    <!-- Active Pipeline Card -->
    <div class="bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 p-5 rounded-2xl border border-slate-800">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
          Orquestração de Custos & Roteamento Inteligente
        </span>
        <span class="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
          Guardrail de R$ 200/mês Ativo
        </span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">1</span>
          <div>
            <div class="font-bold text-slate-200">1º Prioridade: Google Gemini</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Usa a cota gratuita do Google AI Studio (15 RPM / 1M TPM a R$ 0,00).</div>
          </div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xs">2</span>
          <div>
            <div class="font-bold text-slate-200">2º Fallback: OpenAI</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Acionado caso a cota do Gemini expire; consome créditos de teste ou plano pay-as-you-go.</div>
          </div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">3</span>
          <div>
            <div class="font-bold text-slate-200">3º Garantia: Llama Local (Ollama)</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Fallback 100% offline rodando localmente no CPU/RAM do VPS. Custo zero perpétuo.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI Providers Triad -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <!-- 1. Google Gemini Card -->
      <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between">
            <div class="text-xs font-mono text-cyan-400 font-bold uppercase">Google AI Studio</div>
            <span
              class="text-[10px] font-mono px-2 py-0.5 rounded border"
              :class="providers.google_gemini.configured ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800' : 'bg-amber-950/80 text-amber-400 border-amber-800'"
            >
              {{ providers.google_gemini.configured ? 'Key Configurada' : 'Pendente .env' }}
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mt-2">Gemini Flash & Pro</h3>
          <p class="text-xs text-slate-400 mt-1">
            Modelo Ativo: <span class="font-mono text-cyan-300">{{ providers.google_gemini.default_model }}</span>
          </p>

          <div class="mt-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 text-xs space-y-1.5">
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Perfil:</span>
              <span class="text-emerald-400 font-medium">Free Tier Gratuito</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Janela de Contexto:</span>
              <span class="text-cyan-400 font-mono">1.000.000 tokens</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Limite Grátis:</span>
              <span>15 req/min (1M TPM)</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Custo VPS:</span>
              <span class="text-cyan-400 font-mono">0% RAM / 0% CPU</span>
            </div>
          </div>
        </div>

        <div class="mt-5 space-y-2">
          <button
            @click="testProviderConnection('gemini')"
            :disabled="testingProvider === 'gemini'"
            class="w-full py-2 px-3 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-700/50 rounded-xl text-xs font-mono font-bold transition flex items-center justify-center gap-2"
          >
            <span v-if="testingProvider === 'gemini'" class="animate-spin">↻</span>
            <span>Testar Conexão Google</span>
          </button>
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            class="block text-center text-[10px] text-slate-500 hover:text-cyan-400 font-mono transition"
          >
            → Obter Chave Gratuita no Google AI Studio
          </a>
        </div>
      </div>

      <!-- 2. OpenAI Card -->
      <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between">
            <div class="text-xs font-mono text-cyan-400 font-bold uppercase">OpenAI Platform</div>
            <span
              class="text-[10px] font-mono px-2 py-0.5 rounded border"
              :class="providers.openai.configured ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800' : 'bg-slate-800 text-slate-400 border-slate-700'"
            >
              {{ providers.openai.configured ? 'Key Configurada' : 'Não Configurada' }}
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mt-2">GPT-4o Mini & GPT-4o</h3>
          <p class="text-xs text-slate-400 mt-1">
            Modelo Ativo: <span class="font-mono text-cyan-300">{{ providers.openai.default_model }}</span>
          </p>

          <div class="mt-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 text-xs space-y-1.5">
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Perfil:</span>
              <span class="text-amber-400 font-medium">Créditos / Planos</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Janela de Contexto:</span>
              <span class="text-slate-300 font-mono">128.000 tokens</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Papel:</span>
              <span>Raciocínio analítico complexo</span>
            </div>
          </div>
        </div>

        <div class="mt-5 space-y-2">
          <button
            @click="testProviderConnection('openai')"
            :disabled="testingProvider === 'openai'"
            class="w-full py-2 px-3 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-700/50 rounded-xl text-xs font-mono font-bold transition flex items-center justify-center gap-2"
          >
            <span v-if="testingProvider === 'openai'" class="animate-spin">↻</span>
            <span>Testar Conexão OpenAI</span>
          </button>
          <a
            href="https://platform.openai.com/api-keys"
            target="_blank"
            class="block text-center text-[10px] text-slate-500 hover:text-amber-400 font-mono transition"
          >
            → Obter Chave no OpenAI Platform
          </a>
        </div>
      </div>

      <!-- 3. Local Llama Card -->
      <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between">
            <div class="text-xs font-mono text-cyan-400 font-bold uppercase">Ollama On-Premise</div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              100% Local & Offline
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mt-2">Llama & Qwen Local</h3>
          <p class="text-xs text-slate-400 mt-1">
            Modelo: <span class="font-mono text-cyan-300">{{ providers.ollama_llama.default_model }}</span>
          </p>

          <div class="mt-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 text-xs space-y-1.5">
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Custo de API:</span>
              <span class="text-emerald-400 font-medium">R$ 0,00 Perpétuo</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Janela de Contexto:</span>
              <span class="text-slate-300 font-mono">8.192 tokens (8GB VPS)</span>
            </div>
            <div class="flex justify-between text-slate-300">
              <span class="text-slate-500">Modelos no VPS:</span>
              <span class="font-mono text-cyan-400">{{ providers.ollama_llama.installed_models.length || 'Carregando...' }}</span>
            </div>
          </div>
        </div>

        <div class="mt-5 space-y-2">
          <button
            @click="testProviderConnection('ollama')"
            :disabled="testingProvider === 'ollama'"
            class="w-full py-2 px-3 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-700/50 rounded-xl text-xs font-mono font-bold transition flex items-center justify-center gap-2"
          >
            <span v-if="testingProvider === 'ollama'" class="animate-spin">↻</span>
            <span>Testar Ollama Local (Llama)</span>
          </button>
          <div class="text-center text-[10px] text-slate-500 font-mono">
            docker exec -it empire_ollama ollama pull llama3.2:3b
          </div>
        </div>
      </div>
    </div>

    <!-- Test Feedback Banner -->
    <div v-if="testResult" class="p-4 rounded-xl border transition text-xs font-mono" :class="testResult.success ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' : 'bg-rose-950/40 border-rose-800 text-rose-300'">
      <div class="flex items-center justify-between">
        <span class="font-bold uppercase tracking-wider">Resultado do Teste: {{ testResult.provider }}</span>
        <button @click="testResult = null" class="text-slate-400 hover:text-white">✕</button>
      </div>
      <p class="mt-1 text-slate-200">{{ testResult.message }}</p>
    </div>

    <!-- ============================================================================== -->
    <!-- SECTION: GOVERNANÇA DE TOKENS & DELIMITAÇÃO DE TAREFAS (LLAMA VS APIS) -->
    <!-- ============================================================================== -->
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <h3 class="text-base font-bold text-white uppercase font-mono">
              Governança de Tokens & Matriz de Delimitação
            </h3>
          </div>
          <p class="text-xs text-slate-400 mt-1">
            O sistema calcula a densidade de tokens antes de despachar cada tarefa e delega automaticamente entre o Llama local e as APIs para equilibrar custo e RAM.
          </p>
        </div>

        <!-- Token Economics Banner -->
        <div class="flex items-center gap-4 bg-slate-950/80 p-3 rounded-xl border border-slate-800">
          <div>
            <div class="text-[10px] font-mono text-slate-500 uppercase">Tokens Mês (Total)</div>
            <div class="text-sm font-bold text-cyan-400 font-mono">
              {{ (tokenGov.total_tokens_month || 0).toLocaleString() }}
            </div>
          </div>
          <div class="h-8 w-px bg-slate-800"></div>
          <div>
            <div class="text-[10px] font-mono text-slate-500 uppercase">Economia Gerada</div>
            <div class="text-sm font-bold text-emerald-400 font-mono">
              R$ {{ tokenGov.estimated_savings_brl || '0.00' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 3-Tier Task Delimitation Matrix Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Tier 1 -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
              TIER 1 • MICRO TAREFAS
            </span>
            <span class="text-xs font-mono text-slate-400">&lt; 800 tokens</span>
          </div>
          <h4 class="text-sm font-bold text-slate-100">Llama Local (Ollama)</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Classificações, títulos rápidos, status checks e JSONs curtos.
          </p>
          <div class="pt-2 text-[10px] font-mono text-cyan-400 border-t border-slate-800/60 flex items-center justify-between">
            <span>Poupa 100% de cotas</span>
            <span class="text-slate-500">0 ms latência de rede</span>
          </div>
        </div>

        <!-- Tier 2 -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              TIER 2 • MÉDIO PORTE
            </span>
            <span class="text-xs font-mono text-slate-400">800 a 3.500 tokens</span>
          </div>
          <h4 class="text-sm font-bold text-slate-100">Google Gemini Free / OpenAI</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Roteiros de YouTube Dark (RISADA.exe), manuscritos, postagens e e-mails.
          </p>
          <div class="pt-2 text-[10px] font-mono text-cyan-400 border-t border-slate-800/60 flex items-center justify-between">
            <span>Cota Grátis 15 RPM</span>
            <span class="text-slate-500">Alta fluência PT-BR</span>
          </div>
        </div>

        <!-- Tier 3 -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
              TIER 3 • CONTEXTO MASSIVO
            </span>
            <span class="text-xs font-mono text-slate-400">&gt; 3.500 tokens</span>
          </div>
          <h4 class="text-sm font-bold text-slate-100">Gemini 1.5 Flash (1M Tokens)</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Livros KDP completos, transcrições densas e processamento de documentos pesados.
          </p>
          <div class="pt-2 text-[10px] font-mono text-amber-400 border-t border-slate-800/60 flex items-center justify-between">
            <span>Protege RAM da VPS (8GB)</span>
            <span class="text-slate-500">Janela de 1M tokens</span>
          </div>
        </div>
      </div>

      <!-- Interactive Token Simulator & Calculator -->
      <div class="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h4 class="text-xs font-mono font-bold text-slate-200 uppercase">
              Simulador & Testador de Delimitação de Tokens em Tempo Real
            </h4>
            <p class="text-[11px] text-slate-400">
              Cole ou digite um texto para calcular a contagem de tokens em português (~3.6 caracteres/token) e verificar a rota recomendada.
            </p>
          </div>

          <!-- Presets -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="text-[10px] font-mono text-slate-500">Exemplos:</span>
            <button
              @click="loadPreset('micro')"
              class="px-2 py-1 text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
            >
              Micro (Título)
            </button>
            <button
              @click="loadPreset('script')"
              class="px-2 py-1 text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
            >
              Roteiro Dark
            </button>
            <button
              @click="loadPreset('kdp')"
              class="px-2 py-1 text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
            >
              Capítulo KDP
            </button>
          </div>
        </div>

        <div class="space-y-2">
          <textarea
            v-model="simText"
            @input="runTokenSimulation"
            rows="3"
            placeholder="Digite ou cole um texto aqui para verificar os tokens e a rota ideal..."
            class="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono transition"
          ></textarea>
        </div>

        <!-- Real-time Simulation Results Bar -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
          <div>
            <span class="text-slate-500 text-[10px] block">Caracteres:</span>
            <span class="text-slate-200 font-bold">{{ simResults.char_length || simText.length }}</span>
          </div>
          <div>
            <span class="text-slate-500 text-[10px] block">Tokens Estimados:</span>
            <span class="text-cyan-400 font-bold">~{{ simResults.estimated_tokens || Math.ceil(simText.length / 3.6) }}</span>
          </div>
          <div>
            <span class="text-slate-500 text-[10px] block">Tier Classificado:</span>
            <span class="font-bold" :class="getTierBadgeClass(simResults.tier)">
              {{ simResults.tier ? simResults.tier.toUpperCase() : 'MICRO' }}
            </span>
          </div>
          <div>
            <span class="text-slate-500 text-[10px] block">Motor Selecionado:</span>
            <span class="text-amber-400 font-bold">{{ getProviderLabel(simResults.recommended_provider) }}</span>
          </div>
        </div>

        <div v-if="simResults.delegation_reason" class="text-[11px] font-mono text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 flex items-start gap-2">
          <span class="text-cyan-400 font-bold">↳ Decisão:</span>
          <span>{{ simResults.delegation_reason }}</span>
        </div>
      </div>
    </div>

    <!-- Multimodal Media Engines (Piper TTS + FFmpeg + GPU Guardrails) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-cyan-400 font-bold uppercase">Narração Neural (TTS)</div>
        <div class="text-lg font-bold text-white mt-1">Piper TTS</div>
        <div class="text-xs text-slate-400 mt-2">
          Voz: <span class="text-amber-400 font-mono">pt_BR-faber-medium</span> (CPU ultrarrápido)
        </div>
        <div class="mt-3 text-[10px] font-mono text-emerald-400 bg-emerald-950/40 p-1.5 rounded">
          Status: Standalone Binário CPU
        </div>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-cyan-400 font-bold uppercase">Edição de Vídeo</div>
        <div class="text-lg font-bold text-white mt-1">FFmpeg</div>
        <div class="text-xs text-slate-400 mt-2">
          Render: Shorts (9:16) & Vídeos Longos (16:9)
        </div>
        <div class="mt-3 text-[10px] font-mono text-emerald-400 bg-emerald-950/40 p-1.5 rounded">
          Status: Pipeline Otimizado
        </div>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-cyan-400 font-bold uppercase">Abstração de GPU</div>
        <div class="text-lg font-bold text-white mt-1">Modo: CPU Only</div>
        <div class="text-xs text-slate-400 mt-2">
          GPU Remota: <span class="text-slate-500 font-mono">Desativada</span>
        </div>
        <div class="mt-3 text-[10px] font-mono text-slate-400 bg-slate-950/60 p-1.5 rounded">
          Custo Adicional: R$ 0,00
        </div>
      </div>
    </div>

    <!-- Interactive AI Completion Playground -->
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-bold text-slate-200 uppercase font-mono">
            Bancada de Validação de Prompt (Gateway Multi-Provedor)
          </h3>
          <p class="text-xs text-slate-400 mt-0.5">
            Teste prompts reais inspecionando tokens de entrada, tempo de resposta e motor selecionado
          </p>
        </div>

        <div class="flex items-center gap-2">
          <select
            v-model="selectedProvider"
            class="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-mono focus:outline-none focus:border-cyan-500"
          >
            <option value="hybrid">⚡ Híbrido Automático (Delimitação por Tokens)</option>
            <option value="gemini">✨ Google Gemini (Free Tier / Cloud)</option>
            <option value="openai">🤖 OpenAI (GPT-4o Mini / Plans)</option>
            <option value="ollama">🦙 Llama Local (Ollama - 100% Free)</option>
          </select>
        </div>
      </div>

      <div class="flex gap-3">
        <input
          v-model="playgroundPrompt"
          @keyup.enter="runPromptTest"
          placeholder="Digite um prompt de teste..."
          class="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
        />
        <button
          @click="runPromptTest"
          :disabled="runningPrompt || !playgroundPrompt.trim()"
          class="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl font-mono transition flex items-center gap-2"
        >
          <span v-if="runningPrompt" class="animate-spin">↻</span>
          <span>Executar</span>
        </button>
      </div>

      <div v-if="playgroundResponse" class="p-4 bg-slate-950/80 rounded-xl border border-slate-800 space-y-2 text-xs">
        <div class="flex flex-wrap items-center justify-between font-mono text-[11px] pb-2 border-b border-slate-800 gap-2">
          <span class="text-cyan-400 font-bold">Motor: {{ playgroundResponse.provider_name || playgroundResponse.provider }}</span>
          <div class="flex items-center gap-3 text-slate-400">
            <span>Modelo: <span class="text-amber-400">{{ playgroundResponse.model }}</span></span>
            <span>Latência: <span class="text-emerald-400">{{ playgroundResponse.latency_ms }}ms</span></span>
            <span v-if="playgroundResponse.token_metrics" class="text-cyan-300 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800">
              ~{{ playgroundResponse.token_metrics.total_tokens }} tokens ({{ playgroundResponse.token_metrics.tier }})
            </span>
            <span v-if="playgroundResponse.fallback_used" class="text-amber-400 bg-amber-950/50 px-2 py-0.5 rounded">Fallback Ativado</span>
          </div>
        </div>
        <div class="text-slate-200 whitespace-pre-wrap leading-relaxed">{{ playgroundResponse.response }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const loadingStatus = ref(false)
const testingProvider = ref(null)
const testResult = ref(null)

const providers = ref({
  google_gemini: {
    configured: false,
    default_model: 'gemini-1.5-flash',
  },
  openai: {
    configured: false,
    default_model: 'gpt-4o-mini',
  },
  ollama_llama: {
    connected: false,
    default_model: 'llama3.2:3b',
    installed_models: [],
  },
})

const tokenGov = ref({
  total_tokens_today: 0,
  total_tokens_month: 0,
  estimated_savings_brl: '0.00',
  thresholds: {
    micro_max: 800,
    long_context_min: 3500,
  },
})

const selectedProvider = ref('hybrid')
const playgroundPrompt = ref('Explique em uma frase o propósito de um canal dark bíblico de alta retenção.')
const runningPrompt = ref(false)
const playgroundResponse = ref(null)

// Simulator states
const simText = ref('Crie 5 títulos chamativos para um vídeo do RISADA.exe sobre a história de Davi e Golias.')
const simResults = ref({
  char_length: 0,
  estimated_tokens: 0,
  tier: 'micro',
  recommended_provider: 'ollama',
  delegation_reason: '',
})

const fetchEngineStatus = async () => {
  loadingStatus.value = true
  try {
    const res = await axios.get('/api/v1/ai-engine/status')
    if (res.data?.providers) {
      providers.value = res.data.providers
    }
    if (res.data?.token_governance) {
      tokenGov.value = res.data.token_governance
    }
  } catch (e) {
    console.error('Falha ao obter status do AI Engine', e)
  } finally {
    loadingStatus.value = false
  }
}

const testProviderConnection = async (providerName) => {
  testingProvider.value = providerName
  testResult.value = null
  try {
    const res = await axios.post('/api/v1/ai-engine/test-provider', { provider: providerName })
    testResult.value = {
      provider: providerName.toUpperCase(),
      success: res.data.success,
      message: res.data.message || (res.data.success ? 'Conectado com sucesso!' : 'Falha na conexão.'),
    }
    await fetchEngineStatus()
  } catch (err) {
    testResult.value = {
      provider: providerName.toUpperCase(),
      success: false,
      message: err.response?.data?.message || err.message || 'Erro inesperado na chamada.',
    }
  } finally {
    testingProvider.value = null
  }
}

const runTokenSimulation = async () => {
  if (!simText.value.trim()) return
  try {
    const res = await axios.post('/api/v1/ai-engine/estimate-tokens', {
      text: simText.value,
    })
    simResults.value = res.data
  } catch (err) {
    const est = Math.max(1, Math.ceil(simText.value.length / 3.6))
    simResults.value = {
      char_length: simText.value.length,
      estimated_tokens: est,
      tier: est <= 800 ? 'micro' : (est <= 3500 ? 'standard' : 'heavy_context'),
      recommended_provider: est <= 800 ? 'ollama' : 'gemini',
      delegation_reason: 'Cálculo local realizado via heurística PT-BR.',
    }
  }
}

const loadPreset = (type) => {
  if (type === 'micro') {
    simText.value = 'Classifique o sentimento deste comentário do YouTube em: POSITIVO, NEGATIVO ou DÚVIDA.'
  } else if (type === 'script') {
    simText.value = 'Escreva o roteiro narrativo completo de 3 minutos para o canal dark RISADA.exe. Personagem principal: Moisés diante do Mar Vermelho. Tom solene, teologicamente preciso, com ganchos de retenção a cada 30 segundos, marcações de tempo e orientações de entonação para o Piper TTS.'
  } else if (type === 'kdp') {
    simText.value = 'Gere o manuscrito do Capítulo 3 de um guia completo sobre produtividade bíblica e disciplina diária. O capítulo deve conter 4.000 palavras, citações bíblicas verificadas, exercícios práticos ao final de cada subseção, estrutura de tópicos aprofundada e formato pronto para diagramação KDP Amazon.'
  }
  runTokenSimulation()
}

const getTierBadgeClass = (tier) => {
  if (tier === 'micro') return 'text-emerald-400'
  if (tier === 'standard') return 'text-cyan-400'
  return 'text-amber-400'
}

const getProviderLabel = (prov) => {
  if (prov === 'ollama' || prov === 'llama') return 'Llama Local (Ollama)'
  if (prov === 'gemini') return 'Google Gemini 1.5 Flash'
  if (prov === 'openai') return 'OpenAI GPT-4o-mini'
  return prov || 'Híbrido'
}

const runPromptTest = async () => {
  if (!playgroundPrompt.value.trim() || runningPrompt.value) return
  runningPrompt.value = true
  playgroundResponse.value = null

  try {
    const res = await axios.post('/api/v1/ai-engine/complete', {
      prompt: playgroundPrompt.value,
      provider: selectedProvider.value,
    })
    playgroundResponse.value = res.data
  } catch (err) {
    playgroundResponse.value = {
      success: false,
      provider_name: 'Falha',
      model: '-',
      latency_ms: 0,
      response: err.response?.data?.error || err.message || 'Erro ao processar prompt.',
    }
  } finally {
    runningPrompt.value = false
  }
}

onMounted(() => {
  fetchEngineStatus()
  runTokenSimulation()
})
</script>
