<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'

const props = defineProps({
  businessId: { type: [Number, String], required: true },
  business: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['counts'])

const swal = useSwal()

const isLoading = ref(true)
const isRefreshing = ref(false)
const isDeletingBatch = ref(false)
const isDispatchingSeries = ref(false)
const storageData = ref({ total_files: 0, total_size_mb: 0, videos_count: 0, videos: [], files: [], series_tasks: [] })

const subTab = ref('videos') // 'videos' | 'files'
const typeFilter = ref('all')
const searchQuery = ref('')
const selectedVideo = ref(null)
const videoPlaybackError = ref(false)
const renderingTaskIds = ref({})
const selectedFilePaths = ref([])
const lightboxFile = ref(null)
let pollInterval = null

onMounted(async () => {
  await loadOutputs()
  pollInterval = setInterval(() => {
    const hasActiveRender = (storageData.value.series_tasks || []).some(
      (t) => t.status === 'in_progress_agent' || ['prompts', 'images', 'tts', 'ffmpeg'].includes(t.stage) || renderingTaskIds.value[t.id]
    )
    if (hasActiveRender && !isRefreshing.value) loadOutputs()
  }, 4000)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.businessId, () => {
  selectedVideo.value = null
  loadOutputs()
})

async function loadOutputs(showToast = false) {
  isRefreshing.value = true
  try {
    const res = await api.get('/v1/storage/outputs', { params: { business_id: Number(props.businessId) } })
    storageData.value = res.data || {}
    const vids = storageData.value.videos || []
    if (vids.length) {
      const current = selectedVideo.value && vids.find((v) => v.relative_path === selectedVideo.value.relative_path)
      selectedVideo.value = current || vids[0]
    } else {
      selectedVideo.value = null
    }
    const existing = new Set((storageData.value.files || []).map((f) => f.relative_path))
    selectedFilePaths.value = selectedFilePaths.value.filter((p) => existing.has(p))
    for (const st of storageData.value.series_tasks || []) {
      if (st.has_rendered_video || st.stage === 'done' || st.stage === 'failed') delete renderingTaskIds.value[st.id]
    }
    emit('counts', { videos: vids.length, files: (storageData.value.files || []).length })
    if (showToast) swal.toast('Galeria atualizada!', 'success')
  } catch (err) {
    if (showToast) swal.toast('Não foi possível carregar os arquivos deste negócio.', 'warning')
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

function matchesSearch(f) {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return true
  return (
    f.name.toLowerCase().includes(q) ||
    (f.task_title && f.task_title.toLowerCase().includes(q)) ||
    f.relative_path.toLowerCase().includes(q)
  )
}

const videos = computed(() => (storageData.value.videos || []).filter(matchesSearch))
const files = computed(() => {
  let list = storageData.value.files || []
  if (typeFilter.value !== 'all') list = list.filter((f) => f.type === typeFilter.value)
  return list.filter(matchesSearch)
})
const seriesTasks = computed(() => storageData.value.series_tasks || [])

const selectedVideoAssets = computed(() => {
  if (!selectedVideo.value) return { scenes: [], audio: null }
  const tId = Number(selectedVideo.value.task_id)
  const taskFiles = (storageData.value.files || []).filter((f) => Number(f.task_id) === tId)
  return {
    scenes: taskFiles.filter((f) => f.type === 'image').sort((a, b) => a.name.localeCompare(b.name)),
    audio: taskFiles.find((f) => f.type === 'audio') || null,
  }
})

const navigableImages = computed(() => {
  if (subTab.value === 'videos' && selectedVideoAssets.value.scenes.length) return selectedVideoAssets.value.scenes
  return files.value.filter((f) => f.type === 'image')
})

const allFilteredSelected = computed(
  () => files.value.length > 0 && files.value.every((f) => selectedFilePaths.value.includes(f.relative_path))
)

function toggleSelectAll() {
  if (allFilteredSelected.value) {
    const set = new Set(files.value.map((f) => f.relative_path))
    selectedFilePaths.value = selectedFilePaths.value.filter((p) => !set.has(p))
  } else {
    selectedFilePaths.value = Array.from(new Set([...selectedFilePaths.value, ...files.value.map((f) => f.relative_path)]))
  }
}

function toggleFile(path) {
  const idx = selectedFilePaths.value.indexOf(path)
  if (idx >= 0) selectedFilePaths.value.splice(idx, 1)
  else selectedFilePaths.value.push(path)
}

function selectVideo(v) {
  videoPlaybackError.value = false
  selectedVideo.value = v
  subTab.value = 'videos'
  if (window.innerWidth < 1024) {
    document.getElementById('biz-video-player')?.scrollIntoView({ behavior: 'smooth' })
  }
}

function selectVideoByTaskId(taskId) {
  const v = (storageData.value.videos || []).find((x) => Number(x.task_id) === Number(taskId))
  if (v) selectVideo(v)
}

function openLightbox(f) { lightboxFile.value = f }
function closeLightbox() { lightboxFile.value = null }
function stepLightbox(delta) {
  const imgs = navigableImages.value
  if (!lightboxFile.value || imgs.length <= 1) return
  const idx = imgs.findIndex((i) => i.relative_path === lightboxFile.value.relative_path)
  if (idx === -1) return
  lightboxFile.value = imgs[(idx + delta + imgs.length) % imgs.length]
}
function handleKeydown(e) {
  if (!lightboxFile.value) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowRight') stepLightbox(1)
  if (e.key === 'ArrowLeft') stepLightbox(-1)
}

function handleDownload(file) {
  const link = document.createElement('a')
  link.href = file.download_url || file.static_url
  link.setAttribute('download', file.name)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  swal.toast(`Download iniciado: ${file.name}`, 'info')
}

async function handleDeleteFile(file) {
  const ok = await swal.confirm({
    title: `Excluir "${file.name}"?`,
    text: `O arquivo (${file.size_mb} MB) será removido permanentemente do storage.`,
    confirmText: 'Sim, excluir',
    confirmButtonColor: '#ef4444',
  })
  if (!ok) return
  try {
    await api.delete('/v1/storage/files', { params: { path: file.relative_path } })
    if (lightboxFile.value?.relative_path === file.relative_path) closeLightbox()
    swal.toast('Arquivo excluído.', 'success')
    await loadOutputs()
  } catch (err) {
    swal.error('Erro ao excluir arquivo', err.response?.data?.detail || err.message)
  }
}

async function handleDeleteBatch() {
  const count = selectedFilePaths.value.length
  if (!count) return
  const ok = await swal.confirm({
    title: `Excluir ${count} arquivo(s)?`,
    text: 'Os arquivos marcados serão removidos permanentemente do storage.',
    confirmText: `Sim, excluir ${count}`,
    confirmButtonColor: '#ef4444',
  })
  if (!ok) return
  isDeletingBatch.value = true
  try {
    const res = await api.post('/v1/storage/files/delete-batch', { paths: selectedFilePaths.value })
    selectedFilePaths.value = []
    swal.toast(res.data?.message || 'Arquivos excluídos.', 'success')
    await loadOutputs()
  } catch (err) {
    swal.error('Erro na exclusão em lote', err.response?.data?.detail || err.message)
  } finally {
    isDeletingBatch.value = false
  }
}

async function handleDeleteTaskFiles(taskId, title = '') {
  const ok = await swal.confirm({
    title: `Limpar arquivos da Task #${taskId}?`,
    text: `Remove vídeo, narração, legendas e cenas de "${title || `Task #${taskId}`}".`,
    confirmText: 'Sim, limpar',
    confirmButtonColor: '#ef4444',
  })
  if (!ok) return
  try {
    const res = await api.delete(`/v1/storage/tasks/${taskId}/files`)
    swal.toast(res.data?.message || 'Arquivos removidos.', 'success')
    await loadOutputs()
  } catch (err) {
    swal.error('Erro ao limpar arquivos', err.response?.data?.detail || err.message)
  }
}

async function handleRenderTask(task) {
  renderingTaskIds.value[task.id] = true
  try {
    const res = await api.post(`/v1/storage/tasks/${task.id}/render`)
    swal.toast(res.data?.message || `Renderização iniciada para a Task #${task.id}!`, 'success')
    await loadOutputs()
  } catch (err) {
    delete renderingTaskIds.value[task.id]
    swal.error('Erro ao iniciar renderização', err.response?.data?.detail || err.message)
  }
}

async function handleDispatchSeries() {
  const ok = await swal.confirm({
    title: 'Disparar série de vídeos neste negócio?',
    text: 'Cria 3 tarefas no Kanban (Partes 1, 2 e 3) e inicia a renderização da Parte 1 (cenas + narração + FFmpeg).',
    confirmText: 'Sim, criar e renderizar',
    confirmButtonColor: '#10b981',
  })
  if (!ok) return
  isDispatchingSeries.value = true
  try {
    const res = await api.post('/v1/storage/series/dispatch', {
      business_id: Number(props.businessId),
      series_title: 'Série 01 - A Queda de Lúcifer',
      parts_count: 3,
      auto_execute_part_1: true,
    })
    swal.toast(res.data?.message || 'Série despachada!', 'success')
    await loadOutputs()
  } catch (err) {
    swal.error('Erro ao despachar série', err.response?.data?.detail || err.message)
  } finally {
    isDispatchingSeries.value = false
  }
}

function renderStatusLabel(st) {
  if (st.has_rendered_video) return 'Pronto (.mp4)'
  if (st.stage === 'failed') return 'Falhou'
  if (st.status === 'in_progress_agent' || renderingTaskIds.value[st.id]) return `${st.percent || 0}% renderizando`
  return 'Na fila'
}
</script>

<template>
  <div class="space-y-5">
    <!-- Cabeçalho + Estatísticas -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <div class="min-w-0">
        <h3 class="text-base font-bold text-white">Galeria de Vídeos &amp; Arquivos</h3>
        <p class="text-xs text-slate-400 mt-0.5">Tudo que foi produzido para <strong class="text-slate-200">{{ business.name || 'este negócio' }}</strong>: vídeos, narrações, cenas e legendas.</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          @click="handleDispatchSeries"
          :disabled="isDispatchingSeries"
          class="px-3.5 py-2 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 transition disabled:opacity-50 whitespace-nowrap"
        >
          {{ isDispatchingSeries ? 'Iniciando...' : '🎬 Disparar Série' }}
        </button>
        <button
          @click="loadOutputs(true)"
          :disabled="isRefreshing"
          class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition min-w-[38px] flex items-center justify-center"
          title="Recarregar arquivos"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin text-emerald-400': isRefreshing }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <div class="p-3 rounded-xl bg-slate-900 border border-slate-800">
        <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Vídeos</span>
        <span class="text-base font-bold text-white font-mono">{{ storageData.videos_count || 0 }}</span>
      </div>
      <div class="p-3 rounded-xl bg-slate-900 border border-slate-800">
        <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Arquivos</span>
        <span class="text-base font-bold text-white font-mono">{{ storageData.total_files || 0 }}</span>
      </div>
      <div class="p-3 rounded-xl bg-slate-900 border border-slate-800">
        <span class="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block">Espaço</span>
        <span class="text-base font-bold text-white font-mono">{{ storageData.total_size_mb || 0 }} MB</span>
      </div>
    </div>

    <!-- Fila de renderização -->
    <div v-if="seriesTasks.length" class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
      <h4 class="text-xs font-bold uppercase tracking-wider text-slate-300">⚡ Fila de Renderização ({{ seriesTasks.length }})</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        <div v-for="st in seriesTasks.slice(0, 6)" :key="st.id" class="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <span class="text-[10px] font-mono text-slate-400">Task #{{ st.id }}</span>
            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap"
              :class="st.has_rendered_video ? 'bg-emerald-500/20 text-emerald-300'
                : st.stage === 'failed' ? 'bg-rose-500/20 text-rose-300'
                : (st.status === 'in_progress_agent' || renderingTaskIds[st.id]) ? 'bg-amber-500/20 text-amber-300 animate-pulse'
                : 'bg-slate-800 text-slate-400'"
            >{{ renderStatusLabel(st) }}</span>
          </div>
          <h5 class="text-xs font-bold text-slate-100 truncate" :title="st.title">{{ st.title }}</h5>
          <p class="text-[11px] text-slate-500 truncate font-mono" :title="st.status_log">{{ st.status_log || 'Aguardando disparo...' }}</p>
          <div class="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="st.has_rendered_video ? 'bg-emerald-500' : st.stage === 'failed' ? 'bg-rose-500' : 'bg-indigo-500'"
              :style="{ width: `${Math.min(100, Math.max(5, st.percent || 0))}%` }"
            ></div>
          </div>
          <div class="flex items-center justify-end gap-1.5 flex-wrap">
            <button v-if="st.has_rendered_video" @click="selectVideoByTaskId(st.id)" class="px-2.5 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-[10px] font-bold">▶ Assistir</button>
            <button
              @click="handleRenderTask(st)"
              :disabled="renderingTaskIds[st.id] || st.status === 'in_progress_agent'"
              class="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-[10px] font-bold disabled:opacity-50"
            >{{ renderingTaskIds[st.id] || st.status === 'in_progress_agent' ? '⏳ Processando' : st.has_rendered_video ? '↻ Re-renderizar' : '⚡ Renderizar' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Sub-abas + filtros -->
    <div class="p-3 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div class="flex items-center gap-1 p-1 bg-slate-950 rounded-xl border border-slate-800 self-start">
        <button
          @click="subTab = 'videos'"
          class="px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap"
          :class="subTab === 'videos' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
        >🎬 Vídeos <span class="font-mono text-[10px] opacity-80">{{ videos.length }}</span></button>
        <button
          @click="subTab = 'files'"
          class="px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap"
          :class="subTab === 'files' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
        >📁 Todos os Arquivos <span class="font-mono text-[10px] opacity-80">{{ files.length }}</span></button>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select
          v-if="subTab === 'files'"
          v-model="typeFilter"
          class="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
        >
          <option value="all">Todos os tipos</option>
          <option value="video">Vídeos</option>
          <option value="audio">Áudios</option>
          <option value="image">Cenas</option>
          <option value="subtitle">Legendas</option>
        </select>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar arquivo ou título..."
          class="w-full sm:w-56 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
        />
      </div>
    </div>

    <div v-if="isLoading" class="p-12 text-center text-xs text-slate-400">Carregando arquivos do negócio...</div>

    <!-- Vídeos -->
    <div v-else-if="subTab === 'videos'">
      <div v-if="videos.length === 0" class="p-10 rounded-2xl bg-slate-900 border border-dashed border-slate-800 text-center space-y-3">
        <div class="text-4xl">🎬</div>
        <h4 class="text-sm font-bold text-slate-200">Nenhum vídeo renderizado para este negócio ainda</h4>
        <p class="text-xs text-slate-400 max-w-md mx-auto">Dispare uma série ou execute uma tarefa de vídeo para gerar cenas, narração e o .mp4 final.</p>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <!-- Player -->
        <div id="biz-video-player" class="lg:col-span-5 rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-4 lg:sticky lg:top-4 min-w-0">
          <div class="relative bg-black rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center aspect-[9/16] max-h-[520px] mx-auto">
            <template v-if="selectedVideo">
              <video
                :key="selectedVideo.static_url"
                controls
                playsinline
                preload="metadata"
                class="w-full h-full object-contain"
                @error="videoPlaybackError = true"
                @loadeddata="videoPlaybackError = false"
              >
                <source :src="selectedVideo.static_url" type="video/mp4" />
              </video>
              <div v-if="videoPlaybackError" class="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-6 text-center space-y-2">
                <span class="text-2xl">⚠️</span>
                <p class="text-xs font-bold text-slate-200">Não foi possível reproduzir este vídeo.</p>
                <p class="text-[11px] text-slate-400">Ele pode ainda estar sendo gerado ou estar corrompido.</p>
              </div>
            </template>
          </div>

          <div v-if="selectedVideo" class="space-y-3">
            <div class="min-w-0">
              <h4 class="text-sm font-bold text-white leading-snug break-words">{{ selectedVideo.task_title || selectedVideo.name }}</h4>
              <p class="text-[11px] text-slate-400 font-mono mt-1">
                Task #{{ selectedVideo.task_id || '•' }} · {{ selectedVideo.size_mb }} MB · {{ new Date(selectedVideo.modified_at).toLocaleString('pt-BR') }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button @click="handleDownload(selectedVideo)" class="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-bold text-xs">⬇ Baixar .mp4</button>
              <button @click="handleDeleteFile(selectedVideo)" class="px-3 py-2.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/30 border border-rose-500/30 text-rose-300 font-bold text-xs">🗑️</button>
              <a :href="selectedVideo.static_url" target="_blank" rel="noopener noreferrer" class="px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs" title="Abrir em nova aba">↗</a>
            </div>

            <div v-if="selectedVideoAssets.audio" class="pt-3 border-t border-slate-800 space-y-1">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-slate-300">🎙️ Narração ({{ selectedVideoAssets.audio.size_mb }} MB)</span>
                <button @click="handleDownload(selectedVideoAssets.audio)" class="text-emerald-400 hover:underline text-[10px]">Baixar .mp3</button>
              </div>
              <audio :src="selectedVideoAssets.audio.static_url" controls class="w-full h-8"></audio>
            </div>

            <div v-if="selectedVideoAssets.scenes.length" class="pt-3 border-t border-slate-800 space-y-2">
              <span class="text-[11px] font-bold text-slate-300">🖼️ Cenas ({{ selectedVideoAssets.scenes.length }}) — clique para ampliar</span>
              <div class="grid grid-cols-5 gap-1.5 max-h-48 overflow-y-auto p-1 bg-slate-950 rounded-xl border border-slate-800">
                <button
                  v-for="(sc, idx) in selectedVideoAssets.scenes"
                  :key="sc.relative_path"
                  @click="openLightbox(sc)"
                  class="relative aspect-[9/16] rounded-lg overflow-hidden border border-slate-800 hover:border-emerald-400"
                >
                  <img :src="sc.static_url" :alt="sc.name" loading="lazy" class="w-full h-full object-cover" />
                  <span class="absolute bottom-0.5 right-0.5 px-1 rounded bg-black/80 text-[8px] font-mono text-white">#{{ idx + 1 }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Grid de vídeos -->
        <div class="lg:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-3 min-w-0">
          <div
            v-for="v in videos"
            :key="v.relative_path"
            @click="selectVideo(v)"
            class="p-2.5 rounded-xl bg-slate-900 border transition cursor-pointer space-y-2 group min-w-0"
            :class="selectedVideo?.relative_path === v.relative_path ? 'border-emerald-500 shadow-md shadow-emerald-500/10' : 'border-slate-800 hover:border-slate-700'"
          >
            <div class="relative bg-black rounded-lg aspect-[9/16] overflow-hidden border border-slate-800">
              <video :src="v.static_url" preload="metadata" muted playsinline class="w-full h-full object-cover"></video>
              <div class="absolute inset-0 bg-slate-950/30 flex items-center justify-center opacity-80 group-hover:opacity-100 transition">
                <div class="w-9 h-9 rounded-full bg-emerald-500/90 text-slate-950 flex items-center justify-center font-bold text-sm">▶</div>
              </div>
              <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-950/80 text-white">{{ v.size_mb }} MB</span>
            </div>
            <h5 class="text-xs font-bold text-slate-100 truncate group-hover:text-emerald-400" :title="v.task_title || v.name">{{ v.task_title || v.name }}</h5>
            <div class="flex items-center justify-between gap-1" @click.stop>
              <span class="text-[10px] text-slate-500 font-mono truncate">{{ new Date(v.modified_at).toLocaleDateString('pt-BR') }}</span>
              <div class="flex items-center gap-1 shrink-0">
                <button @click.stop="handleDownload(v)" class="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]" title="Baixar">⬇</button>
                <button v-if="v.task_id" @click.stop="handleDeleteTaskFiles(v.task_id, v.task_title || v.name)" class="px-1.5 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/25 text-rose-300 text-[10px]" title="Excluir vídeo e cenas da task">🗑️</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Todos os arquivos -->
    <div v-else class="space-y-3">
      <div v-if="selectedFilePaths.length" class="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 flex flex-wrap items-center justify-between gap-3">
        <span class="text-xs text-rose-200 font-semibold">🗑️ {{ selectedFilePaths.length }} arquivo(s) selecionado(s)</span>
        <div class="flex items-center gap-2">
          <button @click="selectedFilePaths = []" class="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs">Desmarcar</button>
          <button @click="handleDeleteBatch" :disabled="isDeletingBatch" class="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs disabled:opacity-50">
            {{ isDeletingBatch ? 'Excluindo...' : `Excluir (${selectedFilePaths.length})` }}
          </button>
        </div>
      </div>

      <div class="rounded-2xl bg-slate-900 border border-slate-800 overflow-x-auto">
        <table class="w-full min-w-[640px] text-left text-xs">
          <thead>
            <tr class="border-b border-slate-800 text-[11px] text-slate-400 uppercase font-semibold">
              <th class="py-2.5 px-3 w-8">
                <input type="checkbox" :checked="allFilteredSelected" @change="toggleSelectAll" class="rounded border-slate-700 bg-slate-950 cursor-pointer" />
              </th>
              <th class="py-2.5 px-3">Tipo</th>
              <th class="py-2.5 px-3">Arquivo</th>
              <th class="py-2.5 px-3">Tarefa</th>
              <th class="py-2.5 px-3">Tamanho</th>
              <th class="py-2.5 px-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr v-if="files.length === 0">
              <td colspan="6" class="py-8 text-center text-slate-500">Nenhum arquivo encontrado para este negócio.</td>
            </tr>
            <tr
              v-for="f in files"
              :key="f.relative_path"
              :class="{ 'bg-indigo-950/20': selectedFilePaths.includes(f.relative_path) }"
            >
              <td class="py-2.5 px-3">
                <input type="checkbox" :checked="selectedFilePaths.includes(f.relative_path)" @change="toggleFile(f.relative_path)" class="rounded border-slate-700 bg-slate-950 cursor-pointer" />
              </td>
              <td class="py-2.5 px-3">
                <div class="flex items-center gap-2">
                  <button v-if="f.type === 'image'" @click="openLightbox(f)" class="w-8 h-12 rounded overflow-hidden border border-slate-700 hover:border-emerald-400 shrink-0">
                    <img :src="f.static_url" :alt="f.name" loading="lazy" class="w-full h-full object-cover" />
                  </button>
                  <span
                    class="px-2 py-0.5 rounded text-[10px] uppercase font-bold"
                    :class="{
                      'bg-indigo-500/20 text-indigo-300': f.type === 'video',
                      'bg-emerald-500/20 text-emerald-300': f.type === 'audio',
                      'bg-sky-500/20 text-sky-300': f.type === 'image',
                      'bg-amber-500/20 text-amber-300': f.type === 'subtitle',
                    }"
                  >{{ f.type }}</span>
                </div>
              </td>
              <td class="py-2.5 px-3 font-mono">
                <div class="truncate max-w-[220px] text-slate-200 font-semibold" :title="f.name">{{ f.name }}</div>
                <div v-if="f.type === 'audio'" class="mt-1.5 max-w-[220px]">
                  <audio :src="f.static_url" controls preload="none" class="w-full h-7"></audio>
                </div>
              </td>
              <td class="py-2.5 px-3 text-slate-400">
                <div class="truncate max-w-[200px]" :title="f.task_title">{{ f.task_title || `Task #${f.task_id || '•'}` }}</div>
              </td>
              <td class="py-2.5 px-3 text-slate-300 font-mono whitespace-nowrap">{{ f.size_mb }} MB</td>
              <td class="py-2.5 px-3 text-right whitespace-nowrap space-x-1">
                <button v-if="f.type === 'image'" @click="openLightbox(f)" class="px-2 py-1 rounded bg-sky-500/20 text-sky-300 text-[10px] font-bold">Ver</button>
                <button v-else-if="f.type === 'video'" @click="selectVideo(f)" class="px-2 py-1 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-bold">▶ Play</button>
                <button @click="handleDownload(f)" class="px-2 py-1 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">⬇</button>
                <button @click="handleDeleteFile(f)" class="px-2 py-1 rounded bg-rose-500/15 text-rose-300 text-[10px] font-bold">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Lightbox -->
    <div v-if="lightboxFile" class="fixed inset-0 z-50 bg-black/95 backdrop-blur-md flex items-center justify-center p-4" @click="closeLightbox">
      <div class="relative max-w-xl w-full max-h-[92vh] flex flex-col items-center space-y-3" @click.stop>
        <div class="w-full flex items-center justify-between gap-3 text-white border-b border-slate-800 pb-2.5">
          <h4 class="text-xs font-bold truncate">{{ lightboxFile.name }}</h4>
          <div class="flex items-center gap-2 shrink-0">
            <button @click="handleDownload(lightboxFile)" class="px-3 py-1 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs">⬇ Baixar</button>
            <button @click="handleDeleteFile(lightboxFile)" class="px-3 py-1 rounded-lg bg-rose-600 text-white font-bold text-xs">🗑️</button>
            <button @click="closeLightbox" class="p-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-bold">✕</button>
          </div>
        </div>
        <div class="relative w-full flex items-center justify-center">
          <button v-if="navigableImages.length > 1" @click="stepLightbox(-1)" class="absolute left-2 p-2.5 rounded-full bg-black/75 text-white border border-white/20 z-10">◀</button>
          <img :src="lightboxFile.static_url" :alt="lightboxFile.name" class="max-h-[78vh] w-auto rounded-2xl border border-slate-800 object-contain" />
          <button v-if="navigableImages.length > 1" @click="stepLightbox(1)" class="absolute right-2 p-2.5 rounded-full bg-black/75 text-white border border-white/20 z-10">▶</button>
        </div>
      </div>
    </div>
  </div>
</template>

