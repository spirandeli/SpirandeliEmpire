<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useApprovalStore } from '@/stores/approvals'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'toggle-kill-switch', 'logout', 'open-chat'])
const route = useRoute()
const authStore = useAuthStore()
const approvalStore = useApprovalStore()

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
      class="relative w-4/5 max-w-xs bg-slate-900 border-r border-slate-800 flex flex-col justify-between shadow-2xl z-10"
      style="padding-top: max(0.75rem, env(safe-area-inset-top, 0px)); padding-bottom: max(1.5rem, env(safe-area-inset-bottom, 0px))"
    >
      <!-- Header do Drawer -->
      <div class="flex-1 flex flex-col min-h-0">
        <div class="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
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
        <div class="p-4 border-b border-slate-800/60 bg-slate-950/40 shrink-0">
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

        <!-- Links de Navegação Completos -->
        <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
          <div class="px-3 pt-1 pb-1 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">
            Operações Principais
          </div>

          <RouterLink
            to="/"
            @click="handleNavClick"
            class="flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name === 'dashboard' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <div class="flex items-center space-x-3">
              <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
              <span>Dashboard Executivo</span>
            </div>
            <span
              v-if="approvalStore.summary.total_awaiting > 0"
              class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30"
            >
              {{ approvalStore.summary.total_awaiting }}
            </span>
          </RouterLink>

          <RouterLink
            to="/businesses"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name?.startsWith('businesses') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
            <span>Hub de Negócios</span>
          </RouterLink>

          <RouterLink
            to="/tasks"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name === 'tasks.board' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
            <span>Operações (Kanban)</span>
          </RouterLink>

          <RouterLink
            to="/storage-viewer"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name === 'storage.viewer' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 text-indigo-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span>Galeria de Produção</span>
          </RouterLink>

          <RouterLink
            to="/languages"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name?.startsWith('languages') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            <div class="flex items-center justify-between flex-1">
              <span>Academia de Idiomas</span>
              <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">15 min</span>
            </div>
          </RouterLink>

          <div class="px-3 pt-3 pb-1 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">
            Configurações & IA
          </div>

          <RouterLink
            to="/settings/integrations"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name === 'settings.integrations' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"/>
            </svg>
            <span>Integrações & Cofre</span>
          </RouterLink>

          <!-- Link Administrativo de Governança FinOps se Admin -->
          <RouterLink
            v-if="authStore.user?.is_admin"
            to="/admin/ai-governance"
            @click="handleNavClick"
            class="flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition min-h-[42px]"
            :class="route.name === 'admin.ai-governance' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold' : 'text-slate-300 hover:bg-slate-800/60'"
          >
            <svg class="w-4 h-4 text-rose-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Governança & FinOps IA</span>
          </RouterLink>
        </nav>
      </div>

      <!-- Footer do Drawer: Usuário e Sair -->
      <div class="p-4 border-t border-slate-800 bg-slate-950/60 shrink-0 space-y-3">
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
