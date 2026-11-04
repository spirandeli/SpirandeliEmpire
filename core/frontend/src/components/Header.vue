<template>
  <header class="flex items-center justify-between gap-3 z-20">
    <!-- Left/Center: Server & Orchestration Wooden Banner -->
    <div class="pixel-wood rpg-rivets px-3.5 py-2 flex items-center">
      <div class="pixel-wood-inset px-3.5 py-1.5 flex flex-wrap items-center gap-3 text-xs sm:text-[13px]">
        <!-- Server Info -->
        <div class="flex items-center gap-2">
          <span class="inline-flex flex-col gap-0.5 bg-[#1e3a5f] border border-[#0b192c] px-1 py-0.5 rounded-[2px] shadow-inner">
            <span class="w-3.5 h-1 bg-[#38bdf8] block"></span>
            <span class="w-3.5 h-1 bg-[#38bdf8] block"></span>
          </span>
          <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm">Servidor:</span>
          <span class="text-[#4ade80] font-extrabold rpg-text-outline-sm">VPS Ubuntu 24.04 LTS</span>
        </div>

        <span class="text-[#85522d] font-bold hidden sm:inline">|</span>

        <!-- Active Profile & Focus Business Info -->
        <div
          @click="$emit('open-profile')"
          class="hidden sm:flex items-center gap-2 cursor-pointer hover:brightness-110"
          title="Clique para editar seu Perfil e Cadastros"
        >
          <span class="text-base leading-none drop-shadow">👤</span>
          <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm">Perfil:</span>
          <span class="text-[#fbbf24] font-extrabold rpg-text-outline-sm">
            {{ user?.name || 'Comandante' }}
          </span>
          <span class="px-1.5 py-0.5 text-[10px] font-bold rounded bg-[#3b200e] text-[#fde68a] border border-[#85522d]">
            🎯 {{ user?.profile_data?.focus_business_slug || 'tiktok-shop-afiliados' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Right: RPG Control Buttons -->
    <div class="flex items-center gap-2">
      <button
        @click="$emit('open-profile')"
        class="pixel-btn-gold h-11 px-3 flex items-center justify-center gap-1.5 text-xs font-extrabold uppercase"
        title="Gerenciar Meu Perfil e Cadastros"
      >
        <span>👤</span>
        <span class="hidden md:inline">Perfil & Cadastros</span>
      </button>

      <router-link
        to="/vps"
        class="pixel-btn-wood w-11 h-11 flex items-center justify-center text-xl"
        title="Administração VPS & Configurações"
      >
        ⚙️
      </router-link>

      <router-link
        to="/financial"
        class="pixel-btn-wood w-11 h-11 flex items-center justify-center"
        title="Métricas & Financeiro"
      >
        <span class="flex items-end gap-0.5 h-5">
          <span class="w-1.5 h-2.5 bg-[#fcd34d] border border-[#1e0d04]"></span>
          <span class="w-1.5 h-3.5 bg-[#fbbf24] border border-[#1e0d04]"></span>
          <span class="w-1.5 h-5 bg-[#f59e0b] border border-[#1e0d04]"></span>
        </span>
      </router-link>

      <button
        @click="promptChangePassword"
        class="pixel-btn-wood w-11 h-11 flex items-center justify-center text-lg"
        title="Alterar Senha do Comandante"
      >
        🔑
      </button>

      <button
        @click="$emit('logout')"
        class="pixel-btn-red w-11 h-11 flex items-center justify-center text-lg font-black"
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
})

defineEmits(['logout', 'open-profile'])

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
