<template>
  <aside
    class="flex flex-col justify-between h-full select-none transition-all duration-300"
    :class="[
      isMobile ? 'w-72 max-w-[85vw] p-3' : (isCollapsed ? 'w-20' : 'w-60 sm:w-64'),
    ]"
  >
    <!-- Top & Middle Section -->
    <div class="space-y-2.5 overflow-y-auto no-scrollbar">
      <!-- 1. Commander Profile Box (Top-Left) -->
      <div
        class="pixel-wood rpg-rivets p-2.5 flex items-center justify-between gap-2.5 cursor-pointer hover:brightness-110 transition group relative"
        title="Clique para editar seu Perfil ou gerenciar Cadastros"
      >
        <div
          @click="$emit('open-profile')"
          class="flex items-center gap-2.5 min-w-0 flex-1"
        >
          <!-- Pixel Avatar Frame -->
          <div class="w-12 h-12 sm:w-14 sm:h-14 shrink-0 rounded bg-[#3b200e] border-2 border-[#1a0b03] group-hover:border-[#f59e0b] shadow-[inset_0_2px_4px_rgba(0,0,0,0.7),0_1px_0_#85522d] overflow-hidden flex items-center justify-center relative">
            <img
              src="/assets/sprites/avatar.png"
              alt="Spirandeli Commander"
              class="w-full h-full object-cover"
            />
            <span class="absolute bottom-0 right-0 bg-[#f59e0b] text-[#1e0d04] text-[8px] font-black px-1 rounded-tl">
              ✎
            </span>
          </div>

          <!-- Name & Level Bar (Hidden in desktop collapsed mode) -->
          <div v-if="!isCollapsed" class="flex-1 min-w-0 pr-1">
            <div class="flex items-center justify-between gap-1">
              <h1 class="font-extrabold text-[12px] sm:text-[12.5px] tracking-wide text-[#fff7e6] uppercase truncate rpg-text-outline-sm">
                {{ user?.name || 'SPIRANDELIEMPIRE' }}
              </h1>
            </div>
            <p class="text-[9.5px] sm:text-[10px] text-[#fde68a] truncate font-semibold">
              {{ user?.profile_data?.title || 'Comandante Soberano' }}
            </p>
            <div class="flex items-center gap-1.5 mt-1">
              <span class="px-1.5 py-0.5 text-[9.5px] font-bold bg-[#281509] text-[#f5d7a1] border border-[#6e4223] rounded-sm shadow-inner shrink-0">
                Lv. {{ user?.profile_data?.level || 3 }}
              </span>
              <div class="pixel-bar-bg flex-1 h-2.5 sm:h-3">
                <div class="pixel-bar-energy h-full w-[72%]"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Mobile Close Button (✕) -->
        <button
          v-if="isMobile"
          @click.stop="$emit('close-mobile')"
          class="pixel-btn-red px-2 py-1 text-xs font-black shrink-0"
          title="Fechar Menu"
        >
          ✕
        </button>
      </div>

      <!-- 2. Main Sidebar Navigation Panel -->
      <div class="pixel-wood rpg-rivets p-2.5 relative">
        <!-- Hanging RPG Lantern attached to top-right of sidebar -->
        <div
          v-if="!isMobile && !isCollapsed"
          class="hidden xl:block absolute -right-7 top-2 w-7 h-16 pointer-events-none z-30 drop-shadow-[0_4px_6px_rgba(0,0,0,0.7)]"
          title="Lanterna da Vila"
        >
          <div class="w-3 h-1.5 bg-[#3b200e] border border-[#140802] mt-2"></div>
          <div class="w-5 h-10 -mt-0.5 ml-1 rounded-sm bg-gradient-to-b from-[#332924] via-[#fbbf24] to-[#291d17] border-2 border-[#140802] shadow-[0_0_12px_#f59e0b] flex items-center justify-center">
            <div class="w-2.5 h-4 bg-[#fef08a] rounded-full animate-pulse"></div>
          </div>
        </div>

        <!-- Golden CTA Button: + Novo Negócio Digital -->
        <router-link
          to="/factory"
          @click="onNavClick"
          class="pixel-btn-gold w-full py-2 sm:py-2.5 px-3 flex items-center justify-center gap-1.5 text-[12.5px] sm:text-[13px] tracking-tight mb-2.5"
          :title="isCollapsed ? 'Novo Negócio Digital' : ''"
        >
          <span class="text-base font-black leading-none">+</span>
          <span v-if="!isCollapsed">Novo Negócio Digital</span>
        </router-link>

        <!-- Navigation Menu Slots -->
        <nav class="pixel-wood-inset p-1.5 space-y-1">
          <router-link
            v-for="item in menu"
            :key="item.path"
            :to="item.path"
            @click="onNavClick"
            class="flex items-center gap-2.5 px-2.5 py-2 rounded-[3px] text-[12.5px] sm:text-[13px] font-semibold transition-all border"
            :class="[
              isActive(item.path)
                ? 'bg-gradient-to-r from-[#63391b] to-[#4d2b13] text-[#fff6df] border-[#f59e0b] shadow-[inset_0_1px_0_#9c6034,0_0_6px_rgba(245,158,11,0.3)]'
                : 'bg-[#331b0c]/70 text-[#e2c699] border-[#221006] hover:bg-[#452612] hover:text-white hover:border-[#6b3f20]',
              isCollapsed ? 'justify-center px-1' : ''
            ]"
            :title="isCollapsed ? item.name : ''"
          >
            <span class="w-5 h-5 flex items-center justify-center text-base shrink-0 drop-shadow">
              {{ item.icon }}
            </span>
            <span v-if="!isCollapsed" class="truncate rpg-text-outline-sm">{{ item.name }}</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- 3. Bottom-Left Jeffrey Online Status Widget -->
    <router-link
      to="/jeffrey"
      @click="onNavClick"
      class="pixel-wood rpg-rivets px-3 py-2 sm:px-3.5 sm:py-2.5 mt-2 block hover:brightness-110 transition shrink-0"
      title="Clique para abrir o Monitor de Trabalhos e Progresso do Jeffrey"
    >
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span
            class="w-3 h-3 rounded-full shrink-0"
            :class="jeffreyWorking
              ? 'bg-[#fbbf24] border border-[#451a03] shadow-[0_0_8px_#f59e0b] animate-ping'
              : 'bg-[#22c55e] border border-[#052e16] shadow-[0_0_8px_#4ade80]'"
          ></span>
          <span v-if="!isCollapsed" class="font-bold text-[12px] sm:text-[12.5px] text-[#fff5e0] rpg-text-outline-sm truncate">
            {{ jeffreyWorking ? 'Jeffrey Trabalhando' : 'Jeffrey Online (Ocioso)' }}
          </span>
        </div>
        <span
          v-if="activeTasksCount > 0 && !isCollapsed"
          class="px-1.5 py-0.5 text-[10px] font-black rounded bg-[#f59e0b] text-[#1e0d04]"
        >
          {{ activeTasksCount }}
        </span>
      </div>
      <div v-if="!isCollapsed" class="text-[10.5px] sm:text-[11px] text-[#d9bc8c] mt-0.5 pl-5 font-medium truncate">
        <span v-if="jeffreyWorking" class="text-[#fde68a]">{{ workerStep }}</span>
        <span v-else>Limite: <span class="text-[#fbbf24] font-extrabold rpg-text-outline-sm">R$ 200/mês</span></span>
      </div>
    </router-link>
  </aside>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  isMobile: {
    type: Boolean,
    default: false,
  },
  isCollapsed: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['open-profile', 'close-mobile'])

