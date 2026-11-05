<template>
  <header class="bg-slate-900 border border-slate-800 rounded-2xl px-2.5 sm:px-4 py-2 sm:py-2.5 flex items-center justify-between gap-2 sm:gap-3 z-20 select-none shadow-lg">
    <!-- Left: Hamburger / Sidebar Toggle + Server Status Badge -->
    <div class="flex items-center gap-2 min-w-0">
      <!-- Mobile & Tablet Hamburger Button (< 1024px) -->
      <button
        type="button"
        @click="$emit('toggle-menu')"
        class="lg:hidden h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 flex items-center justify-center text-base shrink-0 transition"
        title="Abrir Menu de Navegação"
      >
        <span>☰</span>
      </button>

      <!-- Desktop Sidebar Collapse Toggle (>= 1024px) -->
      <button
        type="button"
        @click="$emit('toggle-collapse')"
        class="hidden lg:flex h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 items-center justify-center text-sm shrink-0 transition"
        :title="isCollapsed ? 'Expandir Barra Lateral' : 'Recolher Barra Lateral'"
      >
        <span>{{ isCollapsed ? '⏩' : '⏪' }}</span>
      </button>

      <!-- Server & Active Profile Badge -->
      <div class="bg-slate-950/80 border border-slate-800 rounded-xl px-2.5 sm:px-3.5 py-1.5 flex items-center gap-2 sm:gap-3 text-xs min-w-0 font-mono">
        <!-- Server Telemetry Pill -->
        <div class="flex items-center gap-1.5 shrink-0">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span class="text-slate-400 hidden sm:inline">Servidor:</span>
          <span class="text-emerald-400 font-bold text-[11px] sm:text-xs">
            VPS Ubuntu
          </span>
        </div>

        <span class="text-slate-700 hidden md:inline">|</span>

        <!-- Active Profile & Focus Business Info -->
        <div
          @click="$emit('open-profile')"
          class="hidden md:flex items-center gap-2 cursor-pointer hover:text-white transition min-w-0 font-sans"
          title="Clique para editar seu Perfil e Cadastros"
        >
          <span class="text-sm">👤</span>
          <span class="text-slate-200 font-semibold truncate">
            {{ user?.name || 'Comandante' }}
          </span>
          <span class="px-2 py-0.5 text-[10px] font-mono font-bold rounded-md bg-slate-800 text-amber-400 border border-slate-700 truncate max-w-[140px] hidden xl:inline">
            🎯 {{ user?.profile_data?.focus_business_slug || 'tiktok-shop' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Right: Quick Action Controls -->
    <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
      <!-- Profile Button -->
      <button
        @click="$emit('open-profile')"
        class="h-9 sm:h-10 px-3 sm:px-3.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wide flex items-center justify-center gap-1.5 transition shadow-sm shadow-amber-500/20"
        title="Gerenciar Meu Perfil e Cadastros"
      >
        <span>👤</span>
        <span class="hidden md:inline">Perfil</span>
      </button>

      <!-- VPS Settings Button -->
      <router-link
        to="/vps"
        class="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 hidden sm:flex items-center justify-center text-sm transition"
        title="Administração VPS & Configurações"
      >
        ⚙️
      </router-link>

      <!-- Financial Metrics Button -->
      <router-link
        to="/financial"
        class="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 hidden sm:flex items-center justify-center text-sm transition"
        title="Métricas & Financeiro"
      >
        📊
      </router-link>

      <!-- Password Change Button -->
      <button
        @click="promptChangePassword"
        class="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 hidden sm:flex items-center justify-center text-sm transition"
        title="Alterar Senha do Comandante"
      >
        🔑
      </button>

      <!-- Logout Button -->
      <button
        @click="$emit('logout')"
        class="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/80 flex items-center justify-center text-sm font-bold transition"
        title="Trancar Painel / Sair (Logout)"
      >
        ⏻
      </button>
    </div>
  </header>
</template>

<script setup>
import axios from 'axios'

defineProps({
  user: {
    type: Object,
    default: null,
  },
  isCollapsed: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['logout', 'open-profile', 'toggle-menu', 'toggle-collapse'])

const promptChangePassword = async () => {
  const currentPassword = prompt('Digite sua senha atual de Comandante:')
  if (!currentPassword) return
  const newPassword = prompt('Digite a nova senha forte (mínimo 6 caracteres):')
  if (!newPassword || newPassword.length < 6) {
    return alert('A nova senha deve ter no mínimo 6 caracteres.')
  }
  try {
    const res = await axios.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    if (res.data?.token) {
      localStorage.setItem('empire_auth_token', res.data.token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`
      alert(res.data.message || 'Senha atualizada com sucesso!')
    }
  } catch (e) {
    alert(e.response?.data?.error || e.response?.data?.message || 'Erro ao alterar senha.')
  }
}
</script>
