<script setup>
import { ref, onMounted } from 'vue'

const deferredPrompt = ref(null)
const showInstallBanner = ref(false)
const isIOS = ref(false)
const showIOSGuide = ref(false)

onMounted(() => {
  // Verifica se o usuário já dispensou hoje
  const dismissed = localStorage.getItem('pwa_prompt_dismissed')
  if (dismissed && Date.now() - Number(dismissed) < 1000 * 60 * 60 * 24 * 3) {
    return
  }

  // Detecção iOS
  const userAgent = window.navigator.userAgent.toLowerCase()
  const isIpadOrIphone = /iphone|ipad|ipod/.test(userAgent)
  const isStandalone = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches

  if (isIpadOrIphone && !isStandalone) {
    isIOS.value = true
    showInstallBanner.value = true
  }

  // Detecção Android / Chrome Desktop
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt.value = e
    showInstallBanner.value = true
  })
})

async function handleInstallClick() {
  if (isIOS.value) {
    showIOSGuide.value = !showIOSGuide.value
    return
  }

  if (!deferredPrompt.value) return

  deferredPrompt.value.prompt()
  const { outcome } = await deferredPrompt.value.userChoice
  if (outcome === 'accepted') {
    showInstallBanner.value = false
  }
  deferredPrompt.value = null
}

function handleDismiss() {
  showInstallBanner.value = false
  showIOSGuide.value = false
  localStorage.setItem('pwa_prompt_dismissed', Date.now().toString())
}
</script>

<template>
  <div
    v-if="showInstallBanner"
    class="fixed top-3 left-3 right-3 sm:left-auto sm:right-6 sm:w-96 z-50 bg-slate-900/95 backdrop-blur-md border border-emerald-500/30 rounded-2xl p-4 shadow-2xl shadow-emerald-500/10 transition-all transform animate-slide-down"
  >
    <div class="flex items-start justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-black text-white text-base shadow-md shadow-emerald-500/20 shrink-0">
          S
        </div>
        <div>
          <h4 class="text-sm font-bold text-white tracking-tight">Instalar Spirandeli OS</h4>
          <p class="text-xs text-slate-400 mt-0.5 leading-snug">
            {{ isIOS ? 'Adicione à tela de início para ter tela cheia e performance nativa.' : 'Tenha acesso rápido offline e experiência de app nativo.' }}
          </p>
        </div>
      </div>
      <button
        @click="handleDismiss"
        class="text-slate-400 hover:text-white p-1 rounded-lg ml-2"
        title="Dispensar aviso"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Guia iOS Expandido -->
    <div v-if="showIOSGuide && isIOS" class="mt-3 p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-300 space-y-1">
      <p class="font-semibold text-emerald-400">Como instalar no iPhone/iPad:</p>
      <p>1. Toque no botão de <strong>Compartilhar</strong> (ícone com quadrado e seta para cima no Safari).</p>
      <p>2. Role para baixo e selecione <strong>"Adicionar à Tela de Início"</strong>.</p>
    </div>

    <div class="mt-3.5 flex items-center justify-end space-x-2">
      <button
        @click="handleDismiss"
        class="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition"
      >
        Agora não
      </button>
      <button
        @click="handleInstallClick"
        class="px-4 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500 to-indigo-600 hover:from-emerald-400 hover:to-indigo-500 text-white shadow-md shadow-emerald-500/20 transition flex items-center space-x-1.5"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        <span>{{ isIOS ? (showIOSGuide ? 'Entendi' : 'Como Instalar') : 'Instalar App' }}</span>
      </button>
    </div>
  </div>
</template>
