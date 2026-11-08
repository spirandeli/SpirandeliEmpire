<script setup>
import { computed } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'

const languageStore = useLanguageStore()
const swal = useSwal()

const profile = computed(() => languageStore.profile)
const stats = computed(() => languageStore.stats)

const flagMap = {
  Inglês: '🇺🇸',
  Espanhol: '🇪🇸',
  Mandarim: '🇨🇳',
  Francês: '🇫🇷',
  Alemão: '🇩🇪',
  Italiano: '🇮🇹',
}

const currentFlag = computed(() => flagMap[profile.value?.target_language] || '🌐')

const cefrColors = {
  UNSET: 'bg-slate-700 text-slate-300',
  A1: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
  A2: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  B1: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  B2: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  C1: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  C2: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
}

const nextCefrLevel = computed(() => {
  const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
  const current = profile.value?.cefr_level
  const index = levels.indexOf(current)
  if (index === -1) return 'A1'
  return levels[index + 1] || 'C2 Master'
})

const daysFormatted = computed(() => {
  const days = profile.value?.study_days || []
  if (days.includes('ALL') || days.length === 7) return 'Todos os dias'
  const map = {
    MON: 'Seg', TUE: 'Ter', WED: 'Qua', THU: 'Qui', FRI: 'Sex', SAT: 'Sáb', SUN: 'Dom',
    1: 'Seg', 2: 'Ter', 3: 'Qua', 4: 'Qui', 5: 'Sex', 6: 'Sáb', 7: 'Dom',
    '1': 'Seg', '2': 'Ter', '3': 'Qua', '4': 'Qui', '5': 'Sex', '6': 'Sáb', '7': 'Dom',
  }
  return days.map((d) => map[d] || d).join(', ')
})

function isDaySelected(dayCode, dayInt) {
  const days = profile.value?.study_days || []
  return days.includes(dayCode) || days.includes(dayInt) || days.includes(String(dayInt))
}

async function openScheduleEditModal() {
  if (!profile.value) return

  const currentTime = profile.value.preferred_time || '07:30'

  const { value: formValues } = await swal.instance.fire({
    title: 'Ajustar Rotina & Agendas',
    html: `
      <div class="text-left text-xs text-slate-300 space-y-4 font-sans">
        <div>
          <label class="block font-bold text-slate-200 mb-1">Horário da Sessão (15 min):</label>
          <input id="swal-time" type="time" class="swal2-input !bg-slate-900 !text-white !border-slate-700 !rounded-xl !text-sm !w-full !m-0" value="${currentTime}">
        </div>
        <div>
          <label class="block font-bold text-slate-200 mb-1">Dias de Estudo:</label>
          <div class="grid grid-cols-4 gap-2 text-center text-xs">
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="MON" ${isDaySelected('MON', 1) ? 'checked' : ''}> <span>Seg</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="TUE" ${isDaySelected('TUE', 2) ? 'checked' : ''}> <span>Ter</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="WED" ${isDaySelected('WED', 3) ? 'checked' : ''}> <span>Qua</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="THU" ${isDaySelected('THU', 4) ? 'checked' : ''}> <span>Qui</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="FRI" ${isDaySelected('FRI', 5) ? 'checked' : ''}> <span>Sex</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="SAT" ${isDaySelected('SAT', 6) ? 'checked' : ''}> <span>Sáb</span>
            </label>
            <label class="cursor-pointer border border-slate-700 rounded-lg p-2 bg-slate-900 flex items-center justify-center space-x-1">
              <input type="checkbox" name="swal-days" value="SUN" ${isDaySelected('SUN', 7) ? 'checked' : ''}> <span>Dom</span>
            </label>
          </div>
        </div>
        <p class="text-[11px] text-slate-400">Ao salvar, o sistema atualizará o Google Calendar e o Apple iCloud automaticamente com alarme 10 min antes.</p>
      </div>
    `,
    focusConfirm: false,
    showCancelButton: true,
    confirmButtonText: 'Salvar e Ressincronizar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#334155',
    background: '#0f172a',
    color: '#f8fafc',
    preConfirm: () => {
      const time = document.getElementById('swal-time').value
      const checkboxes = document.querySelectorAll('input[name="swal-days"]:checked')
      const days = Array.from(checkboxes).map((cb) => cb.value)
      if (!time || days.length === 0) {
        swal.instance.showValidationMessage('Selecione pelo menos um dia e um horário válido.')
        return false
      }
      return { preferred_time: time, study_days: days }
    },
  })

  if (formValues) {
    try {
      await languageStore.updateSchedule(formValues)
      swal.toast('Rotina e agenda Google/Apple atualizadas com sucesso!', 'success')
    } catch (err) {
      swal.error('Erro ao atualizar agenda', err.response?.data?.message || 'Falha ao salvar.')
    }
  }
}
</script>

