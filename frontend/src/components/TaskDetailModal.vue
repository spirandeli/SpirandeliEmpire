<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'
import TaskMediaGallery from '@/components/TaskMediaGallery.vue'

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

const emit = defineEmits(['close', 'execute', 'move', 'delete', 'updated'])
const swal = useSwal()

const activeTab = ref('deliverable') // 'deliverable' | 'briefing' | 'technical'
const activeImagePreview = ref(null)
const pipelineData = ref(null)
const pipelineLoading = ref(false)
const runningStage = ref(null)
const regeneratingScene = ref(null)
const scriptRevisionFeedback = ref('')

const isPipelineTask = computed(() => {
  const act = props.task?.agent_action || ''
  return Boolean(
    props.task?.payload?.pipeline_stage ||
      props.task?.payload?.stage_statuses ||
      props.task?.result?.pipeline_manifest ||
      ['orchestrate_video_pipeline', 'render_video_series', 'agent_script', 'agent_video_scenes', 'agent_narration', 'agent_subtitles', 'agent_assemble_video'].includes(act)
  )
})

const pipelineParentId = computed(() => props.task?.parent_id || props.task?.id)

async function fetchPipelineState() {
  if (!props.task?.id || !isPipelineTask.value) {
    pipelineData.value = null
    return
  }
  pipelineLoading.value = true
  try {
    const res = await api.get(`/tasks/${props.task.id}/pipeline`)
    pipelineData.value = res.data?.data || null
  } catch {
    pipelineData.value = null
  } finally {
    pipelineLoading.value = false
  }
}

async function handleApproveScriptAndContinue() {
  if (!pipelineParentId.value) return
  runningStage.value = 'continue'
  try {
    const res = await api.post(`/tasks/${pipelineParentId.value}/agents/continue`)
    swal.toast(res.data?.message || 'Agentes 2 a 5 iniciados!', 'success')
    await fetchPipelineState()
    emit('updated')
  } catch (err) {
    swal.error('Erro ao liberar pipeline', err.response?.data?.detail || err.message)
  } finally {
    runningStage.value = null
  }
}

async function handleRunSingleAgent(stage, cascade = true) {
  if (!pipelineParentId.value) return
  runningStage.value = stage
  try {
    const payload = { cascade }
    if (stage === 'script' && scriptRevisionFeedback.value.trim()) {
      payload.feedback = scriptRevisionFeedback.value.trim()
      payload.cascade = false
    }
    const res = await api.post(`/tasks/${pipelineParentId.value}/agents/${stage}/run`, payload)
    swal.toast(res.data?.message || `Agente '${stage}' iniciado!`, 'success')
    if (stage === 'script') scriptRevisionFeedback.value = ''
    await fetchPipelineState()
    emit('updated')
  } catch (err) {
    swal.error('Erro ao executar agente', err.response?.data?.detail || err.message)
  } finally {
    runningStage.value = null
  }
}

async function handleRegenerateScene(sceneNumber) {
  if (!pipelineParentId.value) return
  regeneratingScene.value = sceneNumber
  try {
    const res = await api.post(`/tasks/${pipelineParentId.value}/scenes/${sceneNumber}/regenerate`, {
      reassemble: true,
    })
    swal.toast(res.data?.message || `Cena #${sceneNumber} regenerada via Gemini!`, 'success')
    await fetchPipelineState()
    emit('updated')
  } catch (err) {
    swal.error('Erro ao regenerar cena', err.response?.data?.detail || err.message)
  } finally {
    regeneratingScene.value = null
  }
}

