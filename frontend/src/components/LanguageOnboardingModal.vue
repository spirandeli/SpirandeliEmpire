<script setup>
import { ref, computed } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'

const emit = defineEmits(['completed', 'close'])

const languageStore = useLanguageStore()
const swal = useSwal()

const currentStep = ref(1)

const targetLanguage = ref('Inglês')
const learningFocus = ref('business')
const studyDays = ref(['MON', 'TUE', 'WED', 'THU', 'FRI'])
const preferredTime = ref('07:30')
const dailyDuration = ref(15)

const languages = [
  { id: 'Inglês', name: 'Inglês', flag: '🇺🇸', description: 'Global business, tech e liderança internacional' },
  { id: 'Espanhol', name: 'Espanhol', flag: '🇪🇸', description: 'América Latina e expansão de mercado hispânico' },
  { id: 'Mandarim', name: 'Mandarim', flag: '🇨🇳', description: 'Supply chain global, importações e comércio chinês' },
  { id: 'Francês', name: 'Francês', flag: '🇫🇷', description: 'Relações diplomáticas, luxo e mercado europeu' },
  { id: 'Alemão', name: 'Alemão', flag: '🇩🇪', description: 'Engenharia, indústria e polo tecnológico europeu' },
  { id: 'Italiano', name: 'Italiano', flag: '🇮🇹', description: 'Design, alta gastronomia e moda corporativa' },
]

const focusOptions = [
  { id: 'business', title: 'Negócios & Reuniões Executivas', icon: '💼', desc: 'Pitches, negociações, calls com parceiros e e-mails corporativos' },
  { id: 'dev', title: 'Tecnologia & Leitura Técnica Dev', icon: '💻', desc: 'Documentações, arquitetura de software, pull requests e code reviews' },
  { id: 'general', title: 'Conversação Geral & Fluência Diária', icon: '🗣️', desc: 'Diálogos naturais, networking descontraído e vocabulário cotidiano' },
  { id: 'travel', title: 'Viagens & Vivência Internacional', icon: '✈️', desc: 'Aeroportos, imigração, reservas e situações emergenciais no exterior' },
]

const daysOfWeek = [
  { id: 'MON', label: 'Seg' },
  { id: 'TUE', label: 'Ter' },
  { id: 'WED', label: 'Qua' },
  { id: 'THU', label: 'Qui' },
  { id: 'FRI', label: 'Sex' },
  { id: 'SAT', label: 'Sáb' },
  { id: 'SUN', label: 'Dom' },
]

const timePresets = ['07:00', '07:30', '08:00', '12:30', '18:30', '19:00', '21:00']

function toggleDay(dayId) {
  const index = studyDays.value.indexOf(dayId)
  if (index > -1) {
    if (studyDays.value.length > 1) {
      studyDays.value.splice(index, 1)
    }
  } else {
    studyDays.value.push(dayId)
  }
}

function selectAllDays() {
  studyDays.value = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
}

function selectWeekdays() {
  studyDays.value = ['MON', 'TUE', 'WED', 'THU', 'FRI']
}

const canAdvanceStep1 = computed(() => !!targetLanguage.value && !!learningFocus.value)
const canAdvanceStep2 = computed(() => studyDays.value.length > 0 && !!preferredTime.value)

