<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useApprovalStore } from '@/stores/approvals'

const emit = defineEmits(['open-chat', 'open-drawer'])
const route = useRoute()
const approvalStore = useApprovalStore()

const currentRoute = computed(() => route.name)
</script>

<template>
  <nav
    class="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-slate-950/95 backdrop-blur-md border-t border-slate-800/80 px-2 pt-2"
    style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom, 0px))"
  >
    <div class="flex items-center justify-around max-w-lg mx-auto">
      <!-- 1. Dashboard -->
      <RouterLink
        to="/"
        class="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition min-w-[56px] min-h-[44px]"
        :class="currentRoute === 'dashboard' ? 'text-emerald-400 font-semibold' : 'text-slate-400 hover:text-slate-200'"
      >
        <div class="relative">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          <span
            v-if="approvalStore.summary.total_awaiting > 0"
            class="absolute -top-1 -right-2 w-2 h-2 rounded-full bg-amber-400 animate-pulse"
          ></span>
        </div>
        <span class="text-[10px] mt-1 tracking-tight">Painel</span>
      </RouterLink>

      <!-- 2. Ventures -->
      <RouterLink
        to="/businesses"
        class="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition min-w-[56px] min-h-[44px]"
        :class="currentRoute?.startsWith('businesses') ? 'text-emerald-400 font-semibold' : 'text-slate-400 hover:text-slate-200'"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
        <span class="text-[10px] mt-1 tracking-tight">Negócios</span>
      </RouterLink>

      <!-- 3. Botão Central de Destaque COO IA -->
      <button
        @click="emit('open-chat')"
        class="relative -top-3 flex flex-col items-center justify-center group focus:outline-none"
        title="Abrir Chat COO Gemini 3.8"
      >
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 ring-4 ring-slate-950 transition active:scale-95 group-hover:brightness-110">
          <svg class="w-6 h-6 animate-spin-slow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </div>
        <span class="text-[9px] font-bold text-slate-300 mt-1 uppercase tracking-wider">COO IA</span>
      </button>

      <!-- 4. Tarefas (Kanban) -->
      <RouterLink
        to="/tasks"
        class="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition min-w-[56px] min-h-[44px]"
        :class="currentRoute === 'tasks.board' ? 'text-emerald-400 font-semibold' : 'text-slate-400 hover:text-slate-200'"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
        </svg>
        <span class="text-[10px] mt-1 tracking-tight">Tarefas</span>
      </RouterLink>

      <!-- 5. Mais Opções (Drawer) -->
      <button
        @click="emit('open-drawer')"
        class="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition min-w-[56px] min-h-[44px] text-slate-400 hover:text-slate-200"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"/>
        </svg>
        <span class="text-[10px] mt-1 tracking-tight">Mais</span>
      </button>
    </div>
  </nav>
</template>
