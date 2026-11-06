<script setup>
import { ref, watch, nextTick } from 'vue'
import { useAgentChat } from '@/composables/useAgentChat'

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

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      await loadOrCreateConversation(props.businessId)
      scrollToBottom()
    }
  }
)

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
      <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow">
            ✨
          </div>
          <div>
            <h2 class="text-sm font-bold text-white">COO Virtual (Gemini 3.8)</h2>
            <p class="text-[11px] text-slate-400 font-mono">
              {{ conversation?.business ? `Contexto: ${conversation.business.name}` : 'Modo Incubadora de Negócios' }}
            </p>
          </div>
        </div>

        <button
          @click="emit('close')"
          class="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- Quick Action Pills -->
      <div class="p-3 bg-slate-950/30 border-b border-slate-800/80 flex items-center space-x-2 overflow-x-auto text-[11px]">
        <button
          @click="handleQuickPrompt('Estruture um novo modelo de negócio digital lucrativo no nicho de utilidades')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition"
        >
          💡 Conceber Negócio
        </button>
        <button
          @click="handleQuickPrompt('Minere 3 produtos vencedores com alta comissão na TikTok Shop e crie os roteiros')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition"
        >
          🔥 Minerar TikTok Shop
        </button>
        <button
          @click="handleQuickPrompt('Consulte minha agenda de hoje e me diga quais são os melhores horários livres para gravação')"
          class="shrink-0 px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition"
        >
          📅 Checar Agenda
        </button>
      </div>

      <!-- Messages Stream -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        <div v-if="messages.length === 0" class="text-center py-12 text-slate-500">
          <div class="w-12 h-12 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-3 text-slate-400 text-xl">
            🤖
          </div>
          <p class="font-semibold text-slate-300">Como posso acelerar sua operação hoje?</p>
          <p class="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Posso conceber empreendimentos, minerar produtos, escrever roteiros virais e organizar sua agenda.
          </p>
        </div>

        <template v-for="msg in messages" :key="msg.id">
          <!-- Mensagem do Usuário -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[85%] bg-emerald-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow text-sm">
              <p class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Mensagem do Modelo (Gemini) -->
          <div v-else-if="msg.role === 'model'" class="flex justify-start">
            <div class="max-w-[90%] bg-slate-800/90 text-slate-200 border border-slate-700/60 px-4 py-3 rounded-2xl rounded-tl-sm shadow space-y-2">
              <div class="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                <span>COO Virtual</span>
                <span v-if="msg.latency_ms">· {{ msg.latency_ms }}ms</span>
              </div>
              <p v-if="msg.content" class="whitespace-pre-wrap leading-relaxed text-sm text-slate-100">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Mensagem de Tool (Execução de Ferramenta PHP) -->
          <div v-else-if="msg.role === 'tool'" class="flex justify-start">
            <div class="w-full bg-slate-950/70 border border-slate-800 rounded-xl p-3 text-xs font-mono">
              <div class="flex items-center justify-between text-slate-400 mb-1.5">
                <div class="flex items-center space-x-1.5 text-indigo-400 font-semibold">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/></svg>
                  <span>Tool: {{ msg.tool_name }}</span>
                </div>
                <span :class="msg.tool_failed ? 'text-rose-400' : 'text-emerald-400'">
                  {{ msg.tool_failed ? 'Falha' : 'Sucesso' }}
                </span>
              </div>
              <div v-if="msg.tool_result?.message" class="text-slate-300 font-sans">
                {{ msg.tool_result.message }}
              </div>
            </div>
          </div>
        </template>

        <!-- Loading Indicator com Feedback Visual de Estados Assíncronos -->
        <div v-if="loading" class="flex flex-col space-y-2">
          <div class="bg-slate-800/90 border border-indigo-500/30 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center space-x-3 text-xs text-slate-300 shadow-lg shadow-indigo-500/10">
            <span class="relative flex h-2.5 w-2.5">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
            </span>
            <div class="space-y-0.5">
              <span class="font-bold text-indigo-300">Gemini 3.8 em execução</span>
              <p class="text-[11px] text-slate-400">Analisando estratégias, estruturando canvas ou despachando tools...</p>
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
      <div class="p-4 border-t border-slate-800 bg-slate-950/70">
        <form @submit.prevent="handleSend" class="flex items-center space-x-2">
          <input
            v-model="inputText"
            type="text"
            placeholder="Digite suas instruções ou peça ao COO..."
            class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
            :disabled="loading"
          />
          <button
            type="submit"
            :disabled="loading || !inputText.trim()"
            class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 font-semibold text-sm text-white transition flex items-center justify-center shrink-0"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

