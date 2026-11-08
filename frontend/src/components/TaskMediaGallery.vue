<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'

const props = defineProps({
  taskId: {
    type: [Number, String],
    default: null,
  },
  businessId: {
    type: [Number, String],
    default: null,
  },
  initialMedia: {
    type: Object,
    default: null,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

const swal = useSwal()
const loading = ref(false)
const media = ref({
  has_media: false,
  video: null,
  audio: null,
  subtitles: [],
  scenes: [],
  files: [],
})

const lightboxIndex = ref(null)

// Resolução inteligente dos dados a partir do initialMedia
function parseInitialMedia(raw) {
  if (!raw) return null
  const source = raw.result?.media || raw.media || raw.result || raw
  const videoObj = source.video || (source.video_url ? { url: source.video_url, name: 'video.mp4' } : null)
  const audioObj = source.audio || (source.audio_url ? { url: source.audio_url, name: 'audio.mp3' } : null)

  const rawScenes = source.scenes || source.images_generated || []
  const scenesList = rawScenes.map((item, idx) => {
    if (typeof item === 'string') {
      return {
        scene_number: idx + 1,
        name: `scene_${String(idx + 1).padStart(2, '0')}.jpg`,
        url: item,
        download_url: item.includes('?') ? `${item}&download=true` : `${item}?download=true`,
      }
    }
    return item
  })

  const subsList = source.subtitles
    ? Array.isArray(source.subtitles)
      ? source.subtitles
      : [
          source.subtitles.srt_url ? { name: 'subtitles.srt', url: source.subtitles.srt_url, type: 'subtitle' } : null,
          source.subtitles.ass_path ? { name: 'subtitles.ass', url: source.subtitles.ass_path, type: 'subtitle' } : null,
        ].filter(Boolean)
    : []

  const has = Boolean(videoObj || audioObj || scenesList.length > 0)
  return {
    has_media: has,
    video: videoObj,
    audio: audioObj,
    subtitles: subsList,
    scenes: scenesList,
    scenes_count: scenesList.length,
    files: source.files || [],
  }
}

async function fetchTaskMedia() {
  if (!props.taskId) return
  loading.value = true
  try {
    const res = await api.get(`/tasks/${props.taskId}/media`)
    const data = res.data?.data
    if (data && data.has_media) {
      media.value = {
        has_media: true,
        video: data.video || media.value.video,
        audio: data.audio || media.value.audio,
        subtitles: data.subtitles?.length ? data.subtitles : media.value.subtitles,
        scenes: data.scenes?.length ? data.scenes : media.value.scenes,
        scenes_count: data.scenes_count || data.scenes?.length || media.value.scenes.length,
        files: data.files || media.value.files,
      }
    }
  } catch (err) {
    // Falha silenciosa caso o endpoint retorne 404 para tasks sem mídia gerada ainda
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.taskId, props.initialMedia],
  () => {
    if (props.initialMedia) {
      const parsed = parseInitialMedia(props.initialMedia)
      if (parsed) {
        media.value = parsed
      }
    }
    if (props.taskId) {
      fetchTaskMedia()
    }
  },
  { immediate: true, deep: true }
)

const videoUrl = computed(() => {
  return media.value.video?.url || null
})

const videoDownloadUrl = computed(() => {
  if (media.value.video?.download_url) return media.value.video.download_url
  if (videoUrl.value) {
    return videoUrl.value.includes('?') ? `${videoUrl.value}&download=true` : `${videoUrl.value}?download=true`
  }
  return null
})

const audioUrl = computed(() => {
  return media.value.audio?.url || null
})

const audioDownloadUrl = computed(() => {
  if (media.value.audio?.download_url) return media.value.audio.download_url
  if (audioUrl.value) {
    return audioUrl.value.includes('?') ? `${audioUrl.value}&download=true` : `${audioUrl.value}?download=true`
  }
  return null
})

const srtUrl = computed(() => {
  const srt = media.value.subtitles?.find((s) => s.name?.endsWith('.srt') || s.type === 'subtitle')
  return srt?.url || srt?.srt_url || null
})

const scenes = computed(() => {
  return media.value.scenes || []
})

const activeLightboxScene = computed(() => {
  if (lightboxIndex.value === null) return null
  return scenes.value[lightboxIndex.value] || null
})

function openLightbox(idx) {
  lightboxIndex.value = idx
}

function closeLightbox() {
  lightboxIndex.value = null
}

function nextScene() {
  if (lightboxIndex.value !== null && lightboxIndex.value < scenes.value.length - 1) {
    lightboxIndex.value++
  } else {
    lightboxIndex.value = 0
  }
}

function prevScene() {
  if (lightboxIndex.value !== null && lightboxIndex.value > 0) {
    lightboxIndex.value--
  } else {
    lightboxIndex.value = scenes.value.length - 1
  }
}

function handleKeydown(e) {
  if (lightboxIndex.value === null) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowRight') nextScene()
  if (e.key === 'ArrowLeft') prevScene()
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function triggerDownload(url, filename) {
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename || 'download')
  link.setAttribute('target', '_blank')
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  swal.toast(`Download iniciado: ${filename}`, 'success')
}
</script>

<template>
  <div class="space-y-5 text-slate-200">
    <!-- Skeleton loader enquanto busca na API -->
    <div v-if="loading && !media.has_media" class="p-6 rounded-2xl bg-slate-900 border border-slate-800 animate-pulse space-y-4">
      <div class="h-6 w-48 bg-slate-800 rounded"></div>
      <div class="h-64 bg-slate-950 rounded-xl"></div>
    </div>

    <!-- Caso SEM MÍDIA DISPONÍVEL -->
    <div
      v-else-if="!media.has_media && !videoUrl && !audioUrl && scenes.length === 0"
      class="p-6 text-center rounded-2xl bg-slate-950/40 border border-dashed border-slate-800 space-y-2 text-slate-400"
    >
      <div class="w-10 h-10 mx-auto rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 text-lg">
        🎬
      </div>
      <p class="text-xs">Nenhum arquivo de mídia renderizado para esta tarefa ainda.</p>
    </div>

    <!-- MÍDIA DISPONÍVEL -->
    <div v-else class="space-y-5">
      <!-- 1. BLOCO PRINCIPAL: PLAYER DE VÍDEO VERTICAL 9:16 + CONTROLES DE DOWNLOAD -->
      <div
        v-if="videoUrl"
        class="rounded-2xl bg-gradient-to-b from-indigo-950/30 via-slate-900 to-slate-950 border border-indigo-500/30 p-4 sm:p-5 shadow-xl space-y-4"
      >
        <!-- Top bar do Player -->
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div class="flex items-center space-x-2.5">
            <span class="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-sm">
              🎬
            </span>
            <div>
              <h3 class="text-sm font-bold text-white flex items-center space-x-2">
                <span>Vídeo Final Compilado (60s)</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Ready
                </span>
              </h3>
              <p class="text-[11px] text-slate-400">Proporção 9:16 Vertical para TikTok, Reels e Shorts</p>
            </div>
          </div>

          <!-- Badges de Especificações Técnicas -->
          <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
            <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {{ media.video?.resolution || '1080x1920' }}
            </span>
            <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              9:16 Vertical
            </span>
            <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              {{ media.video?.duration_seconds ? `${media.video.duration_seconds}s` : '60.0s' }}
            </span>
            <span v-if="media.video?.size_mb" class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {{ media.video.size_mb }} MB
            </span>
          </div>
        </div>

        <!-- PLAYER DE VÍDEO NATIVO -->
        <div class="flex justify-center bg-black/90 rounded-2xl p-3 sm:p-4 border border-slate-800 shadow-inner">
          <video
            :src="videoUrl"
            controls
            playsinline
            preload="metadata"
            class="max-h-[380px] sm:max-h-[460px] w-auto rounded-xl shadow-2xl border border-slate-700/80 bg-black"
          ></video>
        </div>

        <!-- BARRA DE AÇÃO PRINCIPAL: BOTÃO DE DOWNLOAD DIRETO DO VÍDEO -->
        <div class="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div class="flex items-center space-x-2 text-xs text-slate-400">
            <span>💾 Arquivo:</span>
            <code class="text-[11px] text-indigo-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {{ media.video?.name || 'video_final.mp4' }}
            </code>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <!-- Botão de Download Direto em Destaque -->
            <a
              :href="videoDownloadUrl"
              download
              target="_blank"
              class="px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs inline-flex items-center space-x-2 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition transform hover:-translate-y-0.5 active:translate-y-0"
            >
              <svg class="w-4 h-4 text-slate-950" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Baixar Vídeo (.mp4)</span>
              <span v-if="media.video?.size_mb" class="text-[10px] bg-slate-950/20 px-1.5 py-0.5 rounded font-mono">
                {{ media.video.size_mb }}MB
              </span>
            </a>

            <!-- Download de Legendas SRT -->
            <a
              v-if="srtUrl"
              :href="srtUrl.includes('?') ? `${srtUrl}&download=true` : `${srtUrl}?download=true`"
              download
              target="_blank"
              class="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold inline-flex items-center space-x-1.5 border border-slate-700 transition"
              title="Baixar arquivo de legendas .srt"
            >
              <span>📝</span>
              <span>Legenda (.srt)</span>
            </a>
          </div>
        </div>
      </div>

      <!-- 2. BLOCO DE ÁUDIO & NARRAÇÃO -->
      <div
        v-if="audioUrl"
        class="rounded-2xl bg-slate-900 border border-slate-800 p-4 sm:p-5 shadow-lg space-y-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <span class="w-7 h-7 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20 flex items-center justify-center font-bold text-xs">
              🎙️
            </span>
            <div>
              <h4 class="text-xs font-bold text-white">Locução & Narração de Voz</h4>
              <p class="text-[10px] text-slate-400">Sintetizado via ElevenLabs / EdgeTTS com pausas dramáticas</p>
            </div>
          </div>

          <a
            :href="audioDownloadUrl"
            download
            target="_blank"
            class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium inline-flex items-center space-x-1.5 border border-slate-700 transition"
          >
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Baixar Áudio (.mp3)</span>
          </a>
        </div>

        <!-- PLAYER DE ÁUDIO NATIVO -->
        <div class="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
          <audio :src="audioUrl" controls class="w-full h-9 rounded"></audio>
        </div>
      </div>

      <!-- 3. BLOCO DE CENAS VISUAIS: GRID DAS 20 CENAS (9:16) -->
      <div v-if="scenes.length > 0" class="rounded-2xl bg-slate-900 border border-slate-800 p-4 sm:p-5 shadow-lg space-y-3.5">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/70 pb-2.5">
          <div class="flex items-center space-x-2">
            <span class="text-base">🖼️</span>
            <div>
              <h4 class="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <span>Galeria de Cenas Visuais</span>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 lowercase font-mono">
                  {{ scenes.length }} cenas
                </span>
              </h4>
              <p class="text-[10px] text-slate-400">Miniaturas dos frames gerados (clique para ampliar no lightbox)</p>
            </div>
          </div>

          <span class="text-[10px] text-slate-500">Formato 9:16 Cinematic</span>
        </div>

        <!-- GRID DE IMAGENS DAS CENAS -->
        <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2.5 sm:gap-3">
          <div
            v-for="(scene, idx) in scenes"
            :key="idx"
            @click="openLightbox(idx)"
            class="group relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950 hover:border-emerald-500 cursor-pointer transition-all duration-200 aspect-[9/16] shadow-md hover:shadow-emerald-500/10 flex flex-col justify-end"
          >
            <!-- Imagem -->
            <img
              :src="scene.url"
              :alt="scene.name || `Cena ${idx + 1}`"
              loading="lazy"
              class="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />

            <!-- Gradiente de Sobreposição -->
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-black/20 opacity-70 group-hover:opacity-40 transition-opacity"></div>

            <!-- Badges e Ações na Miniatura -->
            <div class="relative p-2 flex items-center justify-between z-10">
              <span class="px-1.5 py-0.5 rounded bg-black/80 text-white font-mono text-[9px] font-bold border border-white/10">
                #{{ String(scene.scene_number || idx + 1).padStart(2, '0') }}
              </span>

              <!-- Botão de Download Rápido da Cena -->
              <a
                :href="scene.download_url || (scene.url.includes('?') ? `${scene.url}&download=true` : `${scene.url}?download=true`)"
                download
                target="_blank"
                @click.stop
                title="Baixar imagem desta cena"
                class="w-6 h-6 rounded-md bg-black/80 hover:bg-emerald-500 text-slate-300 hover:text-slate-950 flex items-center justify-center transition border border-white/10"
              >
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- LIGHTBOX / MODAL DE VISUALIZAÇÃO EM TELA CHEIA DA CENA -->
    <div
      v-if="lightboxIndex !== null && activeLightboxScene"
      class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/95 backdrop-blur-md animate-in fade-in duration-150"
      @click="closeLightbox"
    >
      <!-- Container do Lightbox -->
      <div class="relative max-w-xl w-full max-h-[92vh] flex flex-col items-center" @click.stop>
        <!-- Header do Lightbox -->
        <div class="w-full flex items-center justify-between pb-3 text-white">
          <div class="flex items-center space-x-2">
            <span class="text-sm font-bold">Cena {{ lightboxIndex + 1 }} de {{ scenes.length }}</span>
            <span class="text-xs text-slate-400 font-mono">({{ activeLightboxScene.name }})</span>
          </div>

          <div class="flex items-center space-x-2">
            <!-- Botão Download da Imagem no Lightbox -->
            <a
              :href="activeLightboxScene.download_url || (activeLightboxScene.url.includes('?') ? `${activeLightboxScene.url}&download=true` : `${activeLightboxScene.url}?download=true`)"
              download
              target="_blank"
              class="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs inline-flex items-center space-x-1 transition"
            >
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Baixar Cena</span>
            </a>

            <!-- Botão Fechar -->
            <button
              @click="closeLightbox"
              class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
              aria-label="Fechar preview"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Imagem Ampliada com Controles Laterais -->
        <div class="relative w-full flex items-center justify-center">
          <button
            @click="prevScene"
            class="absolute left-2 p-2 rounded-full bg-black/70 hover:bg-black text-white border border-white/20 transition z-20"
            title="Cena Anterior (Seta Esquerda)"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <img
            :src="activeLightboxScene.url"
            :alt="activeLightboxScene.name"
            class="max-h-[78vh] w-auto rounded-2xl shadow-2xl border border-slate-800 object-contain"
          />

          <button
            @click="nextScene"
            class="absolute right-2 p-2 rounded-full bg-black/70 hover:bg-black text-white border border-white/20 transition z-20"
            title="Próxima Cena (Seta Direita)"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

