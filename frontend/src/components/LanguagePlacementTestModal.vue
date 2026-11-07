<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'

const emit = defineEmits(['completed', 'close'])

const languageStore = useLanguageStore()
const swal = useSwal()

const currentQuestionIndex = ref(0)
const userAnswers = ref({})
const evaluationResult = ref(null)

onMounted(async () => {
  if (!languageStore.placementTest) {
    try {
      await languageStore.fetchPlacementTest()
    } catch (err) {
      swal.error('Erro ao gerar teste', err.response?.data?.message || 'Falha ao conectar com o Gemini 3.8 Flash.')
    }
  }
})

const test = computed(() => languageStore.placementTest)
const questions = computed(() => test.value?.questions || [])
const currentQuestion = computed(() => questions.value[currentQuestionIndex.value] || null)

const isAnswerSelected = computed(() => {
  return currentQuestion.value && userAnswers.value[currentQuestion.value.id] !== undefined
})

const isLastQuestion = computed(() => {
  return currentQuestionIndex.value === questions.value.length - 1
})

const answeredCount = computed(() => {
  return Object.keys(userAnswers.value).length
})

function selectOption(option) {
  if (!currentQuestion.value) return
  userAnswers.value[currentQuestion.value.id] = option
}

function nextQuestion() {
  if (currentQuestionIndex.value < questions.value.length - 1) {
    currentQuestionIndex.value++
  }
}

function prevQuestion() {
  if (currentQuestionIndex.value > 0) {
    currentQuestionIndex.value--
  }
}

async function handleSubmitTest() {
  if (answeredCount.value < questions.value.length) {
    const proceed = await swal.confirm({
      title: 'Questões não respondidas',
      text: 'Você ainda não respondeu todas as perguntas do teste de nivelamento. Deseja enviar assim mesmo?',
      confirmText: 'Sim, diagnosticar agora',
    })
    if (!proceed) return
  }

  try {
    const formattedAnswers = Object.entries(userAnswers.value).map(([questionId, answer]) => ({
      question_id: parseInt(questionId, 10),
      answer,
    }))

    const response = await languageStore.submitPlacementTest({
      questions: questions.value,
      answers: formattedAnswers,
    })

    evaluationResult.value = response.evaluation

    swal.toast(`Diagnóstico concluído! Nível CEFR definido: ${response.evaluation.cefr_level}`, 'success')
  } catch (err) {
    swal.error('Erro ao avaliar nivelamento', err.response?.data?.message || 'Falha ao processar avaliação.')
  }
}

