<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'
import AppLayout from '@/components/AppLayout.vue'
import LanguageHeader from '@/components/LanguageHeader.vue'
import LanguageOnboardingModal from '@/components/LanguageOnboardingModal.vue'
import LanguagePlacementTestModal from '@/components/LanguagePlacementTestModal.vue'
import LanguageFocusPlayer from '@/components/LanguageFocusPlayer.vue'
import VocabularyVaultTab from '@/components/VocabularyVaultTab.vue'

const languageStore = useLanguageStore()
const swal = useSwal()

const activeTab = ref('daily_lesson') // daily_lesson, vault, diagnosis
const showOnboardingModal = ref(false)
const showPlacementModal = ref(false)

onMounted(async () => {
  try {
    await languageStore.fetchProfile()

    if (!languageStore.hasProfile) {
      showOnboardingModal.value = true
    } else if (languageStore.isPlacementNeeded) {
      showPlacementModal.value = true
    } else {
      await languageStore.fetchTodaySession()
    }
  } catch (err) {
    console.error('Erro ao inicializar academia de idiomas:', err)
  }
})

const profile = computed(() => languageStore.profile)
const currentSession = computed(() => languageStore.currentSession)

const isSessionCompletedToday = computed(() => {
  return currentSession.value?.status === 'completed'
})

async function handleOnboardingCompleted() {
  showOnboardingModal.value = false
  await languageStore.fetchProfile()
  showPlacementModal.value = true
}

async function handlePlacementCompleted() {
  showPlacementModal.value = false
  await languageStore.fetchProfile()
  await languageStore.fetchTodaySession()
}

async function handleRetakePlacement() {
  const proceed = await swal.confirm({
    title: 'Refazer Nivelamento Diagnóstico?',
    text: 'O Gemini 3.8 Flash gerará um novo teste adaptativo para atualizar seu nível CEFR oficial.',
    confirmText: 'Sim, iniciar teste',
  })

  if (proceed) {
    languageStore.placementTest = null
    showPlacementModal.value = true
  }
}

