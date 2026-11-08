<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'toggle-kill-switch', 'logout'])
const route = useRoute()
const authStore = useAuthStore()

function handleNavClick() {
  emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="md:hidden fixed inset-0 z-50 flex">
    <!-- Backdrop com fade -->
    <div
      class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
      @click="emit('close')"
    ></div>

    <!-- Drawer Panel lateral com slide da esquerda -->
    <div
      class="relative w-4/5 max-w-xs bg-slate-900 border-r border-slate-800 flex flex-col justify-between shadow-2xl z-10 safe-top"
      style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom, 0px))"
    >
      <!-- Header do Drawer -->
      <div>
        <div class="p-4 border-b border-slate-800 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-black text-white text-sm shadow-md shadow-emerald-500/20">
              S
            </div>
            <div>
              <span class="font-bold text-sm text-white block">SpirandeliEmpire</span>
              <span class="text-[10px] text-slate-400 font-mono">Gemini 3.8 OS</span>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 min-h-[44px] min-w-[44px] flex items-center justify-center"
            title="Fechar menu"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Autonomia dos Workers (Toggle Rápido Mobile) -->
        <div class="p-4 border-b border-slate-800/60 bg-slate-950/40">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span
                class="w-2.5 h-2.5 rounded-full"
                :class="authStore.isAgentEnabled ? 'bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400' : 'bg-amber-400'"
              ></span>
              <span class="text-xs font-semibold text-slate-200">Workers Autônomos</span>
            </div>
            <button
              @click="emit('toggle-kill-switch')"
              class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
              :class="authStore.isAgentEnabled ? 'bg-emerald-500' : 'bg-slate-700'"
            >
              <span
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                :class="authStore.isAgentEnabled ? 'translate-x-5' : 'translate-x-0'"
              ></span>
            </button>
          </div>
          <p class="text-[10px] text-slate-400 mt-1">
            Status: {{ authStore.isAgentEnabled ? 'Operando automações em background' : 'Todos os workers pausados' }}
          </p>
        </div>

        <!-- Links de Navegação Secundários -->
        <nav class="p-3 space-y-1 overflow-y-auto">
          <RouterLink
            to="/languages"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-medium transition min-h-[44px]"
            :class="route.name?.startsWith('languages') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-5 h-5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            <div class="flex items-center justify-between flex-1">
              <span>Academia de Idiomas</span>
              <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">15 min</span>
            </div>
          </RouterLink>

          <RouterLink
            to="/settings/integrations"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-medium transition min-h-[44px]"
            :class="route.name === 'settings.integrations' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"/>
            </svg>
            <span>Integrações & Cofre</span>
          </RouterLink>

          <!-- Link Administrativo de Governança FinOps se Admin -->
          <RouterLink
            v-if="authStore.user?.is_admin"
            to="/admin/ai-governance"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-medium transition min-h-[44px]"
            :class="route.name === 'admin.ai-governance' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-5 h-5 text-rose-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Governança & FinOps IA</span>
          </RouterLink>
        </nav>
      </div>

      <!-- Footer do Drawer: Usuário e Sair -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 space-y-3">
        <div class="flex items-center justify-between text-xs text-slate-400">
          <div class="truncate mr-2">
            <span class="font-semibold text-slate-200 block truncate">{{ authStore.user?.name }}</span>
            <span class="text-[11px] truncate block text-slate-400">{{ authStore.user?.email }}</span>
          </div>
          <button
            @click="emit('logout')"
            class="p-2.5 rounded-xl bg-slate-800 hover:bg-red-500/20 text-slate-300 hover:text-red-400 transition min-w-[44px] min-h-[44px] flex items-center justify-center"
            title="Encerrar Sessão"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
