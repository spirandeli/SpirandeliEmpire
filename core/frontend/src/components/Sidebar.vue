<template>
  <aside
    class="flex flex-col justify-between h-full select-none transition-all duration-300"
    :class="[
      isMobile ? 'w-72 max-w-[85vw] p-3.5 bg-slate-900 border-r border-slate-800 shadow-2xl' : (isCollapsed ? 'w-20' : 'w-60 sm:w-64'),
    ]"
  >
    <!-- Top & Middle Section -->
    <div class="space-y-3 overflow-y-auto no-scrollbar">
      <!-- 1. Commander Profile Box (Top-Left) -->
      <div
        class="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex items-center justify-between gap-2.5 cursor-pointer hover:border-slate-700 hover:bg-slate-850 transition group"
        title="Clique para editar seu Perfil ou gerenciar Cadastros"
      >
        <div
          @click="$emit('open-profile')"
          class="flex items-center gap-2.5 min-w-0 flex-1"
        >
          <!-- Avatar Frame -->
          <div class="w-11 h-11 shrink-0 rounded-xl bg-slate-950 border border-amber-500/40 group-hover:border-amber-400 overflow-hidden flex items-center justify-center relative shadow-sm transition">
            <img
              src="/assets/sprites/avatar.png"
              alt="Spirandeli Commander"
              class="w-full h-full object-cover"
            />
            <span class="absolute bottom-0 right-0 bg-amber-500 text-slate-950 text-[8px] font-black px-1 rounded-tl">
              ✎
            </span>
          </div>

          <!-- Name & Level Bar -->
          <div v-if="!isCollapsed" class="flex-1 min-w-0 pr-1">
            <div class="flex items-center justify-between gap-1">
              <h1 class="font-bold text-xs sm:text-[13px] tracking-tight text-white uppercase truncate">
                {{ user?.name || 'SPIRANDELI' }}
              </h1>
            </div>
            <p class="text-[11px] text-amber-400 truncate font-medium">
              {{ user?.profile_data?.title || 'Comandante Soberano' }}
            </p>
            <div class="flex items-center gap-1.5 mt-1">
              <span class="px-1.5 py-0.2 text-[9px] font-mono font-bold bg-slate-950 text-slate-300 border border-slate-800 rounded shrink-0">
                Lv. {{ user?.profile_data?.level || 3 }}
              </span>
              <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800/80">
                <div class="bg-emerald-500 h-full rounded-full w-[72%]"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Mobile Close Button (✕) -->
        <button
          v-if="isMobile"
          @click.stop="$emit('close-mobile')"
          class="p-1 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition shrink-0"
          title="Fechar Menu"
        >
          ✕
        </button>
      </div>

      <!-- 2. Main Navigation Panel -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-2.5">
        <!-- Golden CTA Button: + Novo Negócio Digital -->
        <router-link
          to="/factory"
          @click="onNavClick"
          class="w-full py-2.5 px-3 flex items-center justify-center gap-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs tracking-tight transition shadow-md shadow-amber-500/20 mb-2.5"
          :title="isCollapsed ? 'Novo Negócio Digital' : ''"
        >
          <span class="text-base font-black leading-none">+</span>
          <span v-if="!isCollapsed">Novo Negócio Digital</span>
        </router-link>

        <!-- Navigation Menu Links -->
        <nav class="space-y-1">
          <router-link
            v-for="item in menu"
            :key="item.path"
            :to="item.path"
            @click="onNavClick"
            class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all"
            :class="[
              isActive(item.path)
                ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold shadow-sm'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent',
              isCollapsed ? 'justify-center px-1' : ''
            ]"
            :title="isCollapsed ? item.name : ''"
          >
            <span class="w-5 h-5 flex items-center justify-center text-sm shrink-0">
              {{ item.icon }}
            </span>
            <span v-if="!isCollapsed" class="truncate">{{ item.name }}</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- 3. Bottom Jeffrey Online Status Widget -->
    <router-link
      to="/jeffrey"
      @click="onNavClick"
      class="bg-slate-900 border border-slate-800 rounded-2xl p-3 block hover:border-slate-700 transition shrink-0"
      title="Clique para abrir o Monitor de Trabalhos e Progresso do Jeffrey"
    >
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <span
            class="w-2.5 h-2.5 rounded-full shrink-0"
            :class="jeffreyWorking
              ? 'bg-amber-400 shadow-[0_0_8px_#f59e0b] animate-ping'
              : 'bg-emerald-400 shadow-[0_0_8px_#34d399]'"
          ></span>
          <span v-if="!isCollapsed" class="font-semibold text-xs text-slate-200 truncate">
            {{ jeffreyWorking ? 'Jeffrey Trabalhando' : 'Jeffrey Online (Ocioso)' }}
          </span>
        </div>
        <span
          v-if="activeTasksCount > 0 && !isCollapsed"
          class="px-2 py-0.5 text-[10px] font-mono font-bold rounded-full bg-amber-500 text-slate-950"
        >
          {{ activeTasksCount }}
        </span>
      </div>
      <div v-if="!isCollapsed" class="text-[11px] text-slate-400 mt-1 pl-4.5 truncate font-mono">
        <span v-if="jeffreyWorking" class="text-amber-300">{{ workerStep }}</span>
        <span v-else>Teto: <span class="text-slate-300 font-semibold">R$ 200/mês</span></span>
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