function finishAndStartLessons() {
  emit('completed')
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Header do Modal -->
      <div class="p-5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center text-white font-bold text-lg shadow-md shadow-indigo-500/20">
            🎯
          </div>
          <div>
            <h3 class="font-bold text-white text-base">Teste de Nivelamento Adaptativo</h3>
            <span class="text-xs text-slate-400 font-mono">
              Classificação CEFR Oficial (A1 a C1) com Gemini 3.8 Flash
            </span>
          </div>
        </div>

        <span
          v-if="!evaluationResult && questions.length > 0"
          class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700"
        >
          Questão {{ currentQuestionIndex + 1 }} de {{ questions.length }}
        </span>
      </div>

      <!-- Barra de Progresso Superior -->
      <div v-if="!evaluationResult && questions.length > 0" class="w-full bg-slate-800 h-1.5">
        <div
          class="bg-gradient-to-r from-emerald-500 to-indigo-500 h-full transition-all duration-300"
          :style="{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }"
        ></div>
      </div>

      <!-- Loading ao Gerar Teste -->
      <div v-if="languageStore.sessionLoading" class="p-12 text-center space-y-4">
        <div class="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mx-auto"></div>
        <h4 class="font-bold text-white text-sm">O Gemini 3.8 Flash está gerando seus desafios adaptativos...</h4>
        <p class="text-xs text-slate-400">Criando questões personalizadas para o seu idioma e foco.</p>
      </div>

      <!-- TELA DE RESULTADO / DIAGNÓSTICO (Após Submissão) -->
      <div v-else-if="evaluationResult" class="p-6 overflow-y-auto space-y-6 flex-1">
        <div class="text-center space-y-2 p-6 rounded-2xl bg-gradient-to-b from-indigo-950/40 to-slate-900 border border-indigo-500/30">
          <span class="text-xs font-mono uppercase tracking-widest text-indigo-400 font-bold">Diagnóstico Concluído</span>
          <div class="flex items-center justify-center space-x-3">
            <span class="text-4xl font-black text-white font-mono">Nível</span>
            <span class="text-4xl font-black px-4 py-1 rounded-2xl bg-emerald-500 text-slate-950 font-mono shadow-lg shadow-emerald-500/30">
              {{ evaluationResult.cefr_level }}
            </span>
          </div>
          <p class="text-xs text-slate-300 max-w-md mx-auto pt-2 leading-relaxed">
            {{ evaluationResult.executive_summary }}
          </p>
        </div>

        <!-- Pontos Cegos & Fraquezas Detectadas -->
        <div class="space-y-3">
          <h4 class="text-xs font-mono uppercase font-bold text-amber-400 flex items-center space-x-2">
            <span>⚠️</span>
            <span>Pontos Cegos Identificados (Foco dos Micro-Treinos):</span>
          </h4>
          <div class="grid grid-cols-1 gap-2">
            <div
              v-for="(blindSpot, idx) in evaluationResult.blind_spots"
              :key="idx"
              class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-start space-x-2.5"
            >
              <span class="font-mono font-bold text-amber-400">•</span>
              <span>{{ blindSpot }}</span>
            </div>
          </div>
        </div>

        <!-- Plano de Ação Recomendado -->
        <div v-if="evaluationResult.recommended_study_plan" class="p-4 rounded-xl bg-slate-800/60 border border-slate-700 space-y-1">
          <span class="text-[11px] font-mono text-slate-400 uppercase font-bold">Plano de Micro-Learning:</span>
          <p class="text-xs text-slate-300 leading-relaxed">{{ evaluationResult.recommended_study_plan }}</p>
        </div>
      </div>

      <!-- CORPO DAS QUESTÕES (Durante o teste) -->
      <div v-else-if="currentQuestion" class="p-6 overflow-y-auto space-y-5 flex-1">
        <!-- Target CEFR Badge -->
        <div class="flex items-center justify-between">
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Nível Alvo do Desafio: {{ currentQuestion.target_cefr }}
          </span>
          <span v-if="currentQuestion.scenario" class="text-xs text-slate-400 italic">
            Cenário Prático
          </span>
        </div>

        <!-- Cenário ou Contexto -->
        <div v-if="currentQuestion.scenario" class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 font-serif leading-relaxed">
          {{ currentQuestion.scenario }}
        </div>

        <!-- Pergunta -->
        <h4 class="text-sm font-bold text-white leading-relaxed">
          {{ currentQuestion.question }}
        </h4>

        <!-- Opções -->
        <div class="space-y-2.5">
          <button
            v-for="(option, idx) in currentQuestion.options"
            :key="idx"
            type="button"
            @click="selectOption(option)"
            class="w-full p-3.5 rounded-xl border text-left text-xs transition flex items-center justify-between group"
            :class="userAnswers[currentQuestion.id] === option
              ? 'border-emerald-500 bg-emerald-500/10 text-white font-semibold shadow-md shadow-emerald-500/10'
              : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-800/60'"
          >
            <div class="flex items-center space-x-3">
              <span
                class="w-6 h-6 rounded-lg font-mono text-[11px] font-bold flex items-center justify-center transition"
                :class="userAnswers[currentQuestion.id] === option ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400'"
              >
                {{ String.fromCharCode(65 + idx) }}
              </span>
              <span>{{ option }}</span>
            </div>
            <span
              v-if="userAnswers[currentQuestion.id] === option"
              class="text-emerald-400 text-sm font-bold"
            >
              ✓
            </span>
          </button>
        </div>
      </div>

      <!-- Rodapé de Ações -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <template v-if="evaluationResult">
          <div></div>
          <button
            type="button"
            @click="finishAndStartLessons"
            class="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
          >
            <span>Iniciar Sessão Diária de 15 Minutos</span>
            <span>🔥</span>
          </button>
        </template>

        <template v-else-if="questions.length > 0">
          <button
            type="button"
            :disabled="currentQuestionIndex === 0"
            @click="prevQuestion"
            class="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white disabled:opacity-30 transition"
          >
            ← Anterior
          </button>

          <button
            v-if="!isLastQuestion"
            type="button"
            @click="nextQuestion"
            class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md shadow-indigo-600/20 transition flex items-center space-x-1"
          >
            <span>Próxima</span>
            <span>→</span>
          </button>

          <button
            v-else
            type="button"
            :disabled="languageStore.actionLoading"
            @click="handleSubmitTest"
            class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
          >
            <svg v-if="languageStore.actionLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
            <span>Finalizar Diagnóstico com Gemini 3.8 Flash</span>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
