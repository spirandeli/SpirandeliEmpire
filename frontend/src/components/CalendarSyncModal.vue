<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  feedUrl: {
    type: String,
    required: true,
  },
  event: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue'])

const copied = ref(false)
let copyTimeout = null

function closeModal() {
  emit('update:modelValue', false)
}

/**
 * Converte a URL do feed HTTPS/HTTP para o protocolo nativo webcal://
 * para disparar a janela de assinatura automática no macOS / iOS.
 */
const webcalUrl = computed(() => {
  if (!props.feedUrl) return ''
  return props.feedUrl.replace(/^https?:\/\//i, 'webcal://')
})

/**
 * Converte data para string UTC formatada no padrão iCalendar: YYYYMMDDTHHMMSSZ
 */
function toUtcCompactFormat(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

/**
 * Gera dinamicamente a URL de template do Google Agenda para evento único
 */
const googleCalendarEventUrl = computed(() => {
  if (!props.event) return ''

  const startUtc = toUtcCompactFormat(props.event.start_at || props.event.starts_at || new Date().toISOString())
  const endUtc = toUtcCompactFormat(
    props.event.end_at || props.event.ends_at || new Date(Date.now() + 30 * 60 * 1000).toISOString()
  )

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: props.event.title || 'Novo Agendamento',
    dates: `${startUtc}/${endUtc}`,
    details: props.event.description || '',
    location: props.event.location || '',
  })

  return `https://calendar.google.com/calendar/render?${params.toString()}`
})

/**
 * URL de download do arquivo .ics para evento individual
 */
const downloadSingleEventUrl = computed(() => {
  if (!props.event) return '#'
  if (props.event.download_url) return props.event.download_url
  return `/api/v1/calendar/events/${props.event.id}/download`
})

/**
 * Copia a URL do feed para a área de transferência com feedback visual
 */
async function copyFeedUrl() {
  try {
    await navigator.clipboard.writeText(props.feedUrl)
    copied.value = true
    if (copyTimeout) clearTimeout(copyTimeout)
    copyTimeout = setTimeout(() => {
      copied.value = false
    }, 2500)
  } catch (err) {
    console.error('Falha ao copiar feed URL:', err)
  }
}

/**
 * Abre o link nativo do Google Calendar
 */
function openGoogleCalendar() {
  if (googleCalendarEventUrl.value) {
    window.open(googleCalendarEventUrl.value, '_blank', 'noopener,noreferrer')
  }
}

/**
 * Dispara o protocolo nativo webcal:// no sistema operacional
 */
function openAppleWebcal() {
  if (webcalUrl.value) {
    window.location.href = webcalUrl.value
  }
}
</script>