// Quando abre o modal, define a aba inicial e carrega estado dos 5 agentes
watch(
  () => [props.isOpen, props.task?.id],
  ([open]) => {
    if (open) {
      document.body.style.overflow = 'hidden'
      // Se houver entregável, foca nele, senão foca no briefing
      if (props.task?.result) {
        activeTab.value = 'deliverable'
      } else {
        activeTab.value = 'briefing'
      }
      activeImagePreview.value = null
      fetchPipelineState()
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
            <!-- BLOCO 0: PAINEL DE CONTROLE DOS 5 AGENTES ESPECIALIZADOS -->
            <div v-if="isPipelineTask && pipelineData?.stages?.length" class="p-4 rounded-2xl bg-slate-950/90 border border-indigo-500/30 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h4 class="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <span>🤖</span>
                    <span>Pipeline Multi-Agente (5 Especialistas)</span>
                  </h4>
                  <p class="text-[11px] text-slate-400">
                    Re-execute qualquer agente isoladamente ou aprove o roteiro para gerar cenas via Gemini, narração, legendas e montagem.
                  </p>
                </div>
                <button
                  v-if="!pipelineData.script_approved && (pipelineData.stages[0]?.manifest_status === 'completed' || task.status === 'awaiting_supervision')"
                  type="button"
                  @click="handleApproveScriptAndContinue"
                  :disabled="runningStage !== null"
                  class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold shadow-lg shadow-emerald-600/20 transition disabled:opacity-50"
                >
                  {{ runningStage === 'continue' ? '⏳ Liberando Agentes...' : '✅ Aprovar Roteiro & Gerar Vídeo (Agentes 2–5)' }}
                </button>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-5 gap-2">
                <div
                  v-for="st in pipelineData.stages"
                  :key="st.stage"
                  class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-2"
                >
                  <div class="space-y-1">
                    <div class="flex items-center justify-between">
                      <span class="text-[10px] font-bold text-white">{{ st.short_label }}</span>
                      <span
                        class="w-2 h-2 rounded-full"
                        :class="st.manifest_status === 'completed' ? 'bg-emerald-400' : st.subtask?.status === 'in_progress_agent' ? 'bg-indigo-400 animate-pulse' : st.subtask?.status === 'awaiting_supervision' ? 'bg-amber-400' : 'bg-slate-600'"
                      ></span>
                    </div>
                    <p class="text-[10px] text-slate-400 line-clamp-2">{{ st.description }}</p>
                  </div>
                  <button
                    type="button"
                    @click="handleRunSingleAgent(st.stage, st.stage !== 'script')"
                    :disabled="runningStage !== null"
                    class="w-full py-1 px-2 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white text-[10px] font-semibold transition disabled:opacity-50"
                  >
                    {{ runningStage === st.stage ? '⏳ Rodando...' : '↻ Re-executar' }}
                  </button>
                </div>
              </div>

              <!-- Campo opcional para pedir ajuste específico ao Agente 1 (Roteiro) -->
              <div class="flex items-center gap-2 pt-1">
                <input
                  v-model="scriptRevisionFeedback"
                  type="text"
                  placeholder="Opcional: pedir ajuste ao Agente 1 (ex: deixar gancho mais curto e tom mais documental)..."
                  class="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  v-if="scriptRevisionFeedback.trim()"
                  type="button"
                  @click="handleRunSingleAgent('script', false)"
                  :disabled="runningStage !== null"
                  class="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-bold transition disabled:opacity-50"
                >
                  Refazer Roteiro
                </button>
              </div>
            </div>

            <!-- BLOCO 1: PLAYER DE VÍDEO 9:16, ÁUDIO & GRID DE CENAS -->
            <TaskMediaGallery
              :task-id="task.id"
              :business-id="task.business_id"
              :initial-media="task"
            />

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

                  <!-- Prompt Visual para IA Generativa (Google Gemini) -->
                  <div v-if="it.visual_prompt" class="bg-indigo-950/30 p-3 rounded-lg border border-indigo-500/20 space-y-1">
                    <div class="flex items-center justify-between gap-2">
                      <span class="font-bold text-[10px] uppercase text-indigo-400">🎨 Prompt Visual (Google Gemini 9:16):</span>
                      <div class="flex items-center space-x-2">
                        <button
                          v-if="isPipelineTask"
                          type="button"
                          @click="handleRegenerateScene(idx + 1)"
                          :disabled="regeneratingScene === idx + 1"
                          class="px-2 py-0.5 rounded bg-indigo-600/80 hover:bg-indigo-500 text-white text-[10px] font-semibold transition disabled:opacity-50"
                        >
                          {{ regeneratingScene === idx + 1 ? '⏳ Gerando...' : '🔄 Regenerar Cena' }}
                        </button>
                        <button
                          type="button"
                          @click="copyText(it.visual_prompt, 'Prompt visual copiado!')"
                          class="text-[10px] text-indigo-300 hover:text-white underline font-medium"
                        >
                          Copiar Prompt
                        </button>
                      </div>
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

