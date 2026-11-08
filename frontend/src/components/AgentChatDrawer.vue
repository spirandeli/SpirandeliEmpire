<script setup>
import { ref, watch, nextTick } from 'vue'
import { marked } from 'marked'
import { useAgentChat } from '@/composables/useAgentChat'

marked.setOptions({
  gfm: true,
  breaks: true,
})

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  businessId: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['close'])

const {
  conversation,
  messages,
  loading,
  error,
  loadOrCreateConversation,
  sendMessage,
} = useAgentChat()

const inputText = ref('')
const messagesContainer = ref(null)
const expandedTools = ref({})

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      await loadOrCreateConversation(props.businessId)
      scrollToBottom()
    }
  }
)

function toggleToolExpand(msgId) {
  expandedTools.value[msgId] = !expandedTools.value[msgId]
}

function getToolBadge(toolName) {
  if (toolName?.includes('vps') || toolName?.includes('docker')) {
    return { label: 'Infra / VPS', color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' }
  }
  if (toolName?.includes('venture')) {
    return { label: 'Venture / Negócio', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' }
  }
  if (toolName?.includes('task') || toolName?.includes('kanban')) {
    return { label: 'Kanban Workflow', color: 'bg-amber-500/10 text-amber-400 border-amber-500/30' }
  }
  if (toolName?.includes('approval')) {
    return { label: 'Supervisão Humana', color: 'bg-purple-500/10 text-purple-400 border-purple-500/30' }
  }
  if (toolName?.includes('knowledge')) {
    return { label: 'RAG Base', color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' }
  }
  return { label: 'Operação', color: 'bg-slate-700/50 text-slate-300 border-slate-600' }
}

async function handleSend() {
  if (!inputText.value.trim() || loading.value) return

  const text = inputText.value
  inputText.value = ''
  await sendMessage(text)
  scrollToBottom()
}

function handleQuickPrompt(promptText) {
  inputText.value = promptText
  handleSend()
}

function renderMarkdown(content) {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (err) {
    return content
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-hidden flex justify-end">
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
      @click="emit('close')"
    ></div>

    <!-- Drawer Panel -->
    <div class="relative w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full z-10 animate-in slide-in-from-right duration-200">
      <!-- Drawer Header -->
      <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 via-indigo-600 to-cyan-500 flex items-center justify-center text-white font-bold text-sm shadow-md shadow-indigo-500/20">
            ⚡
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <h2 class="text-sm font-bold text-white">Jeffrey · COO Executivo</h2>
              <span class="px-2 py-0.5 text-[10px] font-mono font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Gemini 3.8 Flash
              </span>
            </div>
            <p class="text-[11px] text-slate-400 font-mono">
              {{ conversation?.business ? `Venture: ${conversation.business.name}` : 'Modo Incubadora & Infraestrutura Geral' }}
            </p>
          </div>
        </div>

        <button
          type="button"
          aria-label="Fechar Drawer COO"
          @click="emit('close')"
          class="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- Quick Action Pills -->
      <div class="p-2.5 bg-slate-950/40 border-b border-slate-800/80 flex items-center space-x-2 overflow-x-auto text-[11px] no-scrollbar">
        <button
          @click="handleQuickPrompt('Jeffrey, faça uma auditoria rápida na nossa VPS e liste os contêineres Docker ativos.')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/90 hover:bg-slate-700 text-cyan-300 border border-cyan-500/30 transition flex items-center space-x-1"
        >
          <span>🖥️ Auditar VPS & Docker</span>
        </button>
        <button
          @click="handleQuickPrompt('Estruture uma nova venture no nicho de utilidades virais para o TikTok Shop.')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/90 hover:bg-slate-700 text-emerald-300 border border-emerald-500/30 transition flex items-center space-x-1"
        >
          <span>💡 Criar Venture</span>
        </button>
        <button
          @click="handleQuickPrompt('Consulte a base de conhecimento e me explique as métricas de mineração e roteiro do TikTok Shop.')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/90 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 transition flex items-center space-x-1"
        >
          <span>📚 RAG Base de Negócios</span>
        </button>
      </div>

      <!-- Messages Stream -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        <div v-if="messages.length === 0" class="text-center py-12 text-slate-500">
          <div class="w-12 h-12 rounded-2xl bg-slate-800/60 flex items-center justify-center mx-auto mb-3 text-slate-400 text-2xl shadow-inner border border-slate-700/50">
            🤖
          </div>
          <p class="font-bold text-slate-200">Jeffrey operacional e pronto para despachar.</p>
          <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto leading-relaxed">
            Posso auditar telemetria da VPS, inspecionar contêineres Docker, conceber ventures, movimentar tarefas no Kanban e consultar a base de conhecimento.
          </p>
        </div>

        <template v-for="msg in messages" :key="msg.id">
          <!-- Mensagem do Usuário -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[85%] bg-emerald-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow text-sm">
              <p class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Mensagem do Modelo (Jeffrey) -->
          <div v-else-if="msg.role === 'model'" class="flex justify-start">
            <div class="max-w-[92%] bg-slate-800/90 text-slate-200 border border-slate-700/60 px-4 py-3 rounded-2xl rounded-tl-sm shadow space-y-2">
              <div class="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span class="font-semibold text-slate-300">Jeffrey (COO)</span>
                <span v-if="msg.latency_ms">· {{ msg.latency_ms }}ms</span>
              </div>
              <div
                v-if="msg.content"
                class="chat-markdown text-sm text-slate-100 font-sans"
                v-html="renderMarkdown(msg.content)"
              ></div>
            </div>
          </div>

          <!-- Mensagem de Tool (Execução de Ferramenta ReAct) -->
          <div v-else-if="msg.role === 'tool'" class="flex justify-start w-full">
            <div class="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-xs font-mono transition">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold border" :class="getToolBadge(msg.tool_name).color">
                    {{ getToolBadge(msg.tool_name).label }}
                  </span>
                  <span class="text-slate-300 font-bold">{{ msg.tool_name }}</span>
                </div>
                <div class="flex items-center space-x-2">
                  <span v-if="msg.latency_ms" class="text-slate-500 text-[10px]">{{ msg.latency_ms }}ms</span>
                  <span
                    class="px-1.5 py-0.5 rounded text-[10px] font-bold"
                    :class="msg.tool_failed ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'"
                  >
                    {{ msg.tool_failed ? 'Falha' : 'Sucesso' }}
                  </span>
                  <button
                    @click="toggleToolExpand(msg.id)"
                    class="text-slate-400 hover:text-slate-200 text-[11px] underline ml-1"
                  >
                    {{ expandedTools[msg.id] ? 'Recolher' : 'Detalhes' }}
                  </button>
                </div>
              </div>

              <!-- Resumo amigável -->
              <div v-if="msg.tool_result?.message" class="text-slate-300 font-sans text-xs bg-slate-900/50 p-2 rounded-lg border border-slate-800">
                {{ msg.tool_result.message }}
              </div>

              <!-- Payload Detalhado Expansível -->
              <div v-if="expandedTools[msg.id]" class="mt-2.5 pt-2 border-t border-slate-800/80 space-y-2 text-[11px]">
                <div v-if="msg.tool_args && Object.keys(msg.tool_args).length > 0">
                  <span class="text-slate-500 block mb-0.5">Parâmetros Enviados:</span>
                  <pre class="bg-slate-900 p-2 rounded text-slate-300 overflow-x-auto text-[10px]">{{ JSON.stringify(msg.tool_args, null, 2) }}</pre>
                </div>
                <div>
                  <span class="text-slate-500 block mb-0.5">Resultado da Execução:</span>
                  <pre class="bg-slate-900 p-2 rounded text-slate-300 overflow-x-auto text-[10px]">{{ JSON.stringify(msg.tool_result, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Loading Indicator com Feedback Visual de Estados Assíncronos -->
        <div v-if="loading" class="flex flex-col space-y-2">
          <div class="bg-slate-800/90 border border-indigo-500/40 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center space-x-3 text-xs text-slate-300 shadow-lg shadow-indigo-500/10">
            <span class="relative flex h-2.5 w-2.5">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
            </span>
            <div class="space-y-0.5">
              <span class="font-bold text-indigo-300">Jeffrey ReAct Loop em execução</span>
              <p class="text-[11px] text-slate-400">Raciocinando estratégias, consultando ferramentas ou sintetizando diretrizes...</p>
            </div>
          </div>
          <!-- Skeleton Loader -->
          <div class="space-y-1.5 pl-3">
            <div class="h-2 bg-slate-800 rounded w-3/4 animate-pulse"></div>
            <div class="h-2 bg-slate-800 rounded w-1/2 animate-pulse"></div>
          </div>
        </div>

        <div v-if="error" class="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300">
          {{ error }}
        </div>
      </div>

      <!-- Input Bar -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/80">
        <form @submit.prevent="handleSend" class="flex items-center space-x-2">
          <input
            v-model="inputText"
            type="text"
            placeholder="Instrua o Jeffrey (ex: 'Audite a VPS', 'Crie um negócio no TikTok Shop')..."
            class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
            :disabled="loading"
          />
          <button
            type="submit"
            :disabled="loading || !inputText.trim()"
            class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 font-semibold text-sm text-white transition flex items-center justify-center shrink-0 shadow"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