<template>
  <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl relative overflow-hidden backdrop-blur-md">
    <!-- Glow de fundo sutil -->
    <div class="absolute -top-12 -right-12 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-5 relative z-10">
      <!-- Lado Esquerdo: Idioma Ativo + Nível CEFR + Barra de XP -->
      <div class="flex items-start sm:items-center space-x-3.5 sm:space-x-4 min-w-0">
        <div class="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-2xl sm:text-3xl shadow-inner shrink-0">
          {{ currentFlag }}
        </div>

        <div class="space-y-1.5 min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-lg sm:text-xl font-black text-white tracking-tight">
              {{ profile?.target_language || 'Idiomas' }}
            </h1>
            <span
              class="px-2.5 py-0.5 rounded-full text-xs font-mono font-black border uppercase tracking-wider shrink-0"
              :class="cefrColors[profile?.cefr_level || 'UNSET']"
            >
              {{ profile?.cefr_level === 'UNSET' ? 'Diagnóstico Pendente' : `Nível ${profile?.cefr_level}` }}
            </span>
            <span class="text-xs text-slate-400 capitalize hidden sm:inline-block">
              • {{ profile?.learning_focus }}
            </span>
          </div>

          <!-- Barra de XP para o próximo nível -->
          <div class="flex flex-wrap items-center gap-2 text-[11px] font-mono">
            <span class="text-slate-400">Progresso</span>
            <div class="w-28 sm:w-48 h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/60 shrink-0">
              <div
                class="h-full bg-gradient-to-r from-emerald-500 to-indigo-500 transition-all duration-700"
                :style="{ width: `${languageStore.cefrProgressPercentage}%` }"
              ></div>
            </div>
            <span class="text-emerald-400 font-bold">Rumo a {{ nextCefrLevel }}</span>
          </div>
        </div>
      </div>

      <!-- Lado Direito: Ofensiva (Streak) + Agenda Google/Apple + FinOps Gemini Flash -->
      <div class="flex flex-wrap items-center gap-2.5 w-full lg:w-auto">
        <!-- Contador de Ofensiva (Streak 🔥) -->
        <div
          class="flex items-center space-x-2 px-3 py-2 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 text-amber-300 shadow-sm flex-1 sm:flex-initial min-w-[120px]"
          title="Dias consecutivos de micro-learning completados"
        >
          <span class="text-xl animate-bounce-subtle">🔥</span>
          <div>
            <span class="text-[10px] uppercase font-mono block text-amber-400 font-bold leading-none">Ofensiva</span>
            <span class="text-sm font-black font-mono leading-tight">
              {{ profile?.streak_days || 0 }} {{ (profile?.streak_days || 0) === 1 ? 'dia' : 'dias' }}
            </span>
          </div>
        </div>

        <!-- Agenda Sincronizada (Google / Apple) -->
        <button
          type="button"
          @click="openScheduleEditModal"
          class="flex items-center space-x-2.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-200 transition text-left group flex-1 sm:flex-initial min-w-[140px]"
        >
          <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0"></div>
          <div class="min-w-0">
            <span class="text-[10px] uppercase font-mono block text-slate-400 group-hover:text-emerald-400 transition font-bold leading-none">
              Rotina 15 min ⚙️
            </span>
            <span class="text-xs font-mono font-semibold text-slate-200 leading-tight truncate block">
              {{ profile?.preferred_time }} ({{ daysFormatted }})
            </span>
          </div>
        </button>

        <!-- Consumo de Tokens Flash (FinOps & Latência) -->
        <div
          class="hidden md:flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] font-mono text-slate-400"
          title="Consumo auditado pelo modelo gemini-3.8-flash no backend"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          <span>Flash: <strong class="text-indigo-300">{{ stats?.flash_tokens_used || 0 }}</strong> tokens</span>
          <span class="text-slate-600">|</span>
          <span class="text-emerald-400">\${{ Number(stats?.flash_cost_usd || 0).toFixed(4) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
