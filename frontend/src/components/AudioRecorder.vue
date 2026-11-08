<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  maxDurationSeconds: {
    type: Number,
    default: 60,
  },
  submitLabel: {
    type: String,
    default: 'Analisar Áudio',
  },
  autoAnalyze: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['recorded', 'reset'])

const isRecording = ref(false)
const recordingDuration = ref(0)
const audioBlob = ref(null)
const audioUrl = ref(null)
const audioBase64 = ref(null)
const detectedMimeType = ref('audio/webm')
const errorMessage = ref(null)

let mediaRecorder = null
let audioChunks = []
let timerInterval = null
let streamInstance = null

onUnmounted(() => {
  stopRecordingCleanup()
})

const durationFormatted = computed(() => {
  const mins = Math.floor(recordingDuration.value / 60)
  const secs = recordingDuration.value % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

async function startRecording() {
  errorMessage.value = null
  audioChunks = []
  audioBlob.value = null
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = null
  }
  audioBase64.value = null

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    errorMessage.value = 'Seu navegador não suporta gravação de áudio via microfone.'
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    streamInstance = stream

    // Identifica MIME Type suportado pelo navegador
    let mimeType = 'audio/webm;codecs=opus'
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm'
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4'
      } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
        mimeType = 'audio/ogg'
      } else {
        mimeType = ''
      }
    }
    detectedMimeType.value = mimeType || 'audio/webm'

    mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      const type = detectedMimeType.value.split(';')[0] || 'audio/webm'
      const blob = new Blob(audioChunks, { type })
      audioBlob.value = blob
      audioUrl.value = URL.createObjectURL(blob)

      // Converte para base64
      const reader = new FileReader()
      reader.onloadend = () => {
        audioBase64.value = reader.result
        if (props.autoAnalyze) {
          emitRecorded()
        }
      }
      reader.readAsDataURL(blob)

      stopStreamTracks()
    }

    mediaRecorder.start(250) // coleta a cada 250ms
    isRecording.value = true
    recordingDuration.value = 0

    timerInterval = setInterval(() => {
      recordingDuration.value++
      if (recordingDuration.value >= props.maxDurationSeconds) {
        stopRecording()
      }
    }, 1000)
  } catch (err) {
    console.error('Erro ao acessar microfone:', err)
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      errorMessage.value = 'Permissão de microfone negada. Autorize o acesso ao microfone no seu navegador.'
    } else {
      errorMessage.value = `Falha ao iniciar microfone: ${err.message || 'Erro desconhecido.'}`
    }
    stopRecordingCleanup()
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function stopStreamTracks() {
  if (streamInstance) {
    streamInstance.getTracks().forEach((track) => track.stop())
    streamInstance = null
  }
}

function stopRecordingCleanup() {
  stopRecording()
  stopStreamTracks()
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = null
  }
}

function handleReset() {
  stopRecordingCleanup()
  audioBlob.value = null
  audioBase64.value = null
  recordingDuration.value = 0
  errorMessage.value = null
  emit('reset')
}

function emitRecorded() {
  if (!audioBase64.value) return
  emit('recorded', {
    blob: audioBlob.value,
    base64: audioBase64.value,
    mimeType: detectedMimeType.value.split(';')[0] || 'audio/webm',
    durationSeconds: recordingDuration.value,
  })
}
</script>

<template>
  <div class="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-3">
    <!-- Mensagem de Erro de Permissão -->
    <div v-if="errorMessage" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
      <span>⚠️ {{ errorMessage }}</span>
      <button type="button" @click="errorMessage = null" class="text-rose-400 hover:text-white font-bold ml-2">✕</button>
    </div>

    <!-- ESTADO 1: Inativo / Pronto para Gravar -->
    <div v-if="!isRecording && !audioUrl" class="flex flex-col sm:flex-row items-center justify-between gap-3">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center text-lg">
          🎙️
        </div>
        <div>
          <h4 class="text-xs font-bold text-white">Gravar Pronúncia em Áudio</h4>
          <span class="text-[11px] text-slate-400">Clique para iniciar e fale no microfone (máx. {{ maxDurationSeconds }}s).</span>
        </div>
      </div>

      <button
        type="button"
        @click="startRecording"
        class="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/20 transition flex items-center justify-center space-x-2"
      >
        <span class="w-2.5 h-2.5 rounded-full bg-white animate-ping"></span>
        <span>Iniciar Gravação</span>
      </button>
    </div>

    <!-- ESTADO 2: Gravando Ativamente -->
    <div v-else-if="isRecording" class="flex flex-col sm:flex-row items-center justify-between gap-4 p-3 rounded-xl bg-rose-950/20 border border-rose-500/30">
      <div class="flex items-center space-x-3">
        <div class="relative flex items-center justify-center">
          <div class="w-4 h-4 rounded-full bg-rose-500 animate-ping absolute"></div>
          <div class="w-3.5 h-3.5 rounded-full bg-rose-600 relative"></div>
        </div>
        <div>
          <span class="text-xs font-bold text-rose-300 font-mono tracking-wider">GRAVANDO: {{ durationFormatted }}</span>
          <span class="text-[10px] text-slate-400 block">Fale com clareza a frase sugerida...</span>
        </div>
      </div>

      <div class="flex items-center space-x-2 w-full sm:w-auto">
        <button
          type="button"
          @click="stopRecording"
          class="flex-1 sm:flex-none px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-slate-950 font-black text-xs transition flex items-center justify-center space-x-2 shadow-md"
        >
          <span>⏹ Parar Gravação</span>
        </button>
      </div>
    </div>

    <!-- ESTADO 3: Áudio Gravado Pronto para Envio / Preview -->
    <div v-else-if="audioUrl" class="space-y-3">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center space-x-2">
          <span class="text-xs font-mono font-bold text-emerald-400">✓ Áudio gravado ({{ durationFormatted }})</span>
        </div>
        <div class="flex items-center space-x-2">
          <button
            type="button"
            @click="handleReset"
            class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
            title="Descartar e gravar novamente"
          >
            🔄 Regravar
          </button>
          <button
            type="button"
            :disabled="!audioBase64"
            @click="emitRecorded"
            class="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-black text-xs shadow-md transition flex items-center space-x-1.5"
          >
            <span>{{ submitLabel }}</span>
            <span>⚡</span>
          </button>
        </div>
      </div>

      <!-- Player de Áudio Nativo para Ouvir Antes de Submeter -->
      <div class="pt-1">
        <audio :src="audioUrl" controls class="w-full h-8 rounded-lg outline-none"></audio>
      </div>
    </div>
  </div>
</template>

