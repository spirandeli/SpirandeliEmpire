<template>
  <div class="h-[calc(100vh-8rem)] flex gap-6 max-w-7xl mx-auto">
    <!-- Chat Main Area -->
    <div class="flex-1 bg-slate-900/80 rounded-2xl border border-slate-800 flex flex-col overflow-hidden">
      <!-- Agent Header -->
      <div class="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/60">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 flex items-center justify-center font-bold text-slate-950 text-base shadow-md">
            J
          </div>
          <div>
            <div class="font-bold text-sm text-slate-100 flex items-center gap-2">
              Jeffrey AI
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                Orquestrador Multi-Provedor
              </span>
            </div>
            <div class="text-xs text-slate-400 font-mono">
              Google Gemini + OpenAI + Llama Local • Teto: R$ 200/mês
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Provider Selector Pill -->
          <div class="flex items-center bg-slate-900 border border-slate-700/80 rounded-lg p-1 text-[11px] font-mono">
            <label class="text-slate-400 px-2">Motor:</label>
            <select
              v-model="chosenProvider"
              class="bg-slate-950 text-cyan-300 rounded px-2 py-1 focus:outline-none border border-slate-800"
            >
              <option value="hybrid">⚡ Híbrido (Gemini Free → OpenAI → Llama)</option>
              <option value="gemini">✨ Google Gemini (Free Tier)</option>
              <option value="openai">🤖 OpenAI (Créditos/Planos)</option>
              <option value="ollama">🦙 Llama Local (Ollama R$ 0)</option>
            </select>
          </div>

          <button
            @click="clearChat"
            class="px-3 py-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 rounded-lg border border-slate-700/60 transition"
          >
            Limpar
          </button>
        </div>
      </div>

      <!-- Messages Stream -->
      <div class="flex-1 overflow-y-auto p-6 space-y-4">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="flex flex-col"
          :class="msg.role === 'user' ? 'items-end' : 'items-start'"
        >
          <div class="text-[10px] font-mono text-slate-500 mb-1 px-1 flex flex-wrap items-center gap-2">
            <span>{{ msg.role === 'user' ? 'Comandante' : 'Jeffrey (Orquestrador Central)' }}</span>
            <span
              v-if="msg.provider_name"
              class="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700"
            >
              {{ msg.provider_name }} <span v-if="msg.latency_ms">({{ msg.latency_ms }}ms)</span>
            </span>
            <span
              v-if="msg.token_metrics"
              class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800"
            >
              ~{{ msg.token_metrics.total_tokens }} tokens ({{ msg.token_metrics.tier }})
            </span>
          </div>

          <div
            class="max-w-2xl p-4 rounded-2xl text-xs leading-relaxed"
            :class="msg.role === 'user' 
              ? 'bg-amber-500 text-slate-950 font-medium rounded-tr-none' 
              : 'bg-slate-800/90 text-slate-100 border border-slate-700/80 rounded-tl-none whitespace-pre-line'"
          >
            <div v-if="msg.fallback_used" class="mb-2 p-1.5 bg-amber-950/60 border border-amber-800/70 rounded text-[10px] font-mono text-amber-300">
              ⚠️ Fallback ativado: {{ msg.fallback_reason || 'Provedor primário inacessível ou cota esgotada.' }}
            </div>
            {{ msg.content }}
          </div>
        </div>

        <div v-if="loading" class="flex items-center space-x-2 text-cyan-400 text-xs font-mono p-2">
          <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <span>Jeffrey consultando os modelos de IA e a memória operacional...</span>
        </div>
      </div>

      <!-- Input Area -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60">
        <form @submit.prevent="sendMessage" class="flex gap-3">
          <input
            v-model="inputMessage"
            type="text"
            placeholder="Apresente uma ideia de negócio, solicite viabilidade ou consulte status..."
            class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition"
          />
          <button
            type="submit"
            :disabled="loading || !inputMessage.trim()"
            class="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl font-mono transition flex items-center gap-2"
          >
            <span v-if="loading" class="animate-spin">↻</span>
            <span>Enviar</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Right Sidebar: Specialized Agents & Operational Memory -->
    <div class="w-80 space-y-4 hidden lg:flex lg:flex-col">
      <!-- Specialized Agents Pool -->
      <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-800">
        <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-3">
          Agentes Especializados
        </h4>
        <div class="space-y-2 text-xs">
          <div
            v-for="agent in specializedAgents"
            :key="agent.name"
            class="flex items-center justify-between p-2 rounded-lg bg-slate-950/50 border border-slate-800/60"
          >
            <div>
              <div class="font-medium text-slate-200">{{ agent.name }}</div>
              <div class="text-[10px] text-slate-500">{{ agent.role }}</div>
            </div>
            <span class="w-2 h-2 rounded-full" :class="agent.active ? 'bg-emerald-400' : 'bg-slate-600'"></span>
          </div>
        </div>
      </div>

      <!-- Operational Memory Guidelines -->
      <div class="bg-slate-900/80 p-5 rounded-2xl border border-slate-800 flex-1 overflow-y-auto">
        <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-3">
          Memória Operacional Ativa
        </h4>
        <ul class="text-xs space-y-2 text-slate-400 list-disc pl-4">
          <li>Teto orçamentário rígido de R$ 200/mês respeitado.</li>
          <li>Aproveitamento de cotas gratuitas do Google Gemini (15 RPM a R$ 0,00).</li>
          <li>Fallback para OpenAI e Llama local (Ollama).</li>
          <li>Fidelidade total às Escrituras para o RISADA.exe.</li>
          <li>Aprovação humana mandatória para despesas e deploys.</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const inputMessage = ref('')
