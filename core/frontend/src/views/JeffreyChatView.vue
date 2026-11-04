<template>
  <div class="h-[calc(100vh-7.5rem)] flex gap-3 max-w-[1400px]">
    <!-- 1. LEFT SIDEBAR: Persistent Conversations History -->
    <div class="w-56 pixel-wood rpg-rivets p-2.5 flex flex-col overflow-hidden hidden lg:flex shrink-0">
      <button
        @click="createNewConversation"
        :disabled="creatingChat"
        class="pixel-btn-gold w-full py-2 px-3 text-xs flex items-center justify-center gap-1.5 mb-2.5"
      >
        <span>+</span> Nova Conversa
      </button>

      <div class="flex-1 overflow-y-auto pixel-wood-inset p-1.5 space-y-1 text-xs">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversation(conv.id)"
          class="p-2 rounded cursor-pointer transition flex items-center justify-between border"
          :class="activeConversationId === conv.id
            ? 'bg-[#5c3419] text-[#fef08a] border-[#f59e0b]'
            : 'text-[#e2c699] border-transparent hover:bg-[#3d210f]'"
        >
          <div class="truncate pr-1">
            <div class="truncate text-[11px] font-bold">{{ conv.title }}</div>
            <div class="text-[9px] text-[#c49a6c] mt-0.5">{{ conv.messages_count || 0 }} msgs</div>
          </div>
          <button
            @click.stop="deleteConversation(conv.id)"
            class="text-[#c49a6c] hover:text-red-400 p-1 text-[10px]"
            title="Excluir conversa"
          >
            ✕
          </button>
        </div>

        <div v-if="!loadingConversations && conversations.length === 0" class="text-center py-6 text-[#c49a6c] text-xs">
          Nenhuma conversa anterior.
        </div>
      </div>
    </div>

    <!-- 2. CENTER AREA: Chat Messages Stream & Live Worker Banner -->
    <div class="flex-1 min-w-0 pixel-wood rpg-rivets p-3 flex flex-col overflow-hidden">
      <div class="pixel-wood-inset p-2.5 mb-2.5 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center space-x-2.5 min-w-0">
          <div class="w-9 h-9 rounded bg-[#5c3419] border-2 border-[#f59e0b] text-lg flex items-center justify-center shrink-0">
            🧙‍♂️
          </div>
          <div class="min-w-0">
            <div class="font-extrabold text-xs text-[#fff6e0] flex items-center gap-2 flex-wrap">
              <span class="truncate">{{ currentConversation?.title || 'Jeffrey AI & Agentes' }}</span>
              <span
                v-if="jeffreyActivity.is_working"
                class="text-[10px] px-2 py-0.5 rounded bg-[#78350f] text-[#fef08a] border border-[#f59e0b] flex items-center gap-1.5 animate-pulse"
              >
                <span class="w-2 h-2 rounded-full bg-[#fbbf24]"></span>
                ⚙️ TRABALHANDO ({{ (jeffreyActivity.counts?.in_progress || 0) + (jeffreyActivity.counts?.pending || 0) }} ativa)
              </span>
              <span
                v-else
                class="text-[10px] px-2 py-0.5 rounded bg-[#14532d] text-[#86efac] border border-[#22c55e] flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#4ade80]"></span>
                OCIOSO (Aguardando Ordens)
              </span>
            </div>
            <div class="text-[10px] text-[#d9bc8c] truncate">
              Orquestrador Soberano do Império • Progresso auditado em tempo real
            </div>
          </div>
        </div>

        <div class="flex items-center gap-1.5 flex-wrap">
          <select
            v-model="chosenProvider"
            class="bg-[#241207] text-[#fbbf24] text-[11px] font-bold rounded px-2 py-1.5 border border-[#784725]"
          >
            <option value="hybrid">⚡ Híbrido (Gemini → OpenAI → Llama)</option>
            <option value="gemini">✨ Google Gemini Flash</option>
            <option value="openai">🤖 OpenAI GPT-4o-mini</option>
            <option value="ollama">🦙 Llama Local (Ollama R$ 0)</option>
          </select>

          <button
            @click="promptNewBackgroundTask"
            class="pixel-btn-gold px-2.5 py-1.5 text-[11px] flex items-center gap-1"
          >
            <span>⚡</span> + Tarefa Real
          </button>

          <button
            @click="showActivityPanel = !showActivityPanel"
            class="pixel-btn-wood px-2.5 py-1.5 text-[11px] flex items-center gap-1"
          >
            <span>📋</span>
            <span>Progresso ({{ jeffreyActivity.counts?.total || 0 }})</span>
          </button>
        </div>
      </div>

      <!-- LIVE WORKER PROGRESS BANNER -->
      <div
        v-if="jeffreyActivity.is_working"
        class="mb-2.5 p-2.5 rounded bg-[#2b1507] border-2 border-[#f59e0b] text-xs text-[#fff6e0] shadow-md"
      >
        <div class="flex items-center justify-between gap-2 mb-1.5">
          <div class="font-extrabold text-[#fbbf24] flex items-center gap-2 truncate">
            <span class="inline-block w-2.5 h-2.5 rounded-full bg-[#fbbf24] animate-ping"></span>
            <span>
              Trabalhando agora:
              <strong class="text-white">#{{ jeffreyActivity.worker_state?.task_id || '?' }}</strong>
              — {{ jeffreyActivity.worker_state?.title || 'Executando pesquisa/tarefa...' }}
            </span>
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#451a03] text-[#fde68a] border border-[#8c5828] shrink-0">
            {{ jeffreyActivity.worker_state?.agent_name || 'Jeffrey' }}
          </span>
        </div>
        <div class="text-[11px] text-[#e2c699] mb-1.5 flex justify-between">
          <span>{{ jeffreyActivity.worker_state?.step || 'Processando no worker assíncrono...' }}</span>
          <span class="font-bold text-[#fbbf24]">{{ jeffreyActivity.worker_state?.progress_percent || 50 }}%</span>
        </div>
        <div class="pixel-bar-bg w-full h-3">
          <div
            class="pixel-bar-energy h-full transition-all duration-500"
            :style="{ width: (jeffreyActivity.worker_state?.progress_percent || 50) + '%' }"
          ></div>
        </div>
      </div>

      <!-- Messages Stream -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto rpg-parchment-inner p-4 space-y-4">
        <div
          v-for="msg in messages"
          :key="msg.id || msg.created_at"
          class="flex flex-col"
          :class="msg.role === 'user' ? 'items-end' : 'items-start'"
        >
          <div class="text-[10px] font-bold text-[#5c3419] mb-1 flex items-center gap-2">
            <span>{{ msg.role === 'user' ? 'Comandante' : 'Jeffrey AI' }}</span>
            <span
              v-if="msg.provider && msg.provider !== 'system'"
              class="text-[9px] px-1.5 py-0.5 rounded bg-[#3b200e] text-[#fbbf24]"
            >
              {{ msg.provider }} <span v-if="msg.latency_ms">({{ msg.latency_ms }}ms)</span>
            </span>
          </div>

          <div
            class="max-w-2xl p-3.5 rounded-lg text-xs leading-relaxed border-2"
            :class="msg.role === 'user'
              ? 'bg-[#5c3419] text-[#fff6e0] border-[#1e0d04] font-medium'
              : 'bg-[#fbf0d9] text-[#231104] border-[#8c5828] whitespace-pre-wrap font-medium'"
          >
            <div>{{ msg.content }}</div>

            <div
              v-if="msg.tool_calls && msg.tool_calls.length > 0"
              class="mt-2.5 p-2 bg-[#2b1507] text-[#fde68a] rounded border border-[#8c5828] font-mono text-[10px]"
            >
              <div class="text-[#fbbf24] font-bold mb-1">⚙️ Ferramenta Executada: {{ msg.tool_calls[0].name }}</div>
              <pre class="overflow-x-auto">{{ JSON.stringify(msg.tool_calls[0].arguments, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <div v-if="loading" class="flex items-center space-x-2 text-[#5c3419] text-xs font-bold">
          <span class="w-2.5 h-2.5 rounded-full bg-[#d97706] animate-ping"></span>
          <span>Jeffrey consultando modelos de IA e executando ferramentas...</span>
        </div>
      </div>

      <!-- Input Bar -->
      <div class="pt-2.5">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input
            v-model="inputMessage"
            type="text"
            placeholder="Ordene ao Jeffrey criar roteiros, pesquisar, inspecionar negócios ou consultar métricas..."
            :disabled="loading"
            class="flex-1 pixel-wood-inset px-4 py-2.5 text-xs text-[#fff6e0] placeholder-[#a8865e] focus:outline-none focus:border-[#f59e0b]"
          />
          <button
            type="submit"
            :disabled="loading || !inputMessage.trim()"
            class="pixel-btn-gold px-5 py-2.5 text-xs"
          >
            Enviar ➔
          </button>
        </form>
      </div>
    </div>

    <!-- 3. RIGHT SIDEBAR: LIVE JEFFREY ACTIVITY, TASKS & PROGRESS MONITOR -->
    <div
      v-if="showActivityPanel"
      class="w-80 xl:w-96 pixel-wood rpg-rivets p-2.5 flex flex-col overflow-hidden shrink-0"
    >
      <div class="pixel-wood-inset p-2.5 mb-2 flex items-center justify-between">
        <div>
          <div class="font-extrabold text-xs text-[#fef08a] flex items-center gap-1.5">
            <span>📡</span>
            <span>Monitor do Jeffrey (Ao Vivo)</span>
          </div>
          <div class="text-[10px] text-[#d9bc8c]">
            Atualiza a cada 4s • Fila Redis: {{ jeffreyActivity.queue_length || 0 }}
          </div>
        </div>
        <button @click="fetchJeffreyActivity" class="pixel-btn-wood px-2 py-1 text-[10px]">
          ↻ Atualizar
        </button>
      </div>

      <div class="grid grid-cols-4 gap-1.5 mb-2 text-center">
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Na Fila</div>
          <div class="text-sm font-black text-[#fbbf24]">{{ jeffreyActivity.counts?.pending || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Fazendo</div>
          <div class="text-sm font-black text-[#38bdf8]">{{ jeffreyActivity.counts?.in_progress || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Prontas</div>
          <div class="text-sm font-black text-[#4ade80]">{{ jeffreyActivity.counts?.completed || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Falhas</div>
          <div class="text-sm font-black text-[#f87171]">{{ jeffreyActivity.counts?.failed || 0 }}</div>
        </div>
      </div>

      <div class="flex gap-1.5 mb-2">
        <button
          @click="activitySubTab = 'tasks'"
          class="flex-1 py-1.5 px-2 rounded text-[11px] font-extrabold border transition"
          :class="activitySubTab === 'tasks'
            ? 'bg-[#63391b] text-[#fef08a] border-[#f59e0b]'
            : 'bg-[#2b1507] text-[#c49a6c] border-[#1a0b03] hover:text-white'"
        >
          📋 Trabalhos ({{ jeffreyActivity.recent_tasks?.length || 0 }})
        </button>
        <button
          @click="activitySubTab = 'decisions'"
          class="flex-1 py-1.5 px-2 rounded text-[11px] font-extrabold border transition"
          :class="activitySubTab === 'decisions'
            ? 'bg-[#63391b] text-[#fef08a] border-[#f59e0b]'
            : 'bg-[#2b1507] text-[#c49a6c] border-[#1a0b03] hover:text-white'"
        >
          🔍 Log de Ações ({{ jeffreyActivity.recent_decisions?.length || 0 }})
        </button>
      </div>

      <!-- SUB-TAB 1: TASKS -->
      <div v-if="activitySubTab === 'tasks'" class="flex-1 overflow-y-auto pixel-wood-inset p-2 space-y-2 text-xs">
        <div class="p-2.5 rounded border-2" :class="jeffreyActivity.is_working ? 'bg-[#3b200e] border-[#f59e0b]' : 'bg-[#241207] border-[#4a2810]'">
          <div class="flex items-center justify-between text-[11px] font-bold">
            <span class="text-[#fef08a]">Estado Real do Worker:</span>
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-black uppercase"
              :class="jeffreyActivity.is_working ? 'bg-[#f59e0b] text-[#1e0d04]' : 'bg-[#14532d] text-[#86efac]'"
            >
              {{ jeffreyActivity.is_working ? 'EM EXECUÇÃO' : 'OCIOSO / LIVRE' }}
            </span>
          </div>
          <div class="text-[11px] text-[#e2c699] mt-1 leading-snug">
            {{ jeffreyActivity.worker_state?.step || 'Nenhuma tarefa rodando em background no momento.' }}
          </div>
        </div>

        <div
          v-if="!jeffreyActivity.recent_tasks || jeffreyActivity.recent_tasks.length === 0"
          class="rpg-parchment-inner p-4 text-center space-y-2"
        >
          <div class="text-base">📭</div>
          <div class="font-extrabold text-[#2b1507] text-xs">Nenhuma tarefa registrada</div>
          <p class="text-[11px] text-[#4a2810]">
            Clique abaixo para disparar uma pesquisa ou trabalho real em segundo plano!
          </p>
          <button @click="promptNewBackgroundTask" class="pixel-btn-gold px-3 py-1.5 text-[11px] w-full">
            + Criar Tarefa Real para o Jeffrey
          </button>
        </div>

        <div
          v-for="t in jeffreyActivity.recent_tasks"
          :key="t.id"
          class="rpg-parchment-inner p-2.5 space-y-1.5 border-2 border-[#3a1e0b]"
        >
          <div class="flex items-start justify-between gap-1.5">
            <div class="font-extrabold text-[11.5px] text-[#1e0d04] leading-snug">
              <span class="font-mono text-[#78350f]">#{{ t.id }}</span> {{ t.title }}
            </div>
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-black uppercase shrink-0 border"
              :class="{
                'bg-[#0284c7] text-white border-[#0369a1] animate-pulse': t.status === 'in_progress',
                'bg-[#d97706] text-[#1e0d04] border-[#78350f]': t.status === 'pending',
                'bg-[#15803d] text-white border-[#052e16]': t.status === 'completed',
                'bg-[#b91c1c] text-white border-[#450a0a]': t.status === 'failed',
                'bg-[#57534e] text-white border-[#292524]': t.status === 'cancelled'
              }"
            >
              {{ formatTaskStatus(t.status) }}
            </span>
          </div>

          <div class="flex items-center justify-between text-[10px] text-[#4a2810] font-semibold">
            <span>🤖 {{ t.agent_name || 'Jeffrey' }} ({{ t.type }})</span>
            <span>{{ formatTimeShort(t.completed_at || t.started_at || t.created_at) }}</span>
          </div>

          <div v-if="t.status === 'in_progress' || t.status === 'pending'" class="pt-1">
            <div class="pixel-bar-bg w-full h-2.5">
              <div
                class="pixel-bar-energy h-full transition-all"
                :style="{ width: t.status === 'in_progress' ? '65%' : '20%' }"
              ></div>
            </div>
          </div>

          <div v-if="t.error_message" class="p-1.5 rounded bg-red-100 border border-red-400 text-[10px] text-red-900 font-semibold">
            ⚠️ {{ t.error_message }}
          </div>

          <div class="pt-1 flex flex-wrap items-center justify-between gap-1 border-t border-[#c4924d]">
            <button
              v-if="t.result?.response"
              @click="expandedTaskId = (expandedTaskId === t.id ? null : t.id)"
              class="text-[10.5px] font-extrabold text-[#78350f] hover:underline"
            >
              {{ expandedTaskId === t.id ? '▲ Ocultar Resultado' : '👁️ Ver Entrega Completa' }}
            </button>
            <span v-else class="text-[10px] text-[#5c3419] italic">
              {{ t.status === 'completed' ? 'Concluído' : 'Sem resultado ainda' }}
            </span>

            <div class="flex items-center gap-1">
              <button
                v-if="t.result?.response"
                @click="sendTaskResultToChat(t)"
                class="px-2 py-0.5 rounded bg-[#5c3419] text-[#fef08a] text-[9.5px] font-bold hover:brightness-110"
              >
                📥 No Chat
              </button>
              <button
                v-if="t.status === 'failed' || t.status === 'cancelled' || t.status === 'pending'"
                @click="retryTask(t.id)"
                class="px-2 py-0.5 rounded bg-[#d97706] text-[#1e0d04] text-[9.5px] font-bold hover:brightness-110"
              >
                🔄 Rodar
              </button>
              <button
                v-if="t.status === 'pending' || t.status === 'in_progress'"
                @click="cancelTask(t.id)"
                class="px-1.5 py-0.5 rounded bg-[#991b1b] text-white text-[9.5px] font-bold"
              >
                ✕
              </button>
            </div>
          </div>

          <div
            v-if="expandedTaskId === t.id && t.result?.response"
            class="mt-1.5 p-2 rounded bg-[#fbf0d9] border border-[#8c5828] text-[11px] text-[#1e0d04] whitespace-pre-wrap max-h-60 overflow-y-auto font-medium"
          >
            {{ t.result.response }}
          </div>
        </div>
      </div>

      <!-- SUB-TAB 2: DECISIONS -->
      <div v-else class="flex-1 overflow-y-auto pixel-wood-inset p-2 space-y-2 text-xs">
        <div
          v-for="d in jeffreyActivity.recent_decisions"
          :key="d.id"
          class="rpg-parchment-inner p-2.5 space-y-1 border border-[#3a1e0b]"
        >
          <div class="flex items-center justify-between">
            <span class="font-extrabold text-[11px] text-[#1e0d04]">⚡ {{ d.agent_name }}</span>
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#3b200e] text-[#fbbf24]">
              {{ d.action_type }}
            </span>
          </div>
          <div class="text-[10.5px] text-[#3a1f0d] font-medium">{{ d.justification }}</div>
          <div class="flex justify-between text-[9.5px] text-[#5c3419] font-semibold pt-0.5">
            <span>Motor: {{ d.input_payload?.provider || 'system' }} ({{ d.input_payload?.latency_ms || 0 }}ms)</span>
            <span>{{ formatTimeShort(d.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
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

const showActivityPanel = ref(true)
const activitySubTab = ref('tasks')
const expandedTaskId = ref(null)
const jeffreyActivity = ref({
  is_working: false,
  queue_length: 0,
  worker_state: { status: 'idle', step: 'Ocioso — Aguardando novas ordens.', progress_percent: 0 },
  counts: { total: 0, pending: 0, in_progress: 0, completed: 0, failed: 0, cancelled: 0 },
  active_tasks: [],
  recent_tasks: [],
  recent_decisions: [],
})
let lastCompletedCount = 0

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const fetchJeffreyActivity = async () => {
  try {
    const res = await axios.get('/api/v1/jeffrey/activity')
    if (res.data?.success) {
      const prevCompleted = lastCompletedCount
      const newCompleted = res.data.counts?.completed || 0
      jeffreyActivity.value = res.data
      lastCompletedCount = newCompleted

      if (newCompleted > prevCompleted && activeConversationId.value && !loading.value) {
        selectConversation(activeConversationId.value)
      }
    }
  } catch (e) {
    console.error('Falha ao obter atividades do Jeffrey:', e)
  }
}

const formatTaskStatus = (st) => {
  const map = {
    pending: '⏳ NA FILA',
    in_progress: '⚙️ FAZENDO',
    completed: '✅ CONCLUÍDO',
    failed: '❌ FALHOU',
    cancelled: '🚫 CANCELADO',
  }
  return map[st] || st
}

const formatTimeShort = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (_) {
    return ''
  }
}

const promptNewBackgroundTask = async () => {
  const title = prompt('Qual trabalho ou pesquisa o Jeffrey deve executar em segundo plano?')
  if (!title || !title.trim()) return
  try {
    const res = await axios.post('/api/v1/tasks', {
      title: title.trim().slice(0, 120),
      type: 'research_and_execution',
      agent_name: 'Research Agent',
      payload: {
        prompt: title.trim(),
        provider: chosenProvider.value,
        conversation_id: activeConversationId.value,
      },
    })
    if (res.data?.task) {
      showActivityPanel.value = true
      activitySubTab.value = 'tasks'
      await fetchJeffreyActivity()
      if (activeConversationId.value) {
        messages.value.push({
          role: 'assistant',
          content: `⚙️ **[Tarefa #${res.data.task.id} Enfileirada no Worker]:** _${res.data.task.title}_\n\nAcompanhe o progresso na barra lateral **Monitor do Jeffrey**. Assim que finalizar, o resultado completo será entregue aqui no chat!`,
          provider: 'jeffrey-worker',
        })
        scrollToBottom()
      }
    }
  } catch (e) {
    alert('Erro ao criar tarefa: ' + (e.response?.data?.message || e.message))
  }
}

const retryTask = async (taskId) => {
  try {
    await axios.post(`/api/v1/tasks/${taskId}/retry`)
    await fetchJeffreyActivity()
  } catch (e) {
    alert('Erro ao reenfileirar tarefa: ' + (e.response?.data?.message || e.message))
  }
}

const cancelTask = async (taskId) => {
  try {
    await axios.post(`/api/v1/tasks/${taskId}/cancel`)
    await fetchJeffreyActivity()
  } catch (e) {
    alert('Erro ao cancelar tarefa: ' + (e.response?.data?.message || e.message))
  }
}

const sendTaskResultToChat = (task) => {
  if (!task?.result?.response) return
  messages.value.push({
    role: 'assistant',
    content: `📋 **[Resultado da Tarefa #${task.id} — ${task.title}]:**\n\n${task.result.response}`,
    provider: task.result.provider || 'worker',
    latency_ms: task.result.latency_ms || 0,
  })
  scrollToBottom()
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
  try {
    const res = await axios.get(`/api/v1/chat/conversations/${id}`)
    if (res.data?.conversation) {
      currentConversation.value = res.data.conversation
      messages.value = res.data.conversation.messages || []
      scrollToBottom()
    }
  } catch (err) {
    console.error('Falha ao obter mensagens da conversa:', err)
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
      const conv = conversations.value.find(c => c.id === activeConversationId.value)
      if (conv && conv.title === 'Nova Conversa') {
        conv.title = text.slice(0, 30) + '...'
      }
      fetchJeffreyActivity()
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

let pollTimer = null
onMounted(() => {
  fetchConversations()
  fetchJeffreyActivity()
  pollTimer = setInterval(fetchJeffreyActivity, 4000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
