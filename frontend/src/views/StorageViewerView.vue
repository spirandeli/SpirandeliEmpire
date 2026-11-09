<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'
import { useBusinessStore } from '@/stores/business'

const swal = useSwal()
const businessStore = useBusinessStore()

const isLoading = ref(true)
const isRefreshing = ref(false)
const storageData = ref({
  total_files: 0,
  total_size_mb: 0,
  videos_count: 0,
  storage_directory: '/app/storage/output',
  groups: [],
  videos: [],
  files: [],
  series_tasks: [],
})

const selectedBusinessFilter = ref('')
const selectedTypeFilter = ref('all')
const searchQuery = ref('')
const activeTab = ref('videos') // 'videos' | 'all_files'
const selectedVideoForPlayer = ref(null)
const videoPlaybackError = ref(false)
const isDispatchingSeries = ref(false)
const renderingTaskIds = ref({})
let pollInterval = null

onMounted(async () => {
  await Promise.all([
    businessStore.fetchBusinesses(),
    loadStorageOutputs(),
  ])
  startAutoPolling()
})

onUnmounted(() => {
  stopAutoPolling()
})

function startAutoPolling() {
  stopAutoPolling()
  pollInterval = setInterval(() => {
    const hasActiveRender = (storageData.value.series_tasks || []).some(
      (t) =>
        t.status === 'in_progress_agent' ||
        ['prompts', 'images', 'tts', 'ffmpeg'].includes(t.stage) ||
        renderingTaskIds.value[t.id]
    )
    if (hasActiveRender && !isRefreshing.value) {
      loadStorageOutputs(false)
    }
  }, 4000)
}

function stopAutoPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

