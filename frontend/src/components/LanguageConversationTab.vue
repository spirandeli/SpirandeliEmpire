<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'
import AudioRecorder from '@/components/AudioRecorder.vue'

const languageStore = useLanguageStore()
const swal = useSwal()

const selectedTopic = ref('business_meeting')
const textInput = ref('')
const isAudioInputActive = ref(false)
const chatContainer = ref(null)

onMounted(async () => {
  try {
    await languageStore.fetchConversation()
    scrollToBottom()
  } catch (err) {
    console.error('Erro ao carregar conversação:', err)
  }
})

const messages = computed(() => languageStore.conversationMessages || [])
const topics = computed(() => languageStore.practiceTopics || [])
const targetLanguage = computed(() => languageStore.profile?.target_language || 'Inglês')
const isLoading = computed(() => languageStore.conversationLoading)

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

function selectTopic(topicId) {
  selectedTopic.value = topicId
}

function speakText(text) {
  if (!window.speechSynthesis || !text) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  const lang = targetLanguage.value
  const langCodeMap = {
    Inglês: 'en-US',
    Espanhol: 'es-ES',
    Francês: 'fr-FR',
    Alemão: 'de-DE',
    Italiano: 'it-IT',
    Mandarim: 'zh-CN',
  }
  utterance.lang = langCodeMap[lang] || 'en-US'
  utterance.rate = 0.95
  window.speechSynthesis.speak(utterance)
}

async function handleSendMessage() {
  const content = textInput.value.trim()
  if (!content || isLoading.value) return

  textInput.value = ''
  try {
    await languageStore.sendConversationMessage({
      message: content,
      topic: selectedTopic.value,
    })
    scrollToBottom()
  } catch (err) {
    swal.error('Erro ao enviar mensagem', err.response?.data?.message || 'Falha na comunicação com a IA.')
  }
}

async function handleAudioRecorded({ base64, mimeType }) {
  try {
    isAudioInputActive.value = false
    // 1. Analisa áudio para obter a transcrição e avaliação
    const analysis = await languageStore.analyzePronunciation({
      target_text: 'Conversa prática em ' + targetLanguage.value,
      audio_base64: base64,
      mime_type: mimeType,
    })

    const spokenText = analysis.transcription || ''
    if (!spokenText.trim()) {
      swal.toast('Não foi possível identificar voz no áudio. Tente falar mais próximo ao microfone.', 'warning')
      return
    }

    // 2. Envia a transcrição como mensagem na conversa
    await languageStore.sendConversationMessage({
      message: spokenText,
      topic: selectedTopic.value,
    })
    scrollToBottom()
  } catch (err) {
    swal.error('Erro no envio do áudio', err.response?.data?.message || 'Falha ao processar áudio.')
  }
}

