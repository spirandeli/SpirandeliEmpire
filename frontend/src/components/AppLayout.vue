<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useApprovalStore } from '@/stores/approvals'
import { useSwal } from '@/composables/useSwal'
import AgentChatDrawer from '@/components/AgentChatDrawer.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const approvalStore = useApprovalStore()
const swal = useSwal()

const isChatOpen = ref(false)
const selectedBusinessId = ref(null)

onMounted(async () => {
  await approvalStore.fetchSummary()
})

async function handleToggleKillSwitch() {
  const willDisable = authStore.isAgentEnabled
  const confirmed = await swal.confirm({
    title: willDisable ? 'Pausar Todos os Workers do Agente?' : 'Ativar Workers Autônomos?',
    text: willDisable
      ? 'O Gemini 3.8 deixará de executar jobs e automações em background até você reativar.'
      : 'O agente voltará a operar minerações, roteiros e automações em background.',
    confirmText: willDisable ? 'Sim, pausar agente' : 'Sim, ativar agente',
    confirmButtonColor: willDisable ? '#f59e0b' : '#10b981',
  })

  if (confirmed) {
    await authStore.toggleAgentKillSwitch()
    swal.toast(
      authStore.isAgentEnabled ? 'Workers autônomos ativados!' : 'Workers do agente pausados.',
      authStore.isAgentEnabled ? 'success' : 'warning'
    )
  }
}

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}

function openChat(businessId = null) {
  selectedBusinessId.value = businessId
  isChatOpen.value = true
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex font-sans antialiased selection:bg-emerald-500 selection:text-white">
    <!-- Sidebar -->
    <aside class="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col shrink-0">
      <!-- Logo & Status -->
      <div class="h-16 border-b border-slate-800 flex items-center justify-between px-5">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-black text-white text-sm shadow-lg shadow-emerald-500/20">
            S
          </div>
          <div>
            <span class="font-bold text-sm tracking-tight text-white block">SpirandeliEmpire</span>
            <span class="text-[10px] text-slate-400 uppercase tracking-widest font-mono">Gemini 3.8 OS</span>
          </div>
        </div>

        <!-- Indicador de Status dos Workers -->
        <div class="flex items-center space-x-1.5" :title="authStore.isAgentEnabled ? 'Workers Autônomos Ativos' : 'Workers Pausados'">
          <span
            class="w-2 h-2 rounded-full transition-all"
            :class="authStore.isAgentEnabled ? 'bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400' : 'bg-amber-400'"
          ></span>
          <span class="text-[10px] font-mono text-slate-400">
            {{ authStore.isAgentEnabled ? 'ONLINE' : 'PAUSED' }}
          </span>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <RouterLink
          to="/"
          class="flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition"
          :class="route.name === 'dashboard' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'"
        >
          <div class="flex items-center space-x-3">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
            <span>Dashboard Executivo</span>
          </div>
          <!-- Badge da Inbox de Supervisão -->
          <span
            v-if="approvalStore.summary.total_awaiting > 0"
            class="px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse"
          >
            {{ approvalStore.summary.total_awaiting }}
          </span>
        </RouterLink>

        <RouterLink
          to="/businesses"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition"
          :class="route.name?.startsWith('businesses') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
          <span>Hub de Negócios</span>
        </RouterLink>

        <RouterLink
          to="/tasks"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition"
          :class="route.name === 'tasks.board' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
          <span>Operações (Kanban)</span>
        </RouterLink>

        <RouterLink
          to="/settings/integrations"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition"
          :class="route.name === 'settings.integrations' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"/></svg>
          <span>Integrações & Cofre</span>
        </RouterLink>

        <!-- Link Administrativo de Governança FinOps (Visível se Admin) -->
        <RouterLink
          v-if="authStore.user?.is_admin"
          to="/admin/ai-governance"
          class="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition"
          :class="route.name === 'admin.ai-governance' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'"
        >
          <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span>Governança & FinOps IA</span>
        </RouterLink>
      </nav>

      <!-- Botão Central do Agente (COO Autônomo) -->
      <div class="p-3 border-t border-slate-800 bg-slate-950/40">
        <button
          @click="openChat(null)"
          class="w-full flex items-center justify-center space-x-2.5 px-4 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 font-semibold text-sm text-white shadow-lg shadow-indigo-600/20 transition transform active:scale-98"
        >
          <svg class="w-4 h-4 animate-spin-slow" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          <span>Chat COO Gemini 3.8</span>
        </button>
      </div>

      <!-- User Info & Logout -->
      <div class="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div class="truncate mr-2">
          <span class="font-semibold text-slate-200 block truncate">{{ authStore.user?.name }}</span>
          <span class="text-[11px] truncate block">{{ authStore.user?.email }}</span>
        </div>
        <button
          @click="handleLogout"
          class="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-red-400 transition"
          title="Encerrar Sessão"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
        </button>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top Header -->
      <header class="h-16 bg-slate-900/60 backdrop-blur border-b border-slate-800 flex items-center justify-between px-8">
        <div class="flex items-center space-x-4">
          <slot name="header-title">
            <h1 class="text-base font-bold text-white tracking-tight">SpirandeliEmpire</h1>
          </slot>
        </div>

        <div class="flex items-center space-x-4">
          <!-- Kill-Switch Global do Agente -->
          <div class="flex items-center space-x-2.5 bg-slate-950 px-3.5 py-1.5 rounded-full border border-slate-800">
            <span class="text-xs font-medium text-slate-300">Autonomia dos Workers:</span>
            <button
              @click="handleToggleKillSwitch"
              class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
              :class="authStore.isAgentEnabled ? 'bg-emerald-500' : 'bg-slate-700'"
            >
              <span
                class="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                :class="authStore.isAgentEnabled ? 'translate-x-4' : 'translate-x-0'"
              ></span>
            </button>
          </div>

          <!-- Botão rápido de Chat com Agente -->
          <button
            @click="openChat(null)"
            class="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center space-x-2 transition"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>COO IA</span>
          </button>
        </div>
      </header>

      <!-- Main Body -->
      <main class="flex-1 overflow-y-auto p-8">
        <slot />
      </main>
    </div>

    <!-- Gaveta Lateral de Chat com Gemini 3.8 -->
    <AgentChatDrawer
      :is-open="isChatOpen"
      :business-id="selectedBusinessId"
      @close="isChatOpen = false"
    />
  </div>
</template>