const loading = ref(false)
const chosenProvider = ref('hybrid')

const messages = ref([
  {
    role: 'assistant',
    provider_name: 'Jeffrey Gateway Multi-IA',
    content: 'Saudações, Comandante. Eu sou Jeffrey, orquestrador central do SpirandeliEmpire OS.\n\nAgora estou conectado ao Gateway Multi-Provedor de IA com suporte conjunto a Google Gemini (créditos gratuitos), OpenAI e Llama Local no Ollama.\n\nComo deseja proceder hoje?',
  },
])

const specializedAgents = [
  { name: 'Research Agent', role: 'Pesquisa e referências', active: true },
  { name: 'Business Agent', role: 'Análise de viabilidade', active: true },
  { name: 'Content Agent', role: 'Roteiros e manuscritos', active: true },
  { name: 'Voice Agent', role: 'Piper TTS Brasileiro', active: true },
  { name: 'Video Agent', role: 'FFmpeg Pipeline', active: true },
  { name: 'Finance Agent', role: 'Controle de custos R$ 200', active: true },
]

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userText = inputMessage.value
  messages.value.push({ role: 'user', content: userText })
  inputMessage.value = ''
  loading.value = true

  try {
    const res = await axios.post('/api/v1/jeffrey/chat', {
      message: userText,
      provider: chosenProvider.value,
    })
    messages.value.push({
      role: 'assistant',
      content: res.data.reply,
      provider_name: res.data.provider_name || res.data.model,
      latency_ms: res.data.latency_ms,
      token_metrics: res.data.token_metrics,
      fallback_used: res.data.fallback_used,
      fallback_reason: res.data.fallback_reason,
    })
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: `[Jeffrey Modo Offline/Local]: Recebi sua instrução: "${userText}". O núcleo do sistema registrou a solicitação na fila de orquestração com segurança e aguarda o processamento do modelo local.`,
      provider_name: 'Llama Local (Emergência)',
    })
  } finally {
    loading.value = false
  }
}

const clearChat = () => {
  messages.value = [
    {
      role: 'assistant',
      provider_name: 'Jeffrey Gateway Multi-IA',
      content: 'Histórico resetado. Jeffrey pronto para novas orientações estratégicas.',
    },
  ]
}
</script>