const route = useRoute()
const jeffreyWorking = ref(false)
const activeTasksCount = ref(0)
const workerStep = ref('Processando na fila...')

const onNavClick = () => {
  if (props.isMobile) {
    emit('close-mobile')
  }
}

const fetchStatus = async () => {
  try {
    const res = await axios.get('/api/v1/jeffrey/activity')
    if (res.data?.success) {
      jeffreyWorking.value = !!res.data.is_working
      activeTasksCount.value = (res.data.counts?.in_progress || 0) + (res.data.counts?.pending || 0)
      workerStep.value = res.data.worker_state?.step || 'Processando na fila...'
    }
  } catch (_) {}
}

let statusTimer = null
onMounted(() => {
  fetchStatus()
  statusTimer = setInterval(fetchStatus, 6000)
})
onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
})

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const menu = [
  { name: 'Visão Geral', path: '/', icon: '🏠' },
  { name: 'Jeffrey AI & Agentes', path: '/jeffrey', icon: '🧑' },
  { name: 'Negócios & Contas', path: '/businesses', icon: '🛡️' },
  { name: 'Business Factory', path: '/factory', icon: '🏭' },
  { name: 'AI Engine (Local)', path: '/ai-engine', icon: '⚙️' },
  { name: 'Financeiro (Teto R$ 200)', path: '/financial', icon: '💰' },
  { name: 'Administração VPS', path: '/vps', icon: '🔧' },
]
</script>
