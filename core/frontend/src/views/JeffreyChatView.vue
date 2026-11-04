<template>
  <div class="h-[calc(100vh-8.5rem)] flex gap-4 max-w-7xl mx-auto">
    <!-- LEFT SIDEBAR: Persistent Conversations History -->
    <div class="w-64 bg-slate-900/90 rounded-2xl border border-slate-800 flex flex-col overflow-hidden shadow-xl hidden md:flex">
      <!-- New Conversation Button -->
      <div class="p-3 border-b border-slate-800 bg-slate-950/70">
        <button
          @click="createNewConversation"
          :disabled="creatingChat"
          class="w-full py-2.5 px-3 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-slate-950 font-bold text-xs rounded-xl font-mono flex items-center justify-center gap-2 transition shadow-md"
        >
          <span class="text-sm font-bold">+</span> Nova Conversa
        </button>
      </div>

      <!-- Conversations List -->
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div v-if="loadingConversations" class="text-center py-6 text-slate-500 text-xs font-mono">
          Carregando histórico...
        </div>

        <div
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversation(conv.id)"
          class="group p-2.5 rounded-xl text-xs font-mono cursor-pointer transition flex items-center justify-between border"
          :class="activeConversationId === conv.id
            ? 'bg-cyan-950/50 text-cyan-200 border-cyan-800/80 shadow-sm'
            : 'text-slate-400 border-transparent hover:bg-slate-800/60 hover:text-slate-200'"
        >
          <div class="truncate pr-2">
            <div class="font-semibold truncate text-[11px]">{{ conv.title }}</div>
            <div class="text-[9px] text-slate-500 truncate mt-0.5">
              {{ conv.messages_count || 0 }} msgs • {{ conv.updated_at ? new Date(conv.updated_at).toLocaleDateString() : 'Hoje' }}
            </div>
          </div>

          <button
            @click.stop="deleteConversation(conv.id)"
            class="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-slate-500 transition rounded"
            title="Excluir conversa"
          >
            ✕
          </button>
        </div>

        <div v-if="!loadingConversations && conversations.length === 0" class="text-center py-8 text-slate-500 text-xs font-mono">
          Nenhuma conversa anterior.
        </div>
      </div>
    </div>

    <!-- CENTER AREA: Chat Messages Stream & Controls -->
    <div class="flex-1 bg-slate-900/90 rounded-2xl border border-slate-800 flex flex-col overflow-hidden shadow-xl">
      <!-- Agent Header & Context Controls -->
      <div class="p-3.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/80">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 flex items-center justify-center font-bold text-slate-950 text-base shadow-md">
            J
          </div>
          <div>
            <div class="font-bold text-xs text-slate-100 flex items-center gap-2">
              {{ currentConversation?.title || 'Jeffrey AI Orchestrator' }}
              <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                Online & Persistente
              </span>
            </div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">
              Multi-Provedor (Gemini + OpenAI + Llama Local) • Teto: R$ 200/mês
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Engine Selector -->
          <select
            v-model="chosenProvider"
            class="bg-slate-950 text-cyan-300 text-[11px] font-mono rounded-lg px-2.5 py-1.5 focus:outline-none border border-slate-700"
          >
            <option value="hybrid">⚡ Híbrido (Gemini Free → OpenAI → Llama)</option>
            <option value="gemini">✨ Google Gemini 1.5 Flash</option>
            <option value="openai">🤖 OpenAI GPT-4o-mini</option>
            <option value="ollama">🦙 Llama Local (Ollama R$ 0)</option>
          </select>

          <!-- Mobile New Chat Button -->
          <button
            @click="createNewConversation"
            class="md:hidden px-2.5 py-1.5 text-xs bg-cyan-600 text-white rounded-lg font-mono"
          >
            +
          </button>
        </div>
      </div>

      <!-- Messages Stream -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        <div
          v-for="msg in messages"
          :key="msg.id || msg.created_at"
          class="flex flex-col"
          :class="msg.role === 'user' ? 'items-end' : 'items-start'"
        >
          <!-- Metadata Badge -->
          <div class="text-[10px] font-mono text-slate-500 mb-1 px-1 flex flex-wrap items-center gap-2">
            <span>{{ msg.role === 'user' ? 'Comandante' : 'Jeffrey AI' }}</span>
            <span
              v-if="msg.provider && msg.provider !== 'system'"
              class="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700"
            >
              {{ msg.provider }} <span v-if="msg.latency_ms">({{ msg.latency_ms }}ms)</span>
            </span>
            <span
              v-if="msg.tokens?.total_tokens"
              class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800"
            >
              ~{{ msg.tokens.total_tokens }} tokens
            </span>
          </div>

          <!-- Message Bubble -->
          <div
            class="max-w-2xl p-4 rounded-2xl text-xs leading-relaxed"
            :class="msg.role === 'user' 
              ? 'bg-amber-500 text-slate-950 font-medium rounded-tr-none shadow-md' 
              : 'bg-slate-800/90 text-slate-100 border border-slate-700/80 rounded-tl-none whitespace-pre-line shadow-md'"
          >
            <!-- Fallback alert if triggered -->
            <div v-if="msg.fallback_used" class="mb-2 p-1.5 bg-amber-950/60 border border-amber-800/70 rounded text-[10px] font-mono text-amber-300">
              ⚠️ Fallback de Inteligência: {{ msg.fallback_reason || 'Roteado automaticamente para provedor disponível.' }}
            </div>

            <!-- Content -->
            <div>{{ msg.content }}</div>

            <!-- Tool Execution Card -->
            <div
              v-if="msg.tool_calls && msg.tool_calls.length > 0"
              class="mt-3 p-2.5 bg-slate-950/90 rounded-xl border border-cyan-800/70 text-[11px] font-mono"
            >
              <div class="text-cyan-400 font-bold flex items-center gap-1.5 mb-1">
                <span>⚙️ Ferramenta Executada:</span>
                <span class="text-white">{{ msg.tool_calls[0].name }}</span>
              </div>
              <pre class="text-[10px] text-slate-400 overflow-x-auto p-1 bg-slate-900 rounded border border-slate-800">{{ JSON.stringify(msg.tool_calls[0].arguments, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <!-- Generation Spinner -->
        <div v-if="loading" class="flex items-center space-x-2 text-cyan-400 text-xs font-mono p-2">
          <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <span>Jeffrey consultando memórias, analisando intenção e executando ferramentas...</span>
        </div>
      </div>

      <!-- Input Bar -->
      <div class="p-3 sm:p-4 border-t border-slate-800 bg-slate-950/70">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input
            v-model="inputMessage"
            type="text"
            placeholder="Pergunte sobre projetos, negócios, solicite criação de arquivos ou consulte métricas..."
            :disabled="loading"
            class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-xs text-slate-100 focus:outline-none focus:border-cyan-500 transition"
          />
          <button
            type="submit"
            :disabled="loading || !inputMessage.trim()"
            class="px-5 py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl font-mono transition flex items-center gap-1.5 shadow-md"
          >
            <span v-if="loading" class="animate-spin">↻</span>
            <span v-else>Enviar ➔</span>
          </button>
        </form>
      </div>
    </div>

    <!-- RIGHT SIDEBAR: Specialized Agents & Operational Memory -->
    <div class="w-72 space-y-3 hidden lg:flex lg:flex-col">
      <!-- Specialized Agents Pool (Real from DB) -->
      <div class="bg-slate-900/90 p-4 rounded-2xl border border-slate-800 shadow-xl">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider font-mono mb-2.5 flex items-center justify-between">
          <span>Agentes Especializados</span>
          <span class="text-[9px] text-cyan-400 font-mono">{{ agents.length }} Ativos</span>
        </h4>
        <div class="space-y-1.5 text-xs max-h-48 overflow-y-auto pr-1">
          <div
            v-for="agent in agents"
            :key="agent.id"
            class="p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
          >
            <div>
              <div class="font-semibold text-slate-200 text-[11px]">{{ agent.name }}</div>
              <div class="text-[9px] text-slate-500 truncate max-w-[170px]">{{ agent.role }}</div>
            </div>
            <span class="w-2 h-2 rounded-full" :class="agent.is_active ? 'bg-emerald-400' : 'bg-slate-600'"></span>
          </div>
        </div>
      </div>

      <!-- Tools Catalog Quick View -->
      <div class="bg-slate-900/90 p-4 rounded-2xl border border-slate-800 shadow-xl flex-1 overflow-y-auto">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider font-mono mb-2.5 flex items-center justify-between">
          <span>Ferramentas Reais</span>
          <span class="text-[9px] text-amber-400 font-mono">{{ toolsList.length }} Prontas</span>
        </h4>
        <div class="space-y-1.5 text-[11px] font-mono text-slate-400">
          <div
            v-for="t in toolsList"
            :key="t.name"
            class="p-2 rounded-lg bg-slate-950/50 border border-slate-800/60"
          >
            <div class="text-cyan-300 font-semibold text-[10px] flex justify-between">
              <span>{{ t.name }}</span>
              <span class="text-[8px] px-1 py-0.2 rounded bg-slate-800 text-slate-400">Cat. {{ t.category }}</span>
            </div>
            <div class="text-[9px] text-slate-500 mt-0.5 line-clamp-1">{{ t.description }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import axios from 'axios'

const conversations = ref([])
const activeConversationId = ref(null)
const currentConversation = ref(null)
const messages = ref([])

const loading = ref(false)
const loadingConversations = ref(false)
const creatingChat = ref(false)
const inputMessage = ref('')
const chosenProvider = ref('hybrid')
const chatContainer = ref(null)

const agents = ref([])
const toolsList = ref([])

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const fetchConversations = async () => {
  loadingConversations.value = true
  try {
    const res = await axios.get('/api/v1/chat/conversations')
    if (res.data?.conversations) {
      conversations.value = res.data.conversations
      if (conversations.value.length > 0 && !activeConversationId.value) {
        selectConversation(conversations.value[0].id)
      } else if (conversations.value.length === 0) {
        createNewConversation()
      }
    }
  } catch (err) {
    console.error('Falha ao listar conversas:', err)
  } finally {
    loadingConversations.value = false
  }
}

const selectConversation = async (id) => {
  activeConversationId.value = id
  loading.value = true
  try {
    const res = await axios.get(`/api/v1/chat/conversations/${id}`)
    if (res.data?.conversation) {
      currentConversation.value = res.data.conversation
      messages.value = res.data.conversation.messages || []
      scrollToBottom()
    }
  } catch (err) {
    console.error('Falha ao obter mensagens da conversa:', err)
  } finally {
    loading.value = false
  }
}

const createNewConversation = async () => {
  creatingChat.value = true
  try {
    const res = await axios.post('/api/v1/chat/conversations', {
      title: 'Nova Conversa',
    })
    if (res.data?.conversation) {
      conversations.value.unshift(res.data.conversation)
      selectConversation(res.data.conversation.id)
    }
  } catch (err) {
    console.error('Falha ao criar conversa:', err)
  } finally {
    creatingChat.value = false
  }
}

const deleteConversation = async (id) => {
  if (!confirm('Deseja excluir esta conversa e seu histórico?')) return
  try {
    await axios.delete(`/api/v1/chat/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeConversationId.value === id) {
      if (conversations.value.length > 0) {
        selectConversation(conversations.value[0].id)
      } else {
        messages.value = []
        activeConversationId.value = null
        currentConversation.value = null
      }
    }
  } catch (err) {
    console.error('Falha ao excluir conversa:', err)
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  if (!activeConversationId.value) {
    await createNewConversation()
  }

  const text = inputMessage.value
  inputMessage.value = ''

  // Optimistic UI update
  messages.value.push({
    role: 'user',
    content: text,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()
  loading.value = true

  try {
    const res = await axios.post(`/api/v1/chat/conversations/${activeConversationId.value}/messages`, {
      message: text,
      provider: chosenProvider.value,
    })

    if (res.data?.message) {
      messages.value.push(res.data.message)
      // Update title in list if changed
      const conv = conversations.value.find(c => c.id === activeConversationId.value)
      if (conv && conv.title === 'Nova Conversa') {
        conv.title = text.slice(0, 30) + '...'
      }
      scrollToBottom()
    }
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: `[Jeffrey Modo Resiliente]: Erro ao processar mensagem via API. Detalhes: ${err.response?.data?.message || err.message}`,
      provider: 'offline-error',
    })
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

const fetchAuxiliaryData = async () => {
  try {
    const [agentsRes, toolsRes] = await Promise.all([
      axios.get('/api/v1/agents'),
      axios.get('/api/v1/chat/tools'),
    ])
    if (agentsRes.data?.agents) agents.value = agentsRes.data.agents
    if (toolsRes.data?.tools) toolsList.value = toolsRes.data.tools
  } catch (e) {
    console.error('Falha ao carregar agentes e ferramentas:', e)
  }
}

onMounted(() => {
  fetchConversations()
  fetchAuxiliaryData()
})
</script>