async function handleClearConversation() {
  const proceed = await swal.confirm({
    title: 'Limpar Histórico da Conversa?',
    text: 'Todas as mensagens deste diálogo serão apagadas para iniciar uma nova prática do zero.',
    confirmText: 'Sim, limpar agora',
  })

  if (proceed) {
    try {
      await languageStore.clearConversation()
      swal.toast('Conversa reiniciada com sucesso!', 'success')
    } catch (err) {
      swal.error('Erro ao limpar conversa', err.response?.data?.message || 'Falha ao limpar histórico.')
    }
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Top Header do Chat de Conversação -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div class="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span class="text-xs font-mono uppercase font-bold text-indigo-400">Prática Livre & Conversação Nativa</span>
          </div>
          <h2 class="text-xl font-bold text-white">Área Aberta de Conversação em {{ targetLanguage }}</h2>
          <p class="text-xs text-slate-400 max-w-2xl">
            Pratique diálogos reais a qualquer momento com Alex, seu parceiro executivo nativo.
            Receba respostas autênticas no idioma e dicas pedagógicas laterais de como soaria um nativo.
          </p>
        </div>

        <button
          type="button"
          @click="handleClearConversation"
          class="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition flex items-center space-x-1.5 self-start sm:self-auto shrink-0"
          title="Reiniciar conversa e limpar histórico"
        >
          <span>🔄 Nova Conversa</span>
        </button>
      </div>
    </div>

    <!-- SELETOR DE CENÁRIOS / TÓPICOS -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3">
      <span class="text-[11px] font-mono uppercase font-bold text-slate-400 block">Escolha o Tema do Diálogo:</span>

      <div class="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
        <button
          v-for="topic in topics"
          :key="topic.id"
          type="button"
          @click="selectTopic(topic.id)"
          class="px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2 shrink-0 border"
          :class="selectedTopic === topic.id
            ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/20'
            : 'bg-slate-950/70 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'"
        >
          <span>{{ topic.icon }}</span>
          <span>{{ topic.title }}</span>
        </button>
      </div>
    </div>

    <!-- CHAT CONTAINER -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden flex flex-col h-[520px]">
      <!-- Mensagens Stream -->
      <div
        ref="chatContainer"
        class="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-thin bg-slate-950/40"
      >
        <!-- Mensagem de Boas-Vindas se Vazio -->
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
          <div class="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-2xl text-white">
            💬
          </div>
          <div class="space-y-1 max-w-md">
            <h4 class="text-sm font-bold text-white">Inicie sua conversa em {{ targetLanguage }}</h4>
            <p class="text-xs text-slate-400">
              Envie uma mensagem digitada ou fale no microfone. Alex responderá mantendo a conversa fluindo
              e indicará como aperfeiçoar sua formulação.
            </p>
          </div>
          <div class="pt-2 flex flex-wrap justify-center gap-2">
            <button
              type="button"
              @click="textInput = 'Hi Alex, let\'s review the action items from our morning standup.'; handleSendMessage()"
              class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
            >
              "Hi Alex, let's review our action items..."
            </button>
            <button
              type="button"
              @click="textInput = 'Could we schedule a quick touch base to align our quarterly metrics?'; handleSendMessage()"
              class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
            >
              "Could we schedule a quick touch base?..."
            </button>
          </div>
        </div>

        <!-- Lista de Mensagens -->
        <template v-else>
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="flex flex-col"
            :class="msg.role === 'user' ? 'items-end' : 'items-start'"
          >
            <!-- Mensagem do Usuário -->
            <div
              v-if="msg.role === 'user'"
              class="max-w-[85%] sm:max-w-[70%] space-y-2"
            >
              <div class="p-4 rounded-2xl rounded-tr-sm bg-indigo-600 text-white text-xs leading-relaxed shadow-md">
                {{ msg.content }}
              </div>
            </div>

            <!-- Resposta do Assistente / Tutor Nativo -->
            <div
              v-else
              class="max-w-[85%] sm:max-w-[75%] space-y-3"
            >
              <div class="p-4 rounded-2xl rounded-tl-sm bg-slate-950 border border-slate-800 text-slate-100 text-xs leading-relaxed space-y-2 shadow-md">
                <div class="flex items-center justify-between pb-1 border-b border-slate-900">
                  <div class="flex items-center space-x-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span class="font-bold text-indigo-400 text-[11px] font-mono">Alex (Parceiro Nativo)</span>
                  </div>
                  <button
                    type="button"
                    @click="speakText(msg.content)"
                    class="w-6 h-6 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-xs transition"
                    title="Ouvir áudio nativo"
                  >
                    🔊
                  </button>
                </div>

                <p class="font-sans text-xs whitespace-pre-line text-slate-200">
                  {{ msg.content }}
                </p>
              </div>

              <!-- Cartão de Feedback Pedagógico & Dica Nativa (se houver) -->
              <div
                v-if="msg.feedback && (msg.feedback.has_correction || msg.feedback.native_alternative)"
                class="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs space-y-2"
              >
                <div class="flex items-center space-x-1.5 text-amber-400 font-mono font-bold text-[10px] uppercase">
                  <span>💡</span>
                  <span>Dica de Nativo & Feedback de Expressão:</span>
                </div>

                <!-- Correção Gramatical -->
                <p v-if="msg.feedback.has_correction && msg.feedback.correction_note" class="text-amber-200 text-xs leading-relaxed">
                  {{ msg.feedback.correction_note }}
                </p>

                <!-- Versão Nativa Alternativa -->
                <div v-if="msg.feedback.native_alternative" class="p-2.5 rounded-lg bg-slate-950/80 border border-amber-500/20 flex items-center justify-between gap-2">
                  <div>
                    <span class="text-[9px] font-mono uppercase text-slate-400 block">Como um nativo falaria:</span>
                    <span class="text-xs font-serif font-bold text-amber-300">"{{ msg.feedback.native_alternative }}"</span>
                  </div>
                  <button
                    type="button"
                    @click="speakText(msg.feedback.native_alternative)"
                    class="w-6 h-6 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 flex items-center justify-center text-xs transition shrink-0"
                    title="Ouvir versão nativa"
                  >
                    🔊
                  </button>
                </div>

                <!-- Destaques de Vocabulário -->
                <div v-if="msg.feedback.vocabulary_highlight?.length" class="flex flex-wrap gap-1.5 pt-1">
                  <span
                    v-for="(term, tIdx) in msg.feedback.vocabulary_highlight"
                    :key="tIdx"
                    class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                  >
                    + {{ term }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Indicador de Digitação / Resposta do Assistente -->
          <div v-if="isLoading" class="flex items-center space-x-2 text-slate-400 text-xs font-mono p-2">
            <div class="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></div>
            <span>Alex está digitando a réplica em {{ targetLanguage }}...</span>
          </div>
        </template>
      </div>

      <!-- Barra de Input (Texto ou Gravador de Áudio) -->
      <div class="p-4 bg-slate-950 border-t border-slate-800 space-y-3">
        <!-- Alternar entre modo de gravação de áudio e texto -->
        <div v-if="isAudioInputActive" class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono text-rose-400 font-bold">Gravação de Voz para o Chat:</span>
            <button
              type="button"
              @click="isAudioInputActive = false"
              class="text-xs font-mono text-slate-400 hover:text-white"
            >
              ✕ Cancelar Áudio
            </button>
          </div>

          <AudioRecorder
            submit-label="Enviar Mensagem por Voz"
            @recorded="handleAudioRecorded"
            @reset="isAudioInputActive = false"
          />
        </div>

        <form v-else @submit.prevent="handleSendMessage" class="flex items-center space-x-2">
          <button
            type="button"
            @click="isAudioInputActive = true"
            class="w-10 h-10 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-300 hover:text-rose-400 border border-slate-700 flex items-center justify-center text-base transition shrink-0"
            title="Gravar mensagem por voz"
          >
            🎙️
          </button>

          <input
            v-model="textInput"
            type="text"
            class="flex-1 bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition"
            :placeholder="`Digite sua mensagem em ${targetLanguage}...`"
            :disabled="isLoading"
          />

          <button
            type="submit"
            :disabled="!textInput.trim() || isLoading"
            class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold text-xs shadow-md transition flex items-center space-x-1.5 shrink-0"
          >
            <span>Enviar</span>
            <span>→</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

