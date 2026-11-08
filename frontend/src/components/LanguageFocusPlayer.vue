<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'

const emit = defineEmits(['completed'])

const languageStore = useLanguageStore()
const swal = useSwal()

// Estado do Timer de 15 Minutos (15:00 = 900s)
const totalSeconds = 15 * 60
const remainingSeconds = ref(totalSeconds)
const isTimerRunning = ref(true)
let timerInterval = null

// Navegação entre blocos (1, 2 e 3)
const activeBlock = ref(1)

// Respostas do usuário
const block1Answers = ref({})
const block2Answers = ref({})
const block3Input = ref('')

// Feedback da avaliação
const evaluationFeedback = ref(null)

onMounted(() => {
  startTimer()
})

onUnmounted(() => {
  stopTimer()
})

function startTimer() {
  if (timerInterval) clearInterval(timerInterval)
  isTimerRunning.value = true
  timerInterval = setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value--
    } else {
      stopTimer()
      swal.toast('Tempo de 15 minutos atingido! Finalize suas respostas.', 'warning')
    }
  }, 1000)
}

function stopTimer() {
  isTimerRunning.value = false
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function toggleTimer() {
  if (isTimerRunning.value) {
    stopTimer()
  } else {
    startTimer()
  }
}

const timerFormatted = computed(() => {
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

const timerProgressPercent = computed(() => {
  return ((totalSeconds - remainingSeconds.value) / totalSeconds) * 100
})

const session = computed(() => languageStore.currentSession)
const lesson = computed(() => session.value?.lesson_payload || null)

const block1 = computed(() => lesson.value?.block1_srs || null)
const block2 = computed(() => lesson.value?.block2_immersion || null)
const block3 = computed(() => lesson.value?.block3_active_output || null)

// Validação dos blocos
const canFinishBlock1 = computed(() => {
  if (!block1.value?.items) return true
  return Object.keys(block1Answers.value).length === block1.value.items.length
})

const canFinishBlock2 = computed(() => {
  if (!block2.value?.questions) return true
  return Object.keys(block2Answers.value).length === block2.value.questions.length
})

const canSubmitSession = computed(() => {
  return block3Input.value.trim().length >= 10
})

async function handleFinishLesson() {
  if (!canSubmitSession.value) {
    swal.toast('Escreva pelo menos 2 frases no desafio do Bloco 3 para avaliação.', 'warning')
    return
  }

  stopTimer()

  const timeSpent = totalSeconds - remainingSeconds.value

  const payload = {
    user_answers: {
      block1_srs: block1Answers.value,
      block2_immersion: block2Answers.value,
      block3_active_output: block3Input.value.trim(),
    },
    time_spent_seconds: timeSpent,
  }

  try {
    const response = await languageStore.submitDailySession(payload)
    evaluationFeedback.value = response.evaluation || { overall_score: response.score || 90 }
    const streakDays = response.profile?.streak_days ?? response.streak_days ?? 1

    swal.instance.fire({
      icon: 'success',
      title: 'Missão de 15 Minutos Cumprida! 🔥',
      html: `
        <div class="text-xs text-slate-300 font-sans space-y-2">
          <p>Sua ofensiva subiu para <strong>${streakDays} dias seguidos</strong>!</p>
          <p>O Gemini 3.8 Flash avaliou sua produção ativa e salvou novas palavras no seu cofre SRS.</p>
        </div>
      `,
      confirmButtonText: 'Ver Feedback Detalhado',
      confirmButtonColor: '#10b981',
      background: '#0f172a',
      color: '#f8fafc',
    })

    emit('completed', response)
  } catch (err) {
    swal.error('Erro ao avaliar sessão', err.response?.data?.message || 'Falha ao enviar respostas.')
    startTimer()
  }
}

function speakText(text) {
  if (!window.speechSynthesis || !text) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  const lang = languageStore.profile?.target_language
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
</script>

<template>
  <div class="space-y-6">
    <!-- Top Player Bar com Timer Regressivo de 15 Minutos e Seletor de Blocos -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-md sticky top-4 z-20">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <!-- Timer Regressivo 15:00 -->
        <div class="flex items-center space-x-3">
          <div
            class="px-4 py-2 rounded-xl border flex items-center space-x-2.5 transition"
            :class="remainingSeconds < 180
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              : 'bg-slate-950/80 border-slate-700 text-emerald-400'"
          >
            <button
              type="button"
              @click="toggleTimer"
              class="w-6 h-6 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-xs text-white"
              :title="isTimerRunning ? 'Pausar Timer' : 'Continuar Timer'"
            >
              {{ isTimerRunning ? '⏸' : '▶' }}
            </button>
            <span class="font-mono text-xl font-black tracking-wider">{{ timerFormatted }}</span>
            <span class="text-[10px] uppercase font-mono text-slate-400 font-bold hidden sm:inline">Restante</span>
          </div>

          <!-- Título da Lição -->
          <div class="truncate">
            <h3 class="text-sm font-bold text-white truncate">{{ lesson?.lesson_title || 'Sessão de Micro-Learning' }}</h3>
            <span class="text-xs text-slate-400 truncate block">{{ lesson?.daily_theme || 'Treino Adaptativo' }}</span>
          </div>
        </div>

        <!-- Seletor de Blocos Dinâmicos (3 Blocos de 5 min) -->
        <div class="flex items-center space-x-1.5 p-1 bg-slate-950/80 rounded-xl border border-slate-800">
          <button
            type="button"
            @click="activeBlock = 1"
            class="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition flex items-center space-x-1.5"
            :class="activeBlock === 1
              ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
              : 'text-slate-400 hover:text-white'"
          >
            <span>Bloco 1 (SRS)</span>
            <span v-if="canFinishBlock1" class="text-[10px]">✓</span>
          </button>

          <button
            type="button"
            @click="activeBlock = 2"
            class="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition flex items-center space-x-1.5"
            :class="activeBlock === 2
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-slate-400 hover:text-white'"
          >
            <span>Bloco 2 (Imersão)</span>
            <span v-if="canFinishBlock2" class="text-[10px]">✓</span>
          </button>

          <button
            type="button"
            @click="activeBlock = 3"
            class="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition flex items-center space-x-1.5"
            :class="activeBlock === 3
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'text-slate-400 hover:text-white'"
          >
            <span>Bloco 3 (Ativo)</span>
            <span v-if="canSubmitSession" class="text-[10px]">✓</span>
          </button>
        </div>
      </div>

      <!-- Barra de Progresso do Tempo -->
      <div class="w-full bg-slate-800 h-1 rounded-full overflow-hidden mt-3">
        <div
          class="h-full bg-gradient-to-r from-emerald-500 via-indigo-500 to-amber-500 transition-all duration-1000"
          :style="{ width: `${timerProgressPercent}%` }"
        ></div>
      </div>
    </div>

    <!-- TELA DE FEEDBACK INSTANTÂNEO DO GEMINI 3.8 FLASH (Após Conclusão) -->
    <div v-if="evaluationFeedback" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/40 border border-emerald-500/30">
        <div>
          <span class="text-xs font-mono uppercase tracking-widest text-emerald-400 font-bold block mb-1">
            ⚡ Correção Instantânea Gemini 3.8 Flash
          </span>
          <h2 class="text-xl font-bold text-white">{{ evaluationFeedback.feedback_title }}</h2>
          <p class="text-xs text-slate-300 mt-1">{{ evaluationFeedback.feedback_summary }}</p>
        </div>
        <div class="text-right shrink-0">
          <span class="text-xs font-mono text-slate-400 uppercase block font-bold">Nota da Sessão</span>
          <span class="text-4xl font-black font-mono text-emerald-400">{{ evaluationFeedback.overall_score }}</span>
          <span class="text-xs text-slate-500">/100</span>
        </div>
      </div>

      <!-- Bloco 3 Output Comparison: O que você escreveu vs Versão Nativa -->
      <div v-if="evaluationFeedback.block3_active_evaluation" class="space-y-4">
        <h4 class="text-xs font-mono font-bold uppercase text-slate-300 flex items-center space-x-2">
          <span>🎯</span>
          <span>Desafio Ativo: Comparativo Nativo & Etiqueta</span>
        </h4>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- O que você escreveu -->
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <span class="text-[10px] font-mono uppercase text-slate-400 font-bold block">O que você escreveu:</span>
            <p class="text-xs text-slate-200 font-mono italic">
              "{{ evaluationFeedback.block3_active_evaluation.user_input }}"
            </p>
          </div>

          <!-- Correção Natural / Nativa com Áudio -->
          <div class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/40 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono uppercase text-emerald-400 font-bold block">Correção Natural / Nativa:</span>
              <button
                type="button"
                @click="speakText(evaluationFeedback.block3_active_evaluation.natural_native_version)"
                class="w-6 h-6 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 flex items-center justify-center text-xs transition"
                title="Ouvir versão nativa"
              >
                🔊
              </button>
            </div>
            <p class="text-xs text-emerald-200 font-mono font-semibold">
              "{{ evaluationFeedback.block3_active_evaluation.natural_native_version }}"
            </p>
          </div>
        </div>

        <!-- Explicação Rápida de 2 Linhas -->
        <div class="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 flex items-start space-x-3">
          <span class="text-lg">💡</span>
          <div>
            <span class="text-[10px] font-mono uppercase text-indigo-400 font-bold block">Por que um nativo fala assim:</span>
            <p class="text-xs text-slate-200 leading-relaxed mt-0.5">
              {{ evaluationFeedback.block3_active_evaluation.micro_explanation }}
            </p>
          </div>
        </div>
      </div>

      <!-- Novas Palavras Salvas no Cofre de Repetição Espaçada -->
      <div v-if="evaluationFeedback.new_words_to_vault?.length" class="space-y-3 pt-2">
        <h4 class="text-xs font-mono font-bold uppercase text-amber-400 flex items-center space-x-2">
          <span>📦</span>
          <span>Adicionado ao Cofre de Repetição Espaçada (SRS):</span>
        </h4>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="(word, idx) in evaluationFeedback.new_words_to_vault"
            :key="idx"
            class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition space-y-1"
          >
            <span class="font-bold text-sm text-white block">{{ word.term_or_phrase }}</span>
            <span class="text-xs text-emerald-400 block">{{ word.translation }}</span>
            <span v-if="word.context_example" class="text-[11px] text-slate-400 italic block line-clamp-1">
              "{{ word.context_example }}"
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTEÚDO DOS 3 BLOCOS (Durante o treino) -->
    <div v-else class="space-y-6">
      <!-- BLOCO 1: Aquecimento & Repetição Espaçada (SRS) -->
      <div v-if="activeBlock === 1 && block1" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div class="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <span class="text-[11px] font-mono uppercase font-bold text-emerald-400">Bloco 1 (Minutos 0 a 5)</span>
            <h3 class="text-base font-bold text-white">{{ block1.title }}</h3>
            <p class="text-xs text-slate-400 mt-0.5">{{ block1.instructions || 'Revisão rápida de termos essenciais e repetição espaçada.' }}</p>
          </div>
          <span class="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ~3 a 5 min
          </span>
        </div>

        <div class="space-y-6">
          <div
            v-for="(item, itemIndex) in block1.items"
            :key="item.id || itemIndex"
            class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="text-xs font-mono font-bold text-slate-400">Termo em Foco: <strong class="text-white">{{ item.term }}</strong></span>
                <button
                  type="button"
                  @click="speakText(item.context_sentence || item.term)"
                  class="w-6 h-6 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-xs transition"
                  title="Ouvir pronúncia"
                >
                  🔊
                </button>
              </div>
              <span v-if="item.context_sentence" class="text-xs text-slate-400 italic hidden sm:inline">{{ item.context_sentence }}</span>
            </div>

            <p class="text-xs font-bold text-slate-200">{{ item.prompt }}</p>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                v-for="(option, optIndex) in item.options"
                :key="optIndex"
                type="button"
                @click="block1Answers[item.id || itemIndex] = option"
                class="p-3 rounded-xl border text-left text-xs transition flex items-center justify-between"
                :class="block1Answers[item.id || itemIndex] === option
                  ? 'border-emerald-500 bg-emerald-500/10 text-white font-bold'
                  : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700'"
              >
                <span>{{ option }}</span>
                <span v-if="block1Answers[item.id || itemIndex] === option" class="text-emerald-400 font-bold">✓</span>
              </button>
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <button
            type="button"
            @click="activeBlock = 2"
            class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md transition flex items-center space-x-2"
          >
            <span>Avançar para Bloco 2: Imersão Prática</span>
            <span>→</span>
          </button>
        </div>
      </div>

      <!-- BLOCO 2: Imersão Prática & Contexto -->
      <div v-if="activeBlock === 2 && block2" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div class="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <span class="text-[11px] font-mono uppercase font-bold text-indigo-400">Bloco 2 (Minutos 5 a 10)</span>
            <h3 class="text-base font-bold text-white">{{ block2.title }}</h3>
            <p class="text-xs text-slate-400 mt-0.5">Micro-diálogo contextualizado no seu foco profissional.</p>
          </div>
          <span class="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            ~5 min
          </span>
        </div>

        <!-- Texto / Micro-diálogo (máx 120 palavras) -->
        <div class="p-5 rounded-2xl bg-gradient-to-br from-slate-950 to-slate-900 border border-slate-800 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2 text-xs font-mono font-bold text-indigo-300">
              <span>📖</span>
              <span>{{ block2.scenario_title || 'Cenário Executivo' }}</span>
            </div>
            <button
              type="button"
              @click="speakText(block2.scenario_text)"
              class="px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-mono flex items-center space-x-1.5 transition"
              title="Ouvir diálogo completo"
            >
              <span>🔊</span>
              <span>Ouvir Diálogo</span>
            </button>
          </div>
          <p class="text-xs text-slate-200 leading-relaxed font-serif whitespace-pre-line">
            {{ block2.scenario_text }}
          </p>
        </div>

        <!-- Questões de Compreensão -->
        <div class="space-y-5">
          <div
            v-for="(question, qIndex) in block2.questions"
            :key="question.id || qIndex"
            class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3"
          >
            <h4 class="text-xs font-bold text-white">{{ qIndex + 1 }}. {{ question.question }}</h4>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                v-for="(option, optIndex) in question.options"
                :key="optIndex"
                type="button"
                @click="block2Answers[question.id || qIndex] = option"
                class="p-3 rounded-xl border text-left text-xs transition flex items-center justify-between"
                :class="block2Answers[question.id || qIndex] === option
                  ? 'border-indigo-500 bg-indigo-500/10 text-white font-bold'
                  : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700'"
              >
                <span>{{ option }}</span>
                <span v-if="block2Answers[question.id || qIndex] === option" class="text-indigo-400 font-bold">✓</span>
              </button>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2">
          <button
            type="button"
            @click="activeBlock = 1"
            class="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white"
          >
            ← Bloco 1
          </button>
          <button
            type="button"
            @click="activeBlock = 3"
            class="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs shadow-md transition flex items-center space-x-2"
          >
            <span>Avançar para Bloco 3: Desafio Ativo</span>
            <span>→</span>
          </button>
        </div>
      </div>

      <!-- BLOCO 3: Desafio Ativo de Produção (Output) -->
      <div v-if="activeBlock === 3 && block3" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div class="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <span class="text-[11px] font-mono uppercase font-bold text-amber-400">Bloco 3 (Minutos 10 a 15)</span>
            <h3 class="text-base font-bold text-white">{{ block3.title }}</h3>
            <p class="text-xs text-slate-400 mt-0.5">Produza uma resposta real no idioma para correção do Gemini 3.8 Flash.</p>
          </div>
          <span class="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            ~5 min
          </span>
        </div>

        <!-- Situação / Prompt da Produção Ativa -->
        <div class="p-5 rounded-2xl bg-gradient-to-br from-amber-950/20 via-slate-950 to-slate-900 border border-amber-500/30 space-y-3">
          <div class="flex items-center space-x-2 text-xs font-mono font-bold text-amber-400">
            <span>⚡</span>
            <span>Desafio Prático do Dia</span>
          </div>
          <p class="text-xs text-slate-200 leading-relaxed font-semibold">
            {{ block3.scenario_prompt }}
          </p>

          <div v-if="block3.required_elements?.length" class="space-y-1 pt-1">
            <span class="text-[10px] font-mono uppercase text-slate-400 font-bold block">Elementos Recomendados:</span>
            <ul class="text-[11px] text-slate-300 list-disc list-inside space-y-0.5">
              <li v-for="(elem, eIdx) in block3.required_elements" :key="eIdx">{{ elem }}</li>
            </ul>
          </div>
        </div>

        <!-- Área de Escrita / Input do Usuário -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs font-mono">
            <label class="font-bold text-slate-300">Sua Resposta no Idioma (2 a 4 frases):</label>
            <span class="text-slate-400">{{ block3Input.length }} caracteres</span>
          </div>

          <textarea
            v-model="block3Input"
            rows="4"
            class="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl p-4 text-xs text-white placeholder-slate-600 focus:outline-none transition leading-relaxed"
            placeholder="Digite aqui em inglês/idioma alvo..."
          ></textarea>
        </div>

        <!-- Botão de Finalização da Sessão -->
        <div class="flex items-center justify-between pt-2">
          <button
            type="button"
            @click="activeBlock = 2"
            class="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white"
          >
            ← Bloco 2
          </button>

          <button
            type="button"
            :disabled="!canSubmitSession || languageStore.actionLoading"
            @click="handleFinishLesson"
            class="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 disabled:opacity-50 text-white font-black text-xs shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
          >
            <svg v-if="languageStore.actionLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
            <span>Submeter Sessão para o Gemini 3.8 Flash</span>
            <span>🔥</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