async function handleFinish() {
  try {
    await languageStore.createProfile({
      target_language: targetLanguage.value,
      learning_focus: learningFocus.value,
      study_days: studyDays.value,
      preferred_time: preferredTime.value,
      daily_duration_minutes: dailyDuration.value,
    })

    swal.toast('Rotina criada e sincronizada com Google & Apple Calendar!', 'success')
    emit('completed')
  } catch (err) {
    swal.error('Erro ao salvar configuração', err.response?.data?.message || 'Falha na comunicação com o servidor.')
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Header do Wizard -->
      <div class="p-6 border-b border-slate-800 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/40 flex items-center justify-between">
        <div>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-1">
            ⚡ Powered by Gemini 3.8 Flash
          </span>
          <h2 class="text-xl font-bold text-white tracking-tight">Onboarding: Academia de Idiomas</h2>
          <p class="text-xs text-slate-400">Micro-learning diário de 15 minutos adaptativo à sua agenda executiva</p>
        </div>

        <!-- Indicador de Passos -->
        <div class="flex items-center space-x-2">
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition"
            :class="currentStep === 1 ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' : 'bg-slate-800 text-slate-400'"
          >
            1
          </div>
          <div class="w-6 h-0.5 bg-slate-800"></div>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs transition"
            :class="currentStep === 2 ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' : 'bg-slate-800 text-slate-400'"
          >
            2
          </div>
        </div>
      </div>

      <!-- Corpo com Rolagem -->
      <div class="p-6 overflow-y-auto space-y-6 flex-1">
        <!-- PASSO 1: Idioma e Foco -->
        <div v-if="currentStep === 1" class="space-y-6">
          <div>
            <label class="block text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-3">
              1. Qual idioma você deseja dominar com o Gemini 3.8 Flash?
            </label>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <button
                v-for="lang in languages"
                :key="lang.id"
                type="button"
                @click="targetLanguage = lang.id"
                class="p-3 rounded-xl border text-left transition flex flex-col justify-between"
                :class="targetLanguage === lang.id
                  ? 'border-emerald-500 bg-emerald-500/10 text-white shadow-md shadow-emerald-500/10'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'"
              >
                <div class="flex items-center space-x-2">
                  <span class="text-2xl">{{ lang.flag }}</span>
                  <span class="font-bold text-sm text-slate-100">{{ lang.name }}</span>
                </div>
                <span class="text-[11px] text-slate-400 mt-2 line-clamp-2">{{ lang.description }}</span>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-3">
              2. Qual o seu foco de aprendizado principal?
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                v-for="focus in focusOptions"
                :key="focus.id"
                type="button"
                @click="learningFocus = focus.id"
                class="p-4 rounded-xl border text-left transition flex items-start space-x-3"
                :class="learningFocus === focus.id
                  ? 'border-emerald-500 bg-emerald-500/10 text-white shadow-md shadow-emerald-500/10'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'"
              >
                <span class="text-2xl p-2 rounded-lg bg-slate-800/80">{{ focus.icon }}</span>
                <div>
                  <h4 class="font-bold text-sm text-slate-100">{{ focus.title }}</h4>
                  <p class="text-xs text-slate-400 mt-1 leading-relaxed">{{ focus.desc }}</p>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- PASSO 2: Constância, Horário e Sincronização de Calendário -->
        <div v-else class="space-y-6">
          <div>
            <div class="flex items-center justify-between mb-3">
              <label class="block text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                1. Dias de Constância na Semana
              </label>
              <div class="space-x-2 text-xs">
                <button type="button" @click="selectWeekdays" class="text-emerald-400 hover:underline">Dias Úteis</button>
                <span class="text-slate-600">•</span>
                <button type="button" @click="selectAllDays" class="text-indigo-400 hover:underline">Todos os Dias</button>
              </div>
            </div>

            <div class="grid grid-cols-7 gap-2">
              <button
                v-for="day in daysOfWeek"
                :key="day.id"
                type="button"
                @click="toggleDay(day.id)"
                class="py-3 rounded-xl border font-bold text-xs transition text-center"
                :class="studyDays.includes(day.id)
                  ? 'border-emerald-500 bg-emerald-500 text-slate-950 font-black shadow-lg shadow-emerald-500/20'
                  : 'border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'"
              >
                {{ day.label }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-xs font-mono font-bold text-slate-300 uppercase tracking-wider mb-2">
              2. Horário da Sessão de 15 Minutos
            </label>
            <div class="flex items-center space-x-3 mb-3">
              <input
                v-model="preferredTime"
                type="time"
                class="bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-white font-mono text-sm focus:border-emerald-500 focus:outline-none"
              />
              <span class="text-xs text-slate-400">Duração: <strong class="text-emerald-400">15 minutos</strong> cronometrados</span>
            </div>

            <div class="flex flex-wrap gap-2">
              <button
                v-for="preset in timePresets"
                :key="preset"
                type="button"
                @click="preferredTime = preset"
                class="px-3 py-1.5 rounded-lg border text-xs font-mono transition"
                :class="preferredTime === preset
                  ? 'border-indigo-500 bg-indigo-500/20 text-indigo-300'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200'"
              >
                {{ preset }}
              </button>
            </div>
          </div>

          <!-- Card de Integração com Google & Apple -->
          <div class="p-4 rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/30 to-slate-900 text-slate-300 space-y-2">
            <div class="flex items-center space-x-2 text-indigo-400 font-bold text-xs">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
              <span>Sincronização Automática com Google & Apple iCloud</span>
            </div>
            <p class="text-xs text-slate-400 leading-relaxed">
              O backend agendará os eventos recorrentes (<code class="text-emerald-400 text-[11px]">RRULE:FREQ=WEEKLY</code>) na sua agenda com link direto para a sessão diária e alerta disparado 10 minutos antes.
            </p>
          </div>
        </div>
      </div>

      <!-- Rodapé de Ações -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <button
          v-if="currentStep === 2"
          type="button"
          @click="currentStep = 1"
          class="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800/80 transition"
        >
          ← Voltar
        </button>
        <div v-else></div>

        <button
          v-if="currentStep === 1"
          type="button"
          :disabled="!canAdvanceStep1"
          @click="currentStep = 2"
          class="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
        >
          <span>Avançar para Horários</span>
          <span>→</span>
        </button>

        <button
          v-else
          type="button"
          :disabled="!canAdvanceStep2 || languageStore.actionLoading"
          @click="handleFinish"
          class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 transition flex items-center space-x-2"
        >
          <svg v-if="languageStore.actionLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
          <span>Salvar Rotina e Iniciar Teste Diagnóstico</span>
        </button>
      </div>
    </div>
  </div>
</template>
