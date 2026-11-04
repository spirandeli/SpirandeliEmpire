<template>
  <header class="flex items-center justify-between gap-2 sm:gap-3 z-20 select-none">
    <!-- Left: Hamburger / Sidebar Toggle + Server Status Badge -->
    <div class="flex items-center gap-2 min-w-0">
      <!-- Mobile & Tablet Hamburger Button (< 1024px) -->
      <button
        type="button"
        @click="$emit('toggle-menu')"
        class="lg:hidden pixel-btn-wood h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center text-lg shrink-0 shadow"
        title="Abrir Menu de Navegação"
      >
        <span>☰</span>
      </button>

      <!-- Desktop Sidebar Collapse Toggle (>= 1024px) -->
      <button
        type="button"
        @click="$emit('toggle-collapse')"
        class="hidden lg:flex pixel-btn-wood h-10 w-10 items-center justify-center text-base shrink-0 shadow"
        :title="isCollapsed ? 'Expandir Barra Lateral' : 'Recolher Barra Lateral'"
      >
        <span>{{ isCollapsed ? '⏩' : '⏪' }}</span>
      </button>

      <!-- Server & Orchestration Wooden Banner -->
      <div class="pixel-wood rpg-rivets px-2 sm:px-3.5 py-1.5 sm:py-2 flex items-center min-w-0">
        <div class="pixel-wood-inset px-2 sm:px-3 py-1 flex items-center gap-2 sm:gap-3 text-xs sm:text-[13px] min-w-0">
          <!-- Server Info -->
          <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <span class="inline-flex flex-col gap-0.5 bg-[#1e3a5f] border border-[#0b192c] px-1 py-0.5 rounded-[2px] shadow-inner">
              <span class="w-2.5 sm:w-3.5 h-1 bg-[#38bdf8] block"></span>
              <span class="w-2.5 sm:w-3.5 h-1 bg-[#38bdf8] block"></span>
            </span>
            <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm hidden sm:inline">Servidor:</span>
            <span class="text-[#4ade80] font-extrabold rpg-text-outline-sm text-[11px] sm:text-xs truncate max-w-[110px] sm:max-w-none">
              VPS Ubuntu
            </span>
          </div>

          <span class="text-[#85522d] font-bold hidden md:inline">|</span>

          <!-- Active Profile & Focus Business Info -->
          <div
            @click="$emit('open-profile')"
            class="hidden md:flex items-center gap-2 cursor-pointer hover:brightness-110 min-w-0"
            title="Clique para editar seu Perfil e Cadastros"
          >
            <span class="text-base leading-none drop-shadow">👤</span>
            <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm truncate">
              {{ user?.name || 'Comandante' }}
            </span>
            <span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-[#3b200e] text-[#fde68a] border border-[#85522d] truncate max-w-[130px] hidden xl:inline">
              🎯 {{ user?.profile_data?.focus_business_slug || 'tiktok-shop' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: RPG Control Buttons -->
    <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
      <!-- Profile Button -->
      <button
        @click="$emit('open-profile')"
        class="pixel-btn-gold h-9 sm:h-11 px-2.5 sm:px-3 flex items-center justify-center gap-1.5 text-xs font-extrabold uppercase shadow"
        title="Gerenciar Meu Perfil e Cadastros"
      >
        <span>👤</span>
        <span class="hidden md:inline">Perfil</span>
      </button>

      <!-- VPS Settings Button -->
      <router-link
        to="/vps"
        class="pixel-btn-wood h-9 w-9 sm:h-11 sm:w-11 flex items-center justify-center text-base sm:text-xl shadow"
        title="Administração VPS & Configurações"
      >
        ⚙️
      </router-link>

      <!-- Financial Metrics Button -->
      <router-link
        to="/financial"
        class="pixel-btn-wood h-9 w-9 sm:h-11 sm:w-11 hidden sm:flex items-center justify-center shadow"
        title="Métricas & Financeiro"
      >
        <span class="flex items-end gap-0.5 h-4 sm:h-5">
          <span class="w-1 sm:w-1.5 h-2 sm:h-2.5 bg-[#fcd34d] border border-[#1e0d04]"></span>
          <span class="w-1 sm:w-1.5 h-3 sm:h-3.5 bg-[#fbbf24] border border-[#1e0d04]"></span>
          <span class="w-1 sm:w-1.5 h-4 sm:h-5 bg-[#f59e0b] border border-[#1e0d04]"></span>
        </span>
      </router-link>

      <!-- Password Change Button -->
      <button
        @click="promptChangePassword"
        class="pixel-btn-wood h-9 w-9 sm:h-11 sm:w-11 hidden sm:flex items-center justify-center text-base sm:text-lg shadow"
        title="Alterar Senha do Comandante"
      >
        🔑
      </button>

      <!-- Logout Button -->
      <button
        @click="$emit('logout')"
        class="pixel-btn-red h-9 w-9 sm:h-11 sm:w-11 flex items-center justify-center text-base sm:text-lg font-black shadow"
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