<template>
  <div
    v-if="modelValue"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn"
    @click.self="closeModal"
    @keydown.esc="closeModal"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col transform transition-all duration-200"
    >
      <!-- Header do Modal -->
      <div class="p-6 border-b border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/30 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-xl text-indigo-400">
            📅
          </div>
          <div>
            <h3 class="text-base font-bold text-white tracking-tight">Sincronização de Calendário</h3>
            <p class="text-xs text-slate-400">Integração nativa sem senhas ou permissões OAuth complexas</p>
          </div>
        </div>

        <button
          type="button"
          @click="closeModal"
          class="w-8 h-8 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition"
          title="Fechar"
        >
          ✕
        </button>
      </div>

      <!-- Card de Destaque do Evento (se fornecido no contexto pós-agendamento) -->
      <div v-if="event" class="px-6 pt-5">
        <div class="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 flex items-start space-x-3.5">
          <div class="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-base shrink-0">
            ✓
          </div>
          <div class="space-y-1 flex-1 min-w-0">
            <span class="text-[10px] uppercase font-mono font-bold text-emerald-400 block tracking-wider">Agendamento Confirmado</span>
            <h4 class="text-sm font-bold text-white truncate">{{ event.title || 'Novo Evento' }}</h4>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-300 pt-0.5">
              <span v-if="event.start_at || event.starts_at" class="flex items-center space-x-1">
                <span class="text-slate-500">🕒</span>
                <span>{{ new Date(event.start_at || event.starts_at).toLocaleString() }}</span>
              </span>
              <span v-if="event.location" class="flex items-center space-x-1 text-slate-400">
                <span class="text-slate-500">📍</span>
                <span class="truncate">{{ event.location }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Corpo Principal com as Opções de Calendário -->
      <div class="p-6 space-y-5 overflow-y-auto max-h-[70vh]">
        <!-- BLOCO 1: Google Agenda -->
        <div class="p-5 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition space-y-3.5">
          <div class="flex items-center space-x-2.5">
            <div class="w-7 h-7 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 font-bold text-xs">
              G
            </div>
            <div>
              <h4 class="text-sm font-bold text-white">Google Agenda (Web / Android)</h4>
              <p class="text-[11px] text-slate-400">Adicione este evento ou assine para receber atualizações automáticas</p>
            </div>
          </div>

          <div class="space-y-2 pt-1">
            <!-- Ação 1.1: Adicionar este evento isolado (v-if="event") -->
            <button
              v-if="event"
              type="button"
              @click="openGoogleCalendar"
              class="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-md shadow-sky-600/20 transition active:scale-98"
            >
              <span>+ Adicionar este evento ao Google Agenda</span>
              <span>↗</span>
            </button>

            <!-- Ação 1.2: Copiar URL para Assinar Agenda Completa -->
            <div class="pt-1 space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-slate-400 font-mono">Assinar Feed Completo (Todos os Eventos):</span>
                <span v-if="copied" class="text-emerald-400 font-mono font-bold animate-pulse">✓ Copiado!</span>
              </div>

              <div class="flex items-center space-x-2">
                <input
                  type="text"
                  readonly
                  :value="feedUrl"
                  class="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-[11px] font-mono text-slate-300 focus:outline-none select-all truncate"
                />
                <button
                  type="button"
                  @click="copyFeedUrl"
                  class="px-3 py-2 rounded-xl border text-xs font-bold transition flex items-center space-x-1.5 shrink-0"
                  :class="copied
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300'
                    : 'border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200'"
                >
                  <span>{{ copied ? 'Copiado!' : 'Copiar URL' }}</span>
                </button>
              </div>

              <p class="text-[10px] text-slate-500 leading-tight">
                No Google Agenda, clique em <em>"Outras agendas +"</em> &rarr; <em>"Do URL"</em> e cole o link acima.
              </p>
            </div>
          </div>
        </div>

        <!-- BLOCO 2: Apple Calendar (iOS / macOS / iPadOS) -->
        <div class="p-5 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition space-y-3.5">
          <div class="flex items-center space-x-2.5">
            <div class="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold text-xs">
              
            </div>
            <div>
              <h4 class="text-sm font-bold text-white">Apple Calendar (iPhone, Mac & iPad)</h4>
              <p class="text-[11px] text-slate-400">Assinatura direta com 1 clique usando o protocolo nativo webcal://</p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <!-- Ação 2.1: Sincronizar Agenda Completa (Automático) -->
            <button
              type="button"
              @click="openAppleWebcal"
              class="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white font-bold text-xs shadow-md shadow-indigo-600/20 transition active:scale-98"
              :class="{ 'sm:col-span-2': !event }"
            >
              <span>⚡ Sincronizar Agenda Completa</span>
            </button>

            <!-- Ação 2.2: Baixar apenas este Evento (.ics) -->
            <a
              v-if="event"
              :href="downloadSingleEventUrl"
              download
              class="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 text-slate-200 font-bold text-xs transition"
            >
              <span>📥 Baixar Evento (.ics)</span>
            </a>
          </div>

          <p class="text-[10px] text-slate-500 leading-tight">
            Em dispositivos Apple, o botão <em>"Sincronizar Agenda Completa"</em> abre o app Calendário para adicionar uma assinatura dinâmica atualizada automaticamente.
          </p>
        </div>
      </div>

      <!-- Rodapé do Modal -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/50 flex items-center justify-end">
        <button
          type="button"
          @click="closeModal"
          class="px-5 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          Concluir
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
.animate-fadeIn {
  animation: fadeIn 0.15s ease-out forwards;
}
</style>

