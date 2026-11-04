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

    <!-- Active Pipeline Card + API Key Quick Configuration -->
    <div class="bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 p-5 rounded-2xl border border-slate-800 space-y-4">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <span class="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
          Divisão Cooperativa de Agentes: Llama (Leitura & Análise) + Gemini / Chat (Execução de Tarefas)
        </span>
        <div class="flex items-center gap-2">
          <span
            class="text-[11px] font-mono px-2.5 py-0.5 rounded border font-bold"
            :class="(providers.google_gemini.configured || providers.openai.configured)
              ? 'text-emerald-300 bg-emerald-950/80 border-emerald-700'
              : 'text-amber-300 bg-amber-950/80 border-amber-700'"
          >
            {{ (providers.google_gemini.configured || providers.openai.configured)
              ? '⚡ MODO COOPERATIVO ATIVO (Llama Analisa → Gemini/Chat Executa)'
              : '🦙 MODO 100% LOCAL (Insira a API Key abaixo para ativar divisão)' }}
          </span>
          <button
            v-if="userAccess.is_owner"
            @click="showAvailabilityConfig = !showAvailabilityConfig"
            class="px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-mono font-bold text-xs transition"
          >
            🛡️ {{ showAvailabilityConfig ? 'Fechar Controle de IAs' : 'IAs Disponíveis & Acesso Gemini' }}
          </button>
          <button
            v-if="userAccess.is_owner"
            @click="showKeyConfig = !showKeyConfig"
            class="px-3 py-1 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs transition"
          >
            🔑 {{ showKeyConfig ? 'Fechar Chaves' : 'Configurar API Keys' }}
          </button>
        </div>
      </div>

      <!-- Current Login Access Status Pill -->
      <div class="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono">
        <div class="flex items-center gap-2">
          <span class="text-sm">{{ userAccess.can_use_gemini ? '👑' : '🔒' }}</span>
          <span class="text-slate-300">
            Login Ativo:
            <strong class="text-white">{{ userAccess.user_name || 'Comandante' }}</strong>
            <span v-if="userAccess.user_email" class="text-slate-400">({{ userAccess.user_email }})</span>
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span
            class="px-2.5 py-0.5 rounded border text-[10px] font-bold"
            :class="userAccess.can_use_gemini
              ? 'bg-emerald-950/90 text-emerald-300 border-emerald-700'
              : 'bg-rose-950/90 text-rose-300 border-rose-700'"
          >
            {{ userAccess.can_use_gemini
              ? '✓ ACESSO AO GEMINI 3.8 FLASH LIBERADO NESTE LOGIN'
              : '🔒 GEMINI RESTRITO AO COMANDANTE (USANDO LLAMA LOCAL)' }}
          </span>
          <span class="px-2 py-0.5 rounded bg-slate-900 text-cyan-300 border border-slate-700 text-[10px]">
            Política: {{ availabilityForm.gemini_access_policy === 'owner_only' ? 'Exclusivo Meu Login' : (availabilityForm.gemini_access_policy === 'selected_users' ? 'Logins Selecionados' : 'Todos os Perfis') }}
          </span>
        </div>
      </div>

      <!-- ====================================================================== -->
      <!-- PAINEL DE SELEÇÃO DE TIPOS DE IA DISPONIBILIZADOS & RESTRIÇÃO GEMINI -->
      <!-- ====================================================================== -->
      <form
        v-if="showAvailabilityConfig && userAccess.is_owner"
        @submit.prevent="saveAvailabilityConfig"
        class="p-5 rounded-xl bg-slate-950/95 border border-amber-700/70 space-y-5 text-xs font-mono"
      >
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h4 class="text-sm font-bold text-amber-400 uppercase flex items-center gap-2">
              <span>🛡️</span>
              <span>Configuração de Tipos de IA Disponibilizados & Restrição de Login (Gemini)</span>
            </h4>
            <p class="text-[11px] text-slate-400 mt-0.5">
              Selecione quais motores e modos de IA ficam disponíveis no sistema e mantenha o Google Gemini 3.8 Flash restrito exclusivamente ao seu login.
            </p>
          </div>
          <span class="text-[10px] px-2.5 py-1 rounded bg-amber-950/80 text-amber-300 border border-amber-700 shrink-0">
            👑 Exclusivo do Login Comandante
          </span>
        </div>

        <!-- 1. Seleção dos Tipos de IA Disponibilizados -->
        <div class="space-y-2.5">
          <div class="text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
            1. Tipos de IA que você deseja disponibilizar no Sistema:
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <!-- Hybrid Cooperative -->
            <label
              class="p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between gap-2"
              :class="availabilityForm.enabled_providers.hybrid
                ? 'bg-cyan-950/40 border-cyan-600 text-slate-100'
                : 'bg-slate-900/50 border-slate-800 text-slate-500'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-xs text-cyan-300">⚡ IA Híbrida Cooperativa</span>
                <input type="checkbox" v-model="availabilityForm.enabled_providers.hybrid" class="accent-cyan-400 w-4 h-4" />
              </div>
              <div class="text-[10px] leading-relaxed text-slate-400">
                Llama Local lê e analisa os dados brutos; Gemini 3.8 Flash ou ChatGPT executa a tarefa final.
              </div>
            </label>

            <!-- Google Gemini 3.8 Flash -->
            <label
              class="p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between gap-2"
              :class="availabilityForm.enabled_providers.gemini
                ? 'bg-emerald-950/40 border-emerald-600 text-slate-100'
                : 'bg-slate-900/50 border-slate-800 text-slate-500'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-xs text-emerald-300">✨ Google Gemini 3.8 Flash</span>
                <input type="checkbox" v-model="availabilityForm.enabled_providers.gemini" class="accent-emerald-400 w-4 h-4" />
              </div>
              <div class="text-[10px] leading-relaxed text-slate-400">
                Executor principal cloud (1M tokens, multimodal, voz e imagens). Respeita a trava de login abaixo.
              </div>
            </label>

            <!-- OpenAI ChatGPT -->
            <label
              class="p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between gap-2"
              :class="availabilityForm.enabled_providers.openai
                ? 'bg-amber-950/40 border-amber-600 text-slate-100'
                : 'bg-slate-900/50 border-slate-800 text-slate-500'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-xs text-amber-300">🤖 OpenAI GPT-4o-mini</span>
                <input type="checkbox" v-model="availabilityForm.enabled_providers.openai" class="accent-amber-400 w-4 h-4" />
              </div>
              <div class="text-[10px] leading-relaxed text-slate-400">
                Executor cloud alternativo para copywriting avançado e contingência automática.
              </div>
            </label>

            <!-- Ollama Llama Local -->
            <label
              class="p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between gap-2"
              :class="availabilityForm.enabled_providers.ollama
                ? 'bg-purple-950/40 border-purple-600 text-slate-100'
                : 'bg-slate-900/50 border-slate-800 text-slate-500'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-xs text-purple-300">🦙 Llama / Qwen Local</span>
                <input type="checkbox" v-model="availabilityForm.enabled_providers.ollama" class="accent-purple-400 w-4 h-4" />
              </div>
              <div class="text-[10px] leading-relaxed text-slate-400">
                IA 100% local no container Ollama (qwen2.5:3b) a custo R$ 0,00 para leitura, triagem e fallback.
              </div>
            </label>
          </div>
        </div>

        <!-- 2. Recursos e Módulos Inteligentes Disponibilizados -->
        <div class="space-y-2.5">
          <div class="text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
            2. Recursos e Módulos de IA Ativos no Jeffrey:
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <label class="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-2.5 cursor-pointer">
              <input type="checkbox" v-model="availabilityForm.enabled_capabilities.cooperative_pipeline" class="accent-cyan-400 mt-0.5 w-4 h-4" />
              <div>
                <div class="font-bold text-slate-200 text-xs">⛓️ Pipeline Encadeado (2 Tasks)</div>
                <div class="text-[10px] text-slate-400 mt-0.5">Cria automaticamente Task #1 (Pesquisa) e Task #2 (Hooks de 3s aguardando a 1ª).</div>
              </div>
            </label>
            <label class="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-2.5 cursor-pointer">
              <input type="checkbox" v-model="availabilityForm.enabled_capabilities.live_web_search" class="accent-cyan-400 mt-0.5 w-4 h-4" />
              <div>
                <div class="font-bold text-slate-200 text-xs">🌐 Pesquisa Web Ao Vivo Anti-Alucinação</div>
                <div class="text-[10px] text-slate-400 mt-0.5">Consulta preços reais e produtos virais na web antes de responder, bloqueando links inventados.</div>
              </div>
            </label>
            <label class="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-2.5 cursor-pointer">
              <input type="checkbox" v-model="availabilityForm.enabled_capabilities.voice_and_attachments" class="accent-cyan-400 mt-0.5 w-4 h-4" />
              <div>
                <div class="font-bold text-slate-200 text-xs">🎙️ Multimodalidade (Voz, Áudio & Anexos)</div>
                <div class="text-[10px] text-slate-400 mt-0.5">Permite envio de mensagens de voz gravadas, prints, PDFs e planilhas no chat do Jeffrey.</div>
              </div>
            </label>
          </div>
        </div>

        <!-- 3. Restrição de Acesso ao Gemini por Login -->
        <div class="p-4 rounded-xl bg-slate-900/90 border border-amber-800/60 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <div class="text-xs font-bold text-amber-300 uppercase flex items-center gap-1.5">
                <span>🔒</span>
                <span>3. Restrição de Acesso ao Google Gemini por Login</span>
              </div>
              <p class="text-[10px] text-slate-400 mt-0.5">
                Garante que apenas o seu login consuma a chave do Gemini 3.8 Flash. Outros logins serão roteados automaticamente para a IA padrão definida ao lado.
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="block text-[10px] text-amber-400 mb-1 font-bold">Quem pode usar o Google Gemini?</label>
              <select
                v-model="availabilityForm.gemini_access_policy"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none"
              >
                <option value="owner_only">👑 Exclusivo ao Meu Login Principal (Recomendado)</option>
                <option value="selected_users">👥 Meu Login + Perfis Selecionados Abaixo</option>
                <option value="all_users">🌐 Liberado para Todos os Perfis Logados</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] text-cyan-400 mb-1 font-bold">E-mail do Seu Login Proprietário (Dono do Gemini)</label>
              <input
                v-model="availabilityForm.gemini_owner_email"
                type="email"
                placeholder="Ex: comandante@spirandeliempire.tech"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-cyan-500 outline-none"
              />
            </div>

            <div>
              <label class="block text-[10px] text-purple-400 mb-1 font-bold">IA Padrão para Outros Logins (Sem Acesso ao Gemini)</label>
              <select
                v-model="availabilityForm.default_provider_for_others"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-purple-500 outline-none"
              >
                <option value="ollama">🦙 Llama Local via Ollama (Custo R$ 0,00)</option>
                <option value="openai">🤖 OpenAI GPT-4o-mini (se ativa)</option>
              </select>
            </div>
          </div>

          <!-- Lista de Perfis Cadastrados e Status de Acesso ao Gemini -->
          <div v-if="registeredUsers.length > 0" class="space-y-2 pt-2 border-t border-slate-800">
            <div class="text-[10px] text-slate-400 font-bold uppercase">
              Perfis Cadastrados no Sistema & Permissão do Gemini:
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              <div
                v-for="u in registeredUsers"
                :key="u.id"
                class="p-2.5 rounded-lg border flex items-center justify-between gap-2"
                :class="(u.is_owner || availabilityForm.gemini_access_policy === 'all_users' || (availabilityForm.gemini_access_policy === 'selected_users' && availabilityForm.gemini_allowed_user_ids.includes(u.id)))
                  ? 'bg-emerald-950/30 border-emerald-800/70 text-slate-200'
                  : 'bg-slate-950/80 border-slate-800 text-slate-400'"
              >
                <div class="min-w-0">
                  <div class="font-bold text-xs truncate flex items-center gap-1.5">
                    <span>{{ u.is_owner ? '👑' : '👤' }}</span>
                    <span>{{ u.name }}</span>
                  </div>
                  <div class="text-[10px] text-slate-400 truncate">{{ u.email }}</div>
                </div>

                <div class="shrink-0 flex items-center gap-2">
                  <span
                    v-if="u.is_owner"
                    class="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700 text-[9px] font-bold"
                  >
                    SEU LOGIN (DONO)
                  </span>
                  <label
                    v-else-if="availabilityForm.gemini_access_policy === 'selected_users'"
                    class="flex items-center gap-1 text-[10px] cursor-pointer text-cyan-300"
                  >
                    <input
                      type="checkbox"
                      :value="u.id"
                      v-model="availabilityForm.gemini_allowed_user_ids"
                      class="accent-cyan-400"
                    />
                    <span>Permitir Gemini</span>
                  </label>
                  <span
                    v-else
                    class="px-2 py-0.5 rounded text-[9px] font-bold border"
                    :class="availabilityForm.gemini_access_policy === 'all_users'
                      ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                      : 'bg-rose-950/80 text-rose-300 border-rose-800'"
                  >
                    {{ availabilityForm.gemini_access_policy === 'all_users' ? 'Liberado' : 'Bloqueado (Usa Llama)' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button
            type="submit"
            :disabled="savingAvailability"
            class="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition"
          >
            {{ savingAvailability ? 'Salvando Permissões...' : '💾 Salvar IAs Disponíveis & Restrição do Meu Login' }}
          </button>
        </div>
      </form>

      <!-- Collapsible API Key Configurator -->
      <form
        v-if="showKeyConfig"
        @submit.prevent="saveApiKeys"
        class="p-4 rounded-xl bg-slate-950/90 border border-cyan-800/60 space-y-3 text-xs font-mono"
      >
        <div class="text-slate-300">
          Insira sua <strong>GEMINI_API_KEY</strong> (Google AI Studio) e/ou <strong>OPENAI_API_KEY</strong>. Assim que salva, o sistema automaticamente deixa o <strong>Llama Local</strong> responsável por ler/analisar os dados e o <strong>Gemini / ChatGPT</strong> responsável por executar as tarefas:
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] text-cyan-400 mb-1">Google Gemini API Key (GEMINI_API_KEY)</label>
            <input
              v-model="keyForm.gemini_api_key"
              type="password"
              placeholder="AIzaSy..."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-cyan-500 outline-none"
            />
          </div>
          <div>
            <label class="block text-[10px] text-amber-400 mb-1">OpenAI ChatGPT API Key (OPENAI_API_KEY - Opcional)</label>
            <input
              v-model="keyForm.openai_api_key"
              type="password"
              placeholder="sk-proj-..."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none"
            />
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button
            type="submit"
            :disabled="savingKeys"
            class="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
          >
            {{ savingKeys ? 'Salvando e Ativando...' : '💾 Salvar Chaves & Ativar Divisão Cooperativa' }}
          </button>
        </div>
      </form>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">1</span>
          <div>
            <div class="font-bold text-slate-200">Etapa 1: Llama Local (Leitura & Análise)</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Lê arquivos, filtra pesquisas da web, analisa métricas dos negócios e prepara o resumo técnico a custo R$ 0,00.</div>
          </div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold text-xs">2</span>
          <div>
            <div class="font-bold text-slate-200">Etapa 2: Google Gemini (Executor Principal)</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Recebe a análise pronta do Llama e executa a tarefa final (roteiros, TikTok Shop, chamadas de ferramentas e entregáveis).</div>
          </div>
        </div>
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-xs">3</span>
          <div>
            <div class="font-bold text-slate-200">Etapa 3: ChatGPT / OpenAI (Executor Alternativo)</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Executa tarefas complexas ou assume automaticamente caso a cota gratuita do Gemini seja atingida.</div>
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

          <h3 class="text-lg font-bold text-white mt-2">Gemini 3.8 Flash</h3>
          <p class="text-xs text-slate-400 mt-1">
            Modelo Ativo: <span class="font-mono text-cyan-300">{{ providers.google_gemini.default_model || 'gemini-3.8-flash' }}</span>
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
          <h4 class="text-sm font-bold text-slate-100">Gemini 3.8 Flash (1M Tokens)</h4>
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
            <option value="hybrid">⚡ Automático (Llama Lê/Analisa • Gemini/Chat Executa)</option>
            <option value="cooperative">🤝 Pipeline 2 Etapas (Llama Analisa → Gemini/Chat Executa)</option>
            <option value="gemini">✨ Google Gemini (Executor Cloud)</option>
            <option value="openai">🤖 OpenAI ChatGPT (Executor Cloud)</option>
            <option value="ollama">🦙 Llama Local (Leitura & Análise Offline)</option>
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
const showKeyConfig = ref(false)
const showAvailabilityConfig = ref(true)
const savingKeys = ref(false)
const savingAvailability = ref(false)
const keyForm = ref({
  gemini_api_key: '',
  openai_api_key: '',
})

const userAccess = ref({
  user_id: null,
  user_name: 'Comandante',
  user_email: '',
  is_owner: true,
  can_use_gemini: true,
  available_options: [],
})

const registeredUsers = ref([])

const availabilityForm = ref({
  enabled_providers: {
    ollama: true,
    gemini: true,
    openai: true,
    hybrid: true,
  },
  enabled_capabilities: {
    cooperative_pipeline: true,
    voice_and_attachments: true,
    live_web_search: true,
  },
  gemini_access_policy: 'owner_only',
  gemini_owner_email: '',
  gemini_allowed_user_ids: [],
  default_provider_for_others: 'ollama',
})

const saveAvailabilityConfig = async () => {
  savingAvailability.value = true
  try {
    const res = await axios.post('/api/v1/ai-engine/configure-availability', availabilityForm.value)
    testResult.value = {
      provider: 'CATÁLOGO DE IAs & RESTRIÇÃO DE LOGIN GEMINI',
      success: true,
      message: res.data?.message || 'Configuração de IAs disponibilizadas e restrição de login salva com sucesso!',
    }
    await fetchEngineStatus()
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao salvar configuração de IAs disponíveis.')
  } finally {
    savingAvailability.value = false
  }
}

const saveApiKeys = async () => {
  savingKeys.value = true
  try {
    const res = await axios.post('/api/v1/ai-engine/configure-keys', keyForm.value)
    if (res.data?.status?.providers) {
      providers.value = res.data.status.providers
    }
    testResult.value = {
      provider: 'COOPERATIVO (LLAMA + GEMINI/CHAT)',
      success: true,
      message: res.data?.message || 'Chaves salvas com sucesso!',
    }
    keyForm.value.gemini_api_key = ''
    keyForm.value.openai_api_key = ''
    showKeyConfig.value = false
    await fetchEngineStatus()
    await runTokenSimulation()
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao salvar chaves de API.')
  } finally {
    savingKeys.value = false
  }
}

const providers = ref({
  google_gemini: {
    configured: false,
    default_model: 'gemini-3.8-flash',
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
    if (res.data?.user_access) {
      userAccess.value = res.data.user_access
      if (!userAccess.value.can_use_gemini && selectedProvider.value === 'gemini') {
        selectedProvider.value = 'ollama'
      }
    }
    if (res.data?.registered_users) {
      registeredUsers.value = res.data.registered_users
    }
    if (res.data?.availability_config) {
      const cfg = res.data.availability_config
      availabilityForm.value = {
        enabled_providers: {
          ollama: cfg.enabled_providers?.ollama ?? true,
          gemini: cfg.enabled_providers?.gemini ?? true,
          openai: cfg.enabled_providers?.openai ?? true,
          hybrid: cfg.enabled_providers?.hybrid ?? true,
        },
        enabled_capabilities: {
          cooperative_pipeline: cfg.enabled_capabilities?.cooperative_pipeline ?? true,
          voice_and_attachments: cfg.enabled_capabilities?.voice_and_attachments ?? true,
          live_web_search: cfg.enabled_capabilities?.live_web_search ?? true,
        },
        gemini_access_policy: cfg.gemini_access_policy || 'owner_only',
        gemini_owner_email: cfg.gemini_owner_email || userAccess.value.user_email || '',
        gemini_allowed_user_ids: Array.isArray(cfg.gemini_allowed_user_ids) ? cfg.gemini_allowed_user_ids : [],
        default_provider_for_others: cfg.default_provider_for_others || 'ollama',
      }
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
  if (prov === 'gemini') return 'Google Gemini 3.8 Flash'
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
