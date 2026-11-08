<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { useSwal } from '@/composables/useSwal'

marked.setOptions({
  gfm: true,
  breaks: true,
})

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  task: {
    type: Object,
    default: null,
  },
  isExecuting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'execute', 'move', 'delete'])
const swal = useSwal()

const activeTab = ref('deliverable') // 'deliverable' | 'briefing' | 'technical'
const activeImagePreview = ref(null)

// Quando abre o modal, define a aba inicial
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      document.body.style.overflow = 'hidden'
      // Se houver entregável, foca nele, senão foca no briefing
      if (props.task?.result) {
        activeTab.value = 'deliverable'
      } else {
        activeTab.value = 'briefing'
      }
      activeImagePreview.value = null
    } else {
      document.body.style.overflow = ''
    }
  }
)

function handleKeyDown(e) {
  if (e.key === 'Escape' && props.isOpen) {
    if (activeImagePreview.value) {
      activeImagePreview.value = null
    } else {
      emit('close')
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  document.body.style.overflow = ''
})

function renderMarkdown(content) {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (err) {
    return content
  }
}

function copyText(text, successMsg = 'Copiado para a área de transferência!') {
  if (!text) return
  if (typeof text === 'object') {
    text = JSON.stringify(text, null, 2)
  }
  navigator.clipboard.writeText(text)
  swal.toast(successMsg, 'success')
}

function formatDate(isoStr) {
  if (!isoStr) return '—'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch (e) {
    return isoStr
  }
}

const executionDuration = computed(() => {
  if (!props.task?.started_at || !props.task?.completed_at) return null
  try {
    const start = new Date(props.task.started_at).getTime()
    const end = new Date(props.task.completed_at).getTime()
    const diffSec = Math.max(0, Math.round((end - start) / 1000))
    if (diffSec < 60) return `${diffSec}s`
    const mins = Math.floor(diffSec / 60)
    const secs = diffSec % 60
    return `${mins}m ${secs}s`
  } catch (e) {
    return null
  }
})

const hasDeliverable = computed(() => {
  return Boolean(props.task?.result)
})

const videoUrl = computed(() => {
  return props.task?.result?.video_url || props.task?.result?.media?.video?.url || null
})

const audioUrl = computed(() => {
  return props.task?.result?.audio_url || props.task?.result?.media?.audio?.url || null
})

const srtUrl = computed(() => {
  return props.task?.result?.srt_url || props.task?.result?.media?.subtitles?.srt_url || null
})

const imagesList = computed(() => {
  return props.task?.result?.media?.images_generated || []
})

function getStatusBadge(status) {
  switch (status) {
    case 'backlog':
      return { label: '1. Backlog Geral', cls: 'bg-slate-800 text-slate-300 border-slate-700' }
    case 'in_progress_agent':
      return { label: '2. IA Worker (Executando)', cls: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' }
    case 'awaiting_supervision':
      return { label: '3. Supervisão (Revisar)', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/30' }
    case 'todo_user':
      return { label: '4. A Fazer (Humano)', cls: 'bg-sky-500/20 text-sky-300 border-sky-500/30' }
    case 'done':
    case 'completed':
      return { label: '5. Concluído', cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    case 'blocked':
      return { label: 'Bloqueado', cls: 'bg-rose-500/20 text-rose-300 border-rose-500/30' }
    default:
      return { label: status || 'Desconhecido', cls: 'bg-slate-800 text-slate-300 border-slate-700' }
  }
}

function getPriorityBadge(priority) {
  switch (priority) {
    case 'urgent':
      return { label: 'Urgente', cls: 'bg-rose-500/20 text-rose-300 border-rose-500/40' }
    case 'high':
      return { label: 'Alta', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' }
    case 'medium':
      return { label: 'Média', cls: 'bg-slate-800 text-slate-300 border-slate-700' }
    case 'low':
      return { label: 'Baixa', cls: 'bg-slate-800/80 text-slate-400 border-slate-800' }
    default:
      return { label: priority || 'Média', cls: 'bg-slate-800 text-slate-300 border-slate-700' }
  }
}
</script>

<template>
  <div
    v-if="isOpen && task"
    class="fixed inset-0 z-50 overflow-hidden flex items-center justify-center p-2 sm:p-4 md:p-6"
    role="dialog"
    aria-modal="true"
  >
    <!-- Backdrop com blur -->
    <div
      class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
      @click="emit('close')"
    ></div>

    <!-- Modal Container -->
    <div
      class="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[92vh] z-10 animate-in fade-in zoom-in-95 duration-200 overflow-hidden"
    >
      <!-- HEADER DO MODAL -->
      <div class="px-5 py-4 border-b border-slate-800 bg-slate-950/70 shrink-0 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <!-- Badges de Status, Assignee & Prioridade -->
          <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <span
              class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border tracking-wide"
              :class="getStatusBadge(task.status).cls"
            >
              {{ task.status_label || getStatusBadge(task.status).label }}
            </span>

            <span
              class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider"
              :class="task.assignee === 'agent' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' : 'bg-sky-500/10 text-sky-400 border-sky-500/30'"
            >
              {{ task.assignee === 'agent' ? '🤖 Gemini IA Worker' : '👤 Humano' }}
            </span>

            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-semibold border"
              :class="getPriorityBadge(task.priority).cls"
            >
              {{ getPriorityBadge(task.priority).label }}
            </span>

            <span v-if="task.business" class="text-[11px] text-slate-400 font-medium">
              Venture: <strong class="text-white">{{ task.business.name }}</strong>
            </span>
          </div>

          <!-- Botão Fechar -->
          <button
            type="button"
            @click="emit('close')"
            aria-label="Fechar modal"
            class="p-1.5 rounded-xl text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Título da Tarefa -->
        <h2 class="text-base sm:text-lg font-bold text-white tracking-tight leading-snug">
          {{ task.title }}
        </h2>

        <!-- NAVEGAÇÃO POR ABAS -->
        <div class="flex items-center space-x-1 border-b border-slate-800/60 pt-1 -mb-1">
          <button
            type="button"
            @click="activeTab = 'deliverable'"
            class="px-3.5 py-1.5 text-xs font-semibold rounded-t-xl transition flex items-center space-x-1.5 border-b-2"
            :class="activeTab === 'deliverable'
              ? 'text-emerald-400 border-emerald-400 bg-emerald-500/10'
              : 'text-slate-400 hover:text-slate-200 border-transparent'"
          >
            <span>📄</span>
            <span>Entregável & Mídia</span>
            <span
              v-if="hasDeliverable"
              class="w-2 h-2 rounded-full bg-emerald-400 inline-block ml-0.5"
            ></span>
          </button>

          <button
            type="button"
            @click="activeTab = 'briefing'"
            class="px-3.5 py-1.5 text-xs font-semibold rounded-t-xl transition flex items-center space-x-1.5 border-b-2"
            :class="activeTab === 'briefing'
              ? 'text-emerald-400 border-emerald-400 bg-emerald-500/10'
              : 'text-slate-400 hover:text-slate-200 border-transparent'"
          >
            <span>📋</span>
            <span>Briefing & Instruções</span>
          </button>

          <button
            type="button"
            @click="activeTab = 'technical'"
            class="px-3.5 py-1.5 text-xs font-semibold rounded-t-xl transition flex items-center space-x-1.5 border-b-2"
            :class="activeTab === 'technical'
              ? 'text-emerald-400 border-emerald-400 bg-emerald-500/10'
              : 'text-slate-400 hover:text-slate-200 border-transparent'"
          >
            <span>⚙️</span>
            <span>Logs & Execução</span>
            <span
              v-if="task.failure_reason"
              class="w-2 h-2 rounded-full bg-rose-400 inline-block ml-0.5"
              title="Possui falha registrada"
            ></span>
          </button>
        </div>
      </div>

      <!-- CORPO DO MODAL (SCROLLÁVEL) -->
      <div class="flex-1 overflow-y-auto p-5 space-y-5 text-slate-300 text-xs leading-relaxed">
        <!-- ================= ABA 1: ENTREGÁVEL & MÍDIA ================= -->
        <div v-if="activeTab === 'deliverable'" class="space-y-4">
          <!-- Caso ainda NÃO haja entregável produzido -->
          <div
            v-if="!hasDeliverable"
            class="p-8 text-center rounded-2xl bg-slate-950/60 border border-dashed border-slate-800 space-y-3"
          >
            <div class="w-12 h-12 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-xl">
              ⚡
            </div>
            <div>
              <h3 class="text-sm font-bold text-white">Nenhum entregável produzido ainda</h3>
              <p class="text-xs text-slate-400 max-w-md mx-auto mt-1">
                Esta tarefa ainda não foi executada pelo IA Worker (Gemini 3.8). Você pode disparar a execução autônoma agora mesmo.
              </p>
            </div>
            <div class="pt-2">
              <button
                v-if="task.assignee === 'agent'"
                type="button"
                @click="emit('execute', task)"
                :disabled="isExecuting"
                class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs inline-flex items-center space-x-1.5 shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
              >
                <span v-if="isExecuting" class="animate-spin">⏳</span>
                <span v-else>⚡</span>
                <span>{{ isExecuting ? 'Executando com IA...' : 'Executar Tarefa com Gemini 3.8' }}</span>
              </button>
            </div>
          </div>

          <!-- Caso HAJA entregável produzido -->
          <template v-else>
            <!-- BLOCO 1: PLAYER DE VÍDEO 9:16 & MÍDIAS VERTICAIS -->
            <div
              v-if="videoUrl"
              class="p-4 rounded-2xl bg-gradient-to-b from-indigo-950/40 via-slate-900 to-slate-950 border border-indigo-500/30 space-y-3.5 shadow-xl"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <span class="text-lg">🎬</span>
                  <div>
                    <h3 class="text-sm font-bold text-white">Vídeo Vertical 9:16 Renderizado</h3>
                    <p class="text-[10px] text-slate-400">Pronto para TikTok Shop, YouTube Shorts e Instagram Reels</p>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5 text-[10px] font-mono">
                  <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">1080x1920</span>
                  <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {{ task.result?.media?.video?.duration_seconds || '60' }}s
                  </span>
                  <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {{ task.result?.media?.video?.size_mb || '0' }} MB
                  </span>
                </div>
              </div>

              <!-- Player de Vídeo 9:16 com proporção elegante -->
              <div class="flex justify-center bg-black/80 rounded-xl p-3 border border-slate-800/80">
                <video
                  :src="videoUrl"
                  controls
                  playsinline
                  class="max-h-[360px] sm:max-h-[420px] w-auto rounded-lg shadow-2xl border border-slate-700/60"
                ></video>
              </div>

              <!-- Botões de Ação e Download -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                <a
                  :href="videoUrl"
                  download
                  target="_blank"
                  class="px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] text-center flex items-center justify-center space-x-1.5 transition shadow-md shadow-emerald-500/20"
                >
                  <span>📥</span>
                  <span>Baixar Vídeo (.mp4)</span>
                </a>

                <a
                  v-if="audioUrl"
                  :href="audioUrl"
                  download
                  target="_blank"
                  class="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] text-center flex items-center justify-center space-x-1.5 transition shadow-sm"
                >
                  <span>🎙️</span>
                  <span>Baixar Áudio (.mp3)</span>
                </a>

                <a
                  v-if="srtUrl"
                  :href="srtUrl"
                  download
                  target="_blank"
                  class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-[11px] text-center flex items-center justify-center space-x-1.5 transition border border-slate-700"
                >
                  <span>📝</span>
                  <span>Legendas (.srt)</span>
                </a>
              </div>

              <!-- Galeria de Cenas Visuais Geradas -->
              <div v-if="imagesList.length > 0" class="pt-3 border-t border-slate-800/80">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Cenas Visuais Geradas ({{ imagesList.length }} frames 9:16):
                  </span>
                  <span class="text-[10px] text-slate-500">Clique para expandir</span>
                </div>
                <div class="flex space-x-2 overflow-x-auto pb-1.5">
                  <div
                    v-for="(imgUrl, iIdx) in imagesList"
                    :key="iIdx"
                    @click="activeImagePreview = imgUrl"
                    class="shrink-0 w-20 h-32 rounded-xl overflow-hidden border border-slate-800 hover:border-emerald-500 cursor-pointer transition shadow-md group relative"
                    :title="`Cena ${iIdx + 1} (Clique para ampliar)`"
                  >
                    <img :src="imgUrl" :alt="`Cena ${iIdx + 1}`" class="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
                    <span class="absolute bottom-1 right-1 text-[9px] bg-black/70 text-white px-1 rounded font-mono">
                      #{{ iIdx + 1 }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- BLOCO 2: RESUMO EXECUTIVO -->
            <div v-if="task.result?.summary" class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <span>💡</span>
                  <span>Resumo Executivo da Entrega</span>
                </h4>
                <button
                  type="button"
                  @click="copyText(task.result.summary, 'Resumo executivo copiado!')"
                  class="text-[10px] text-slate-400 hover:text-white underline"
                >
                  Copiar Resumo
                </button>
              </div>
              <p class="text-slate-200 text-xs leading-relaxed">{{ task.result.summary }}</p>
            </div>

            <!-- BLOCO 3: CONTEÚDO FORMATADO EM MARKDOWN -->
            <div v-if="task.result?.markdown_content" class="space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
                  <span>📑</span>
                  <span>Documento / Roteiro Completo</span>
                </h4>
                <button
                  type="button"
                  @click="copyText(task.result.markdown_content, 'Conteúdo Markdown copiado!')"
                  class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold flex items-center space-x-1 transition"
                >
                  <span>📋</span>
                  <span>Copiar Markdown</span>
                </button>
              </div>

              <!-- Renderização com tipografia Dark chat-markdown -->
              <div
                class="chat-markdown p-5 rounded-2xl bg-slate-950 border border-slate-800/90 text-slate-200 shadow-inner"
                v-html="renderMarkdown(task.result.markdown_content)"
              ></div>
            </div>

            <!-- BLOCO 4: ITENS & CENAS DETALHADAS -->
            <div v-if="task.result?.items?.length" class="space-y-3 pt-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <span>🎞️</span>
                  <span>Cenas & Assets Estruturados ({{ task.result.items.length }})</span>
                </h4>
                <span class="text-[10px] text-slate-500">TTS & Prompts Midjourney/Leonardo</span>
              </div>

              <div class="space-y-3">
                <div
                  v-for="(it, idx) in task.result.items"
                  :key="idx"
                  class="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-2.5 hover:border-slate-700 transition"
                >
                  <div class="flex items-center justify-between">
                    <strong class="text-white text-xs font-bold">{{ idx + 1 }}. {{ it.title }}</strong>
                    <div class="flex items-center space-x-1.5">
                      <span
                        v-for="(tg, tIdx) in it.tags || []"
                        :key="tIdx"
                        class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[9px] font-mono"
                      >
                        {{ tg }}
                      </span>
                      <span v-if="it.description" class="text-slate-500 text-[10px] ml-1">{{ it.description }}</span>
                    </div>
                  </div>

                  <!-- Script de Narração -->
                  <div v-if="it.script" class="bg-slate-900/70 p-3 rounded-lg border border-slate-800/60 space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="text-emerald-400 font-semibold text-[10px] uppercase tracking-wider">🎙️ Narração / TTS:</span>
                      <button
                        type="button"
                        @click="copyText(it.script, 'Narração copiada!')"
                        class="text-[10px] text-slate-400 hover:text-emerald-300 underline"
                      >
                        Copiar Narração
                      </button>
                    </div>
                    <p class="text-slate-200 text-[11px] leading-relaxed">{{ it.script }}</p>
                  </div>

                  <!-- Prompt Visual para IA Generativa -->
                  <div v-if="it.visual_prompt" class="bg-indigo-950/30 p-3 rounded-lg border border-indigo-500/20 space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="font-bold text-[10px] uppercase text-indigo-400">🎨 Prompt Visual (Midjourney / Leonardo):</span>
                      <button
                        type="button"
                        @click="copyText(it.visual_prompt, 'Prompt visual copiado!')"
                        class="text-[10px] text-indigo-300 hover:text-white underline font-medium"
                      >
                        Copiar Prompt
                      </button>
                    </div>
                    <code class="block font-mono text-[10px] text-indigo-200 bg-slate-950/60 p-2 rounded border border-indigo-500/10 select-all whitespace-pre-wrap">
                      {{ it.visual_prompt }}
                    </code>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- ================= ABA 2: BRIEFING & INSTRUÇÕES ================= -->
        <div v-if="activeTab === 'briefing'" class="space-y-4">
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
              <span>🎯</span>
              <span>Descrição Integral da Demanda</span>
            </h4>
            <div class="text-slate-200 text-xs whitespace-pre-wrap leading-relaxed">
              {{ task.description || 'Nenhuma descrição detalhada informada na criação desta tarefa.' }}
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span class="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Origem da Demanda</span>
              <span class="text-slate-200 font-medium">
                {{ task.source === 'agent' ? '🤖 Agente Autônomo' : task.source === 'automation' ? '⚡ Automação Cron/Evento' : '👤 Usuário / Operador' }}
              </span>
            </div>

            <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
              <span class="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Ação Executada</span>
              <span class="text-slate-200 font-mono text-[11px]">
                {{ task.agent_action || 'pipeline_general_execution' }}
              </span>
            </div>

            <div v-if="task.business" class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1 sm:col-span-2">
              <span class="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Negócio / Venture Associado</span>
              <div class="flex items-center justify-between">
                <span class="text-emerald-400 font-bold text-sm">{{ task.business.name }}</span>
                <span class="text-slate-500 text-[11px] font-mono">ID #{{ task.business_id }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ================= ABA 3: LOGS & EXECUÇÃO ================= -->
        <div v-if="activeTab === 'technical'" class="space-y-4">
          <!-- Alerta de Erro se houver Falha -->
          <div
            v-if="task.failure_reason"
            class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-2"
          >
            <div class="flex items-center space-x-2">
              <span class="text-base">⚠️</span>
              <span class="font-bold text-xs uppercase tracking-wider">Falha Registrada na Execução</span>
            </div>
            <p class="font-mono text-[11px] bg-slate-950 p-2.5 rounded-lg border border-rose-500/20 text-rose-200 whitespace-pre-wrap">
              {{ task.failure_reason }}
            </p>
          </div>

          <!-- Métricas de Tempo e Timestamps -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span class="text-[10px] uppercase font-bold text-slate-500 block">Criada Em</span>
              <span class="text-white font-mono text-[11px]">{{ formatDate(task.created_at) }}</span>
            </div>

            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span class="text-[10px] uppercase font-bold text-slate-500 block">Iniciada Em</span>
              <span class="text-white font-mono text-[11px]">{{ formatDate(task.started_at) }}</span>
            </div>

            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span class="text-[10px] uppercase font-bold text-slate-500 block">Concluída Em</span>
              <span class="text-white font-mono text-[11px]">{{ formatDate(task.completed_at) }}</span>
            </div>

            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
              <span class="text-[10px] uppercase font-bold text-slate-500 block">Duração / Tentativas</span>
              <span class="text-emerald-400 font-mono text-[11px]">
                {{ executionDuration || '—' }} · {{ task.attempts || 0 }}x
              </span>
            </div>
          </div>

          <!-- Payload JSON de Entrada -->
          <div v-if="task.payload && Object.keys(task.payload).length > 0" class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold text-slate-400">Payload de Entrada (JSON):</span>
              <button
                type="button"
                @click="copyText(task.payload, 'Payload copiado!')"
                class="text-[10px] text-slate-400 hover:text-white underline"
              >
                Copiar JSON
              </button>
            </div>
            <pre class="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[10px] text-cyan-300 overflow-x-auto max-h-48">{{ JSON.stringify(task.payload, null, 2) }}</pre>
          </div>

          <!-- Result Raw JSON para Inspecção Avançada -->
          <div v-if="task.result" class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold text-slate-400">Result Estruturado Bruto:</span>
              <button
                type="button"
                @click="copyText(task.result, 'Resultado bruto copiado!')"
                class="text-[10px] text-slate-400 hover:text-white underline"
              >
                Copiar JSON
              </button>
            </div>
            <pre class="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[10px] text-amber-300 overflow-x-auto max-h-48">{{ JSON.stringify(task.result, null, 2) }}</pre>
          </div>
        </div>
      </div>

      <!-- FOOTER DE AÇÕES DO MODAL -->
      <div class="px-5 py-3.5 border-t border-slate-800 bg-slate-950/80 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 shrink-0">
        <!-- Lado Esquerdo: Ações de Cópia e Exclusão -->
        <div class="flex items-center space-x-2">
          <button
            v-if="hasDeliverable"
            type="button"
            @click="copyText(task.result?.markdown_content || task.result?.summary, 'Todo o conteúdo copiado com sucesso!')"
            class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center space-x-1"
          >
            <span>📋</span>
            <span>Copiar Entregável</span>
          </button>

          <button
            type="button"
            @click="emit('delete', task)"
            class="px-3 py-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 text-xs font-medium transition"
          >
            Excluir Tarefa
          </button>
        </div>

        <!-- Lado Direito: Ações de Execução, Aprovação e Fechamento -->
        <div class="flex items-center justify-end space-x-2">
          <!-- Botão Executar / Reexecutar IA Worker -->
          <button
            v-if="task.assignee === 'agent'"
            type="button"
            @click="emit('execute', task)"
            :disabled="isExecuting"
            class="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition flex items-center space-x-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-50"
          >
            <span v-if="isExecuting" class="animate-spin">⏳</span>
            <span v-else>⚡</span>
            <span>{{ isExecuting ? 'Executando...' : (hasDeliverable ? 'Reexecutar IA' : 'Executar com IA') }}</span>
          </button>

          <!-- Botão Aprovar Entregável (quando em supervisão ou backlog) -->
          <button
            v-if="task.status === 'awaiting_supervision' || (task.status !== 'done' && task.status !== 'completed' && hasDeliverable)"
            type="button"
            @click="emit('move', task, 'done')"
            class="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition flex items-center space-x-1.5 shadow-md shadow-emerald-500/20"
          >
            <span>✓</span>
            <span>Aprovar & Concluir</span>
          </button>

          <!-- Botão Fechar -->
          <button
            type="button"
            @click="emit('close')"
            class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>

    <!-- LIGHTBOX PREVIEW DE IMAGEM AMPLIADA -->
    <div
      v-if="activeImagePreview"
      class="fixed inset-0 z-60 bg-black/90 backdrop-blur-md flex items-center justify-center p-4"
      @click="activeImagePreview = null"
    >
      <div class="relative max-w-lg max-h-[90vh] flex flex-col items-center">
        <button
          type="button"
          @click="activeImagePreview = null"
          class="absolute -top-10 right-0 text-white hover:text-rose-400 p-2 text-sm font-bold"
        >
          ✕ Fechar
        </button>
        <img
          :src="activeImagePreview"
          alt="Visualização da Cena"
          class="max-w-full max-h-[80vh] rounded-2xl shadow-2xl border border-slate-700 object-contain"
        />
        <div class="mt-3 flex items-center space-x-3">
          <a
            :href="activeImagePreview"
            download
            target="_blank"
            class="px-3.5 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition flex items-center space-x-1"
          >
            <span>📥</span>
            <span>Baixar Imagem</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