async function handleStartNewTrainingSession() {
  await languageStore.fetchTodaySession()
}
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <!-- Loading Inicial -->
      <div v-if="languageStore.loading && !profile" class="p-16 text-center space-y-3">
        <div class="w-10 h-10 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mx-auto"></div>
        <p class="text-xs font-mono text-slate-400">Carregando Academia de Idiomas...</p>
      </div>

      <template v-else>
        <!-- Header de Gamificação, Ofensiva e Agenda Google/Apple -->
        <LanguageHeader v-if="profile" />

        <!-- Navegação por Abas -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div class="flex items-center space-x-2">
            <button
              type="button"
              @click="activeTab = 'daily_lesson'"
              class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2"
              :class="activeTab === 'daily_lesson'
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            >
              <span>⏱️ Treino de 15 Minutos</span>
              <span
                v-if="isSessionCompletedToday"
                class="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-mono"
              >
                Feito hoje
              </span>
            </button>

            <button
              type="button"
              @click="activeTab = 'vault'"
              class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2"
              :class="activeTab === 'vault'
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            >
              <span>📦 Cofre SRS</span>
              <span
                v-if="languageStore.stats?.due_reviews_count > 0"
                class="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/20 text-amber-300 font-mono font-bold"
              >
                {{ languageStore.stats.due_reviews_count }} pendentes
              </span>
            </button>

            <button
              type="button"
              @click="activeTab = 'diagnosis'"
              class="px-4 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-2"
              :class="activeTab === 'diagnosis'
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'"
            >
              <span>🎯 Diagnóstico & CEFR</span>
            </button>
          </div>

          <!-- Botão para Configurar Outro Idioma / Onboarding -->
          <button
            type="button"
            @click="showOnboardingModal = true"
            class="text-xs font-mono text-slate-400 hover:text-emerald-400 transition flex items-center space-x-1"
          >
            <span>+ Trocar Idioma / Rotina</span>
          </button>
        </div>

        <!-- ABA 1: Treino Diário de 15 Minutos -->
        <div v-if="activeTab === 'daily_lesson'">
          <!-- Se a lição já foi concluída hoje -->
          <div
            v-if="isSessionCompletedToday"
            class="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-4 shadow-xl"
          >
            <div class="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-3xl mx-auto shadow-inner">
              🔥
            </div>
            <div class="space-y-1">
              <span class="text-xs font-mono uppercase tracking-widest text-emerald-400 font-bold">Ofensiva Mantida!</span>
              <h3 class="text-xl font-bold text-white">Você já concluiu sua sessão de 15 minutos hoje!</h3>
              <p class="text-xs text-slate-400 max-w-md mx-auto">
                Sua constância é a chave da fluência funcional. Seu próximo micro-learning está agendado na sua agenda para amanhã às
                <strong class="text-white">{{ profile?.preferred_time }}</strong>.
              </p>
            </div>

            <div class="pt-4 flex items-center justify-center space-x-3">
              <button
                type="button"
                @click="activeTab = 'vault'"
                class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition"
              >
                Revisar Palavras no Cofre
              </button>
            </div>
          </div>

          <!-- Se o Nivelamento Diagnóstico ainda estiver pendente -->
          <div
            v-else-if="languageStore.isPlacementNeeded"
            class="bg-slate-900 border border-indigo-500/30 rounded-2xl p-8 text-center space-y-5 shadow-2xl relative overflow-hidden"
          >
            <div class="absolute -top-10 -right-10 w-48 h-48 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none"></div>
            <div class="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-3xl mx-auto shadow-inner text-white">
              🎯
            </div>
            <div class="space-y-2 max-w-lg mx-auto">
              <span class="text-xs font-mono uppercase tracking-widest text-indigo-400 font-bold">Nivelamento Diagnóstico Pendente</span>
              <h3 class="text-xl font-bold text-white">Calibre seu Nível CEFR Oficial</h3>
              <p class="text-xs text-slate-300 leading-relaxed">
                Para liberar seus 3 blocos diários de 15 minutos adaptados à sua rotina, complete o teste diagnóstico rápido (10 questões de A1 a C1).
              </p>
            </div>
            <div>
              <button
                type="button"
                @click="showPlacementModal = true"
                class="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-black text-xs shadow-lg shadow-emerald-500/20 transition flex items-center space-x-2 mx-auto"
              >
                <span>Fazer Teste de Nivelamento Agora (10 Questões)</span>
                <span>→</span>
              </button>
            </div>
          </div>

          <!-- Player Focado dos 3 Blocos de 15 Minutos -->
          <LanguageFocusPlayer
            v-else-if="currentSession"
            @completed="handleStartNewTrainingSession"
          />

          <!-- Loading da Sessão Diária com Botão de Recarregar -->
          <div v-else class="p-16 text-center space-y-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div class="w-10 h-10 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin mx-auto"></div>
            <p class="text-xs font-mono text-slate-400">Preparando seus 3 blocos dinâmicos com Gemini 3.8 Flash...</p>
            <button
              type="button"
              @click="handleStartNewTrainingSession"
              class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition inline-flex items-center space-x-1.5"
            >
              <span>Recarregar Sessão</span>
            </button>
          </div>
        </div>

        <!-- ABA 2: Cofre de Vocabulário & Repetição Espaçada -->
        <div v-if="activeTab === 'vault'">
          <VocabularyVaultTab />
        </div>

        <!-- ABA 3: Diagnóstico CEFR & Fraquezas -->
        <div v-if="activeTab === 'diagnosis'" class="space-y-6">
          <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <span class="text-xs font-mono uppercase font-bold text-indigo-400">Classificação Padrão Europeu (CEFR)</span>
                <h3 class="text-xl font-bold text-white">Nível Atual: {{ profile?.cefr_level }}</h3>
                <p class="text-xs text-slate-400 mt-0.5">Diagnóstico gerado a partir do seu teste de nivelamento adaptativo.</p>
              </div>

              <button
                type="button"
                @click="handleRetakePlacement"
                class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition flex items-center space-x-1.5 self-start sm:self-auto"
              >
                <span>🔄 Refazer Nivelamento</span>
              </button>
            </div>

            <!-- Resumo Executivo -->
            <div v-if="profile?.weaknesses_diagnosis?.executive_summary" class="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
              {{ profile.weaknesses_diagnosis.executive_summary }}
            </div>

            <!-- Pontos Cegos Críticos -->
            <div class="space-y-3">
              <h4 class="text-xs font-mono uppercase font-bold text-amber-400 flex items-center space-x-2">
                <span>⚠️</span>
                <span>Pontos Cegos Monitorados pelo Gemini 3.8 Flash:</span>
              </h4>

              <div
                v-if="profile?.weaknesses_diagnosis?.blind_spots?.length"
                class="grid grid-cols-1 sm:grid-cols-2 gap-3"
              >
                <div
                  v-for="(spot, idx) in profile.weaknesses_diagnosis.blind_spots"
                  :key="idx"
                  class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-start space-x-2.5"
                >
                  <span class="font-bold text-amber-400 font-mono">•</span>
                  <span class="leading-relaxed">{{ spot }}</span>
                </div>
              </div>

              <p v-else class="text-xs text-slate-500 italic">
                Nenhum ponto cego crítico detectado até o momento.
              </p>
            </div>

            <!-- Pontos Fortes -->
            <div v-if="profile?.weaknesses_diagnosis?.strengths?.length" class="space-y-3">
              <h4 class="text-xs font-mono uppercase font-bold text-emerald-400 flex items-center space-x-2">
                <span>✓</span>
                <span>Pontos Fortes Demonstrados:</span>
              </h4>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div
                  v-for="(str, idx) in profile.weaknesses_diagnosis.strengths"
                  :key="idx"
                  class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-200 flex items-start space-x-2.5"
                >
                  <span class="font-bold text-emerald-400 font-mono">✓</span>
                  <span class="leading-relaxed">{{ str }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Modal de Onboarding (Setup Inicial) -->
      <LanguageOnboardingModal
        v-if="showOnboardingModal"
        @completed="handleOnboardingCompleted"
        @close="showOnboardingModal = false"
      />

      <!-- Modal de Nivelamento Diagnóstico (Placement Test) -->
      <LanguagePlacementTestModal
        v-if="showPlacementModal"
        @completed="handlePlacementCompleted"
        @close="showPlacementModal = false"
      />
    </div>
  </AppLayout>
</template>