async function loadStorageOutputs(showToast = false) {
  isRefreshing.value = true
  try {
    const res = await api.get('/v1/storage/outputs')
    storageData.value = res.data || {}
    const vids = storageData.value.videos || []

    if (vids.length > 0) {
      if (!selectedVideoForPlayer.value) {
        selectedVideoForPlayer.value = vids[0]
      } else {
        const currentMatch = vids.find(
          (v) => v.relative_path === selectedVideoForPlayer.value.relative_path
        )
        if (!currentMatch) {
          selectedVideoForPlayer.value = vids[0]
        }
      }
    }

    // Limpa flags locais de renderização para tarefas que já concluíram
    for (const st of storageData.value.series_tasks || []) {
      if (st.has_rendered_video || st.stage === 'done') {
        delete renderingTaskIds.value[st.id]
      }
    }

    if (showToast) {
      swal.toast('Galeria de Produção atualizada!', 'success')
    }
  } catch (err) {
    console.error('Erro ao carregar outputs:', err)
    if (showToast) {
      swal.toast('Não foi possível escanear o diretório de outputs.', 'warning')
    }
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

// Filtra as tarefas de série do Kanban
const filteredSeriesTasks = computed(() => {
  let list = storageData.value.series_tasks || []
  if (selectedBusinessFilter.value) {
    list = list.filter((t) => String(t.business_id) === String(selectedBusinessFilter.value))
  }
  return list
})

// Filtra os vídeos
const filteredVideos = computed(() => {
  let list = storageData.value.videos || []
  if (selectedBusinessFilter.value) {
    list = list.filter((v) => String(v.business_id) === String(selectedBusinessFilter.value))
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(
      (v) =>
        v.name.toLowerCase().includes(q) ||
        (v.task_title && v.task_title.toLowerCase().includes(q)) ||
        (v.business_name && v.business_name.toLowerCase().includes(q))
    )
  }
  return list
})

// Filtra todos os arquivos
const filteredFiles = computed(() => {
  let list = storageData.value.files || []
  if (selectedBusinessFilter.value) {
    list = list.filter((f) => String(f.business_id) === String(selectedBusinessFilter.value))
  }
  if (selectedTypeFilter.value !== 'all') {
    list = list.filter((f) => f.type === selectedTypeFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    list = list.filter(
      (f) =>
        f.name.toLowerCase().includes(q) ||
        f.relative_path.toLowerCase().includes(q) ||
        (f.task_title && f.task_title.toLowerCase().includes(q))
    )
  }
  return list
})

function selectVideo(video) {
  videoPlaybackError.value = false
  selectedVideoForPlayer.value = video
  if (window.innerWidth < 768) {
    const el = document.getElementById('main-video-player')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }
}

function selectVideoByTaskId(taskId) {
  const vid = (storageData.value.videos || []).find((v) => Number(v.task_id) === Number(taskId))
  if (vid) {
    activeTab.value = 'videos'
    selectVideo(vid)
  }
}

function handleDownload(file) {
  const url = file.download_url || file.static_url
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', file.name)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  swal.toast(`Download iniciado: ${file.name}`, 'info')
}

async function handleRenderSingleTask(task) {
  renderingTaskIds.value[task.id] = true
  try {
    const res = await api.post(`/v1/storage/tasks/${task.id}/render`)
    swal.toast(res.data.message || `Renderização iniciada para Tarefa #${task.id}!`, 'success')
    await loadStorageOutputs(false)
  } catch (err) {
    delete renderingTaskIds.value[task.id]
    swal.error('Erro ao iniciar renderização', err.response?.data?.detail || err.message)
  }
}

async function handleDispatchDefaultSeries() {
  const bizId = selectedBusinessFilter.value || (businessStore.businesses[0]?.id)
  if (!bizId) {
    swal.warning('Selecione um Venture', 'Cadastre ou selecione um negócio para associar as tarefas da série.')
    return
  }

  const confirmed = await swal.confirm({
    title: 'Iniciar Série 01 - A Queda de Lúcifer?',
    text: 'O sistema criará as 3 tarefas no Kanban (Partes 1, 2 e 3) e iniciará automaticamente a renderização de 20 cenas + narração TTS + FFmpeg.',
    confirmText: 'Sim, criar e renderizar',
    confirmButtonColor: '#10b981',
  })

  if (!confirmed) return

  isDispatchingSeries.value = true
  try {
    const res = await api.post('/v1/storage/series/dispatch', {
      business_id: Number(bizId),
      series_title: 'Série 01 - A Queda de Lúcifer',
      parts_count: 3,
      auto_execute_part_1: true,
    })
    swal.toast(res.data.message || 'Série despachada e renderização iniciada!', 'success')
    await loadStorageOutputs(false)
  } catch (err) {
    swal.error('Erro ao despachar série', err.response?.data?.detail || err.message)
  } finally {
    isDispatchingSeries.value = false
  }
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full gap-3">
        <div>
          <div class="flex items-center space-x-2.5">
            <h1 class="text-lg sm:text-xl font-bold text-white tracking-tight">
              Galeria de Produção & Storage Viewer
            </h1>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              /app/storage/output
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">
            Inspeção visual direta de vídeos (.mp4), narrações (.mp3) e assets gerados pelo pipeline ABVOS
          </p>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Botão Despachar Série -->
          <button
            @click="handleDispatchDefaultSeries"
            :disabled="isDispatchingSeries"
            class="px-3.5 py-2 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-md shadow-emerald-400/20 transition flex items-center space-x-1.5 disabled:opacity-50"
            title="Criar tarefas da Série no Kanban e iniciar renderização"
          >
            <span>🎬</span>
            <span>{{ isDispatchingSeries ? 'Iniciando Pipeline...' : 'Disparar Série (Partes 1, 2 e 3)' }}</span>
          </button>

          <!-- Botão Atualizar -->
          <button
            @click="loadStorageOutputs(true)"
            :disabled="isRefreshing"
            class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition flex items-center justify-center min-w-[38px]"
            title="Recarregar arquivos do disco"
          >
            <svg
              class="w-4 h-4"
              :class="{'animate-spin text-emerald-400': isRefreshing}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Indicadores de Armazenamento e Estatísticas -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-lg">
            🎬
          </div>
          <div>
            <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Vídeos Finais</span>
            <span class="text-base font-bold text-white font-mono">{{ storageData.videos_count || 0 }}</span>
          </div>
        </div>

        <div class="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-lg">
            📁
          </div>
          <div>
            <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Total de Arquivos</span>
            <span class="text-base font-bold text-white font-mono">{{ storageData.total_files || 0 }}</span>
          </div>
        </div>

        <div class="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-lg">
            💾
          </div>
          <div>
            <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Espaço Ocupado</span>
            <span class="text-base font-bold text-white font-mono">{{ storageData.total_size_mb || 0 }} MB</span>
          </div>
        </div>

        <div class="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-lg">
            ⚡
          </div>
          <div>
            <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Formato Nativo</span>
            <span class="text-xs font-bold text-amber-300 font-mono">9:16 (1080x1920)</span>
          </div>
        </div>
      </div>

      <!-- Fila de Produção & Status de Renderização da Série (Kanban -> FFmpeg) -->
      <div
        v-if="filteredSeriesTasks.length > 0"
        class="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-sm">⚡</span>
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-200">
              Pipeline de Renderização de Séries ({{ filteredSeriesTasks.length }})
            </h2>
          </div>
          <span class="text-[11px] text-slate-400">
            20 Cenas x 3s = 60s • TTS + FFmpeg 9:16
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div
            v-for="st in filteredSeriesTasks.slice(0, 6)"
            :key="st.id"
            class="p-3 rounded-xl bg-slate-950 border border-slate-800/90 flex flex-col justify-between space-y-2.5"
          >
            <div>
              <div class="flex items-center justify-between gap-2">
                <span class="text-[10px] font-mono text-slate-400">Task #{{ st.id }}</span>
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                  :class="{
                    'bg-emerald-500/20 text-emerald-300': st.has_rendered_video,
                    'bg-amber-500/20 text-amber-300 animate-pulse': !st.has_rendered_video && (st.status === 'in_progress_agent' || renderingTaskIds[st.id]),
                    'bg-slate-800 text-slate-400': !st.has_rendered_video && st.status !== 'in_progress_agent' && !renderingTaskIds[st.id],
                  }"
                >
                  {{ st.has_rendered_video ? 'Pronto (.mp4)' : (st.status === 'in_progress_agent' || renderingTaskIds[st.id] ? `${st.percent}% Renderizando` : 'Na Fila') }}
                </span>
              </div>
              <h4 class="text-xs font-bold text-slate-100 line-clamp-1 mt-1" :title="st.title">
                {{ st.title }}
              </h4>
              <p class="text-[11px] text-slate-400 line-clamp-1 mt-0.5 font-mono">
                {{ st.status_log || 'Aguardando disparo do pipeline...' }}
              </p>
            </div>

            <!-- Barra de Progresso -->
            <div class="space-y-1.5">
              <div class="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                <div
                  class="h-full transition-all duration-500 rounded-full"
                  :class="st.has_rendered_video ? 'bg-emerald-500' : 'bg-indigo-500'"
                  :style="{ width: `${Math.min(100, Math.max(5, st.percent || 0))}%` }"
                ></div>
              </div>

              <div class="flex items-center justify-end gap-2 pt-0.5">
                <button
                  v-if="st.has_rendered_video"
                  @click="selectVideoByTaskId(st.id)"
                  class="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-bold transition"
                >
                  ▶ Assistir no Player
                </button>
                <button
                  @click="handleRenderSingleTask(st)"
                  :disabled="renderingTaskIds[st.id] || st.status === 'in_progress_agent'"
                  class="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-[10px] font-bold transition disabled:opacity-50"
                >
                  {{ renderingTaskIds[st.id] || st.status === 'in_progress_agent' ? '⏳ Processando...' : (st.has_rendered_video ? '↻ Re-renderizar' : '⚡ Renderizar Agora') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Barra de Filtros e Abas -->
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <!-- Abas de Visualização -->
          <div class="flex items-center space-x-1 p-1 bg-slate-950 rounded-xl border border-slate-800 self-start">
            <button
              @click="activeTab = 'videos'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5"
              :class="activeTab === 'videos' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
            >
              <span>🎬 Galeria de Vídeos</span>
              <span class="px-1.5 py-0.2 rounded text-[10px] bg-slate-900/60 font-mono">{{ filteredVideos.length }}</span>
            </button>
            <button
              @click="activeTab = 'all_files'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5"
              :class="activeTab === 'all_files' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
            >
              <span>📁 Todos os Arquivos (Áudio & Cenas)</span>
              <span class="px-1.5 py-0.2 rounded text-[10px] bg-slate-900/60 font-mono">{{ filteredFiles.length }}</span>
            </button>
          </div>

          <!-- Filtros de Negócio e Busca -->
          <div class="flex flex-wrap items-center gap-2.5">
            <!-- Venture Filter -->
            <select
              v-model="selectedBusinessFilter"
              class="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Todos os Negócios</option>
              <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
                {{ b.name }}
              </option>
            </select>

            <!-- Tipo Filter (se aba all_files) -->
            <select
              v-if="activeTab === 'all_files'"
              v-model="selectedTypeFilter"
              class="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">Todos os Tipos</option>
              <option value="video">Vídeos (.mp4)</option>
              <option value="audio">Áudios (.mp3)</option>
              <option value="image">Cenas (.png/.jpg)</option>
              <option value="subtitle">Legendas (.srt)</option>
            </select>

            <!-- Busca por nome -->
            <div class="relative">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar arquivo ou título..."
                class="w-48 sm:w-60 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                v-if="searchQuery"
                @click="searchQuery = ''"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ESTADO DE CARREGAMENTO -->
      <div v-if="isLoading" class="p-12 text-center">
        <div class="inline-block animate-spin text-3xl mb-3">🎬</div>
        <p class="text-xs text-slate-400">Varrendo recursivamente /app/storage/output...</p>
      </div>

      <!-- ABA 1: GALERIA DE VÍDEOS COM PLAYER PRINCIPAL -->
      <div v-else-if="activeTab === 'videos'" class="space-y-6">
        <!-- SEÇÃO PRINCIPAL: PLAYER EMBUTIDO & LISTAGEM LADO A LADO -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <!-- Coluna Esquerda: Player de Vídeo em Destaque (5 Colunas) -->
          <div id="main-video-player" class="lg:col-span-5 rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-4 shadow-xl shadow-slate-950/50 sticky top-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
              <div class="flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider text-white">
                  Player Cinemático 9:16
                </h3>
              </div>
              <span
                v-if="selectedVideoForPlayer"
                class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold"
              >
                {{ selectedVideoForPlayer.size_mb }} MB
              </span>
            </div>

            <!-- Container do Player HTML5 com Aspect Ratio 9:16 Cinemático -->
            <div class="relative bg-black rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center min-h-[380px] max-h-[520px]">
              <template v-if="selectedVideoForPlayer">
                <video
                  :key="selectedVideoForPlayer.static_url"
                  controls
                  autoplay
                  playsinline
                  preload="metadata"
                  class="w-full h-full max-h-[500px] object-contain mx-auto"
                  @error="videoPlaybackError = true"
                  @loadeddata="videoPlaybackError = false"
                >
                  <source :src="selectedVideoForPlayer.static_url" type="video/mp4" />
                  Seu navegador não suporta reprodução de vídeo HTML5.
                </video>
                <div
                  v-if="videoPlaybackError"
                  class="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-6 text-center space-y-2"
                >
                  <span class="text-2xl">⚠️</span>
                  <p class="text-xs font-bold text-slate-200">Não foi possível reproduzir este arquivo de vídeo.</p>
                  <p class="text-[11px] text-slate-400">O arquivo pode ainda estar sendo gravado pelo FFmpeg ou ser um artefato de teste.</p>
                </div>
              </template>
              <div v-else class="p-8 text-center text-slate-500 space-y-2">
                <div class="text-3xl">🎞️</div>
                <p class="text-xs">Selecione um vídeo na galeria para assistir</p>
              </div>
            </div>

            <!-- Metadados e Botão de Download 1-Clique -->
            <div v-if="selectedVideoForPlayer" class="space-y-3 pt-1">
              <div>
                <h4 class="text-sm font-black text-white leading-snug">
                  {{ selectedVideoForPlayer.task_title || selectedVideoForPlayer.name }}
                </h4>
                <div class="flex flex-wrap items-center gap-2 text-[11px] text-slate-400 mt-1 font-mono">
                  <span v-if="selectedVideoForPlayer.business_name">
                    Venture: <strong class="text-emerald-400">{{ selectedVideoForPlayer.business_name }}</strong>
                  </span>
                  <span v-if="selectedVideoForPlayer.business_name">•</span>
                  <span>Arquivo: <strong class="text-slate-200">{{ selectedVideoForPlayer.name }}</strong></span>
                  <span>•</span>
                  <span>Modificado: {{ new Date(selectedVideoForPlayer.modified_at).toLocaleDateString() }}</span>
                </div>
              </div>

              <div class="flex items-center space-x-2 pt-1">
                <!-- Botão de Download com 1 Clique Direto pelo Navegador -->
                <button
                  @click="handleDownload(selectedVideoForPlayer)"
                  class="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 transition flex items-center justify-center space-x-2"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>Baixar Vídeo (.mp4)</span>
                </button>

                <!-- Abrir em nova aba -->
                <a
                  :href="selectedVideoForPlayer.static_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white transition"
                  title="Abrir URL estática em nova aba"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>
          </div>

          <!-- Coluna Direita: Grid dos Vídeos Gerados (7 Colunas) -->
          <div class="lg:col-span-7 space-y-4">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold uppercase tracking-wider text-slate-400">
                Vídeos Disponíveis em /app/storage/output ({{ filteredVideos.length }})
              </h2>
              <span class="text-[11px] text-slate-500">Clique para inspecionar e dar play</span>
            </div>

            <!-- Estado Vazio -->
            <div
              v-if="filteredVideos.length === 0"
              class="p-10 rounded-2xl bg-slate-900 border border-dashed border-slate-800 text-center space-y-3"
            >
              <div class="text-4xl">🎬</div>
              <h3 class="text-sm font-bold text-slate-200">Nenhum vídeo renderizado encontrado para este filtro</h3>
              <p class="text-xs text-slate-400 max-w-md mx-auto">
                Inicie uma série para disparar o pipeline autônomo com 20 cenas, narração TTS e compilação FFmpeg.
              </p>
              <button
                @click="handleDispatchDefaultSeries"
                :disabled="isDispatchingSeries"
                class="px-4 py-2 rounded-xl bg-emerald-400 text-slate-950 font-bold text-xs shadow hover:bg-emerald-300 transition disabled:opacity-50"
              >
                {{ isDispatchingSeries ? 'Iniciando Pipeline...' : 'Disparar Série 01 - A Queda de Lúcifer' }}
              </button>
            </div>

            <!-- Grid de Cards de Vídeo -->
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div
                v-for="v in filteredVideos"
                :key="v.relative_path"
                @click="selectVideo(v)"
                class="p-3.5 rounded-xl bg-slate-900 border transition cursor-pointer space-y-2.5 relative group"
                :class="selectedVideoForPlayer?.relative_path === v.relative_path
                  ? 'border-emerald-500 bg-slate-900/90 shadow-md shadow-emerald-500/10'
                  : 'border-slate-800 hover:border-slate-700 hover:bg-slate-850'"
              >
                <!-- Thumbnail Preview com Mini-Player ou Ícone -->
                <div class="relative bg-black rounded-lg aspect-[9/16] max-h-48 overflow-hidden flex items-center justify-center border border-slate-800 group-hover:border-slate-700">
                  <video
                    :src="v.static_url"
                    preload="metadata"
                    muted
                    playsinline
                    class="w-full h-full object-cover"
                  ></video>
                  <div class="absolute inset-0 bg-slate-950/40 flex items-center justify-center opacity-80 group-hover:opacity-100 transition">
                    <div class="w-10 h-10 rounded-full bg-emerald-500/90 text-slate-950 flex items-center justify-center font-bold text-sm shadow-lg transform group-hover:scale-110 transition">
                      ▶
                    </div>
                  </div>
                  <span class="absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-950/80 text-white">
                    {{ v.size_mb }} MB
                  </span>
                </div>

                <!-- Detalhes do Card -->
                <div>
                  <h4 class="text-xs font-bold text-slate-100 line-clamp-1 group-hover:text-emerald-400 transition">
                    {{ v.task_title || v.name }}
                  </h4>
                  <div class="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                    <span class="font-mono truncate">{{ v.business_name || `Biz #${v.business_id}` }} • Task #{{ v.task_id || '•' }}</span>
                    <span>{{ new Date(v.modified_at).toLocaleDateString() }}</span>
                  </div>
                </div>

                <!-- Botões de Ação Rápida -->
                <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2" @click.stop>
                  <button
                    @click.stop="selectVideo(v)"
                    class="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-[10px] font-bold transition flex items-center space-x-1"
                  >
                    <span>▶ Play</span>
                  </button>

                  <button
                    @click.stop="handleDownload(v)"
                    class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] font-bold transition flex items-center space-x-1"
                    title="Baixar arquivo .mp4"
                  >
                    <span>⬇ Baixar</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ABA 2: TODOS OS ARQUIVOS (ÁUDIOS, CENAS E LEGENDAS) -->
      <div v-else class="space-y-4">
        <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="border-b border-slate-800 text-[11px] text-slate-400 uppercase font-semibold">
                <th class="py-2.5 px-3">Tipo</th>
                <th class="py-2.5 px-3">Nome do Arquivo</th>
                <th class="py-2.5 px-3">Venture / Task</th>
                <th class="py-2.5 px-3">Tamanho</th>
                <th class="py-2.5 px-3">Modificado</th>
                <th class="py-2.5 px-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60 font-mono">
              <tr v-if="filteredFiles.length === 0">
                <td colspan="6" class="py-8 text-center text-slate-500">
                  Nenhum arquivo encontrado para os filtros selecionados.
                </td>
              </tr>
              <tr
                v-for="f in filteredFiles"
                :key="f.relative_path"
                class="hover:bg-slate-850/60 transition"
              >
                <td class="py-2.5 px-3">
                  <span
                    class="px-2 py-0.5 rounded text-[10px] uppercase font-bold"
                    :class="{
                      'bg-indigo-500/20 text-indigo-300': f.type === 'video',
                      'bg-emerald-500/20 text-emerald-300': f.type === 'audio',
                      'bg-sky-500/20 text-sky-300': f.type === 'image',
                      'bg-amber-500/20 text-amber-300': f.type === 'subtitle',
                    }"
                  >
                    {{ f.type }}
                  </span>
                </td>
                <td class="py-2.5 px-3 font-semibold text-slate-200">
                  <div class="truncate max-w-xs">{{ f.name }}</div>
                  <div class="text-[10px] text-slate-500 truncate">{{ f.relative_path }}</div>
                </td>
                <td class="py-2.5 px-3 text-slate-400">
                  <div class="text-slate-300 truncate max-w-[200px]">{{ f.business_name || `Biz #${f.business_id || '•'}` }}</div>
                  <div class="text-[10px] text-slate-500 truncate max-w-[200px]">{{ f.task_title || `Task #${f.task_id || '•'}` }}</div>
                </td>
                <td class="py-2.5 px-3 text-slate-300">
                  {{ f.size_mb }} MB
                </td>
                <td class="py-2.5 px-3 text-slate-400 text-[11px]">
                  {{ new Date(f.modified_at).toLocaleString() }}
                </td>
                <td class="py-2.5 px-3 text-right space-x-1.5">
                  <a
                    :href="f.static_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] transition inline-block"
                  >
                    Abrir
                  </a>
                  <button
                    @click="handleDownload(f)"
                    class="px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/40 text-emerald-300 text-[10px] font-bold transition"
                  >
                    Download
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
