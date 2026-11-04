<template>
  <header class="flex items-center justify-between gap-3 z-20">
    <!-- Left/Center: Server & Orchestration Wooden Banner -->
    <div class="pixel-wood rpg-rivets px-3.5 py-2 flex items-center">
      <div class="pixel-wood-inset px-3.5 py-1.5 flex flex-wrap items-center gap-3 text-xs sm:text-[13px]">
        <!-- Server Info -->
        <div class="flex items-center gap-2">
          <!-- Pixel Server Rack Icon -->
          <span class="inline-flex flex-col gap-0.5 bg-[#1e3a5f] border border-[#0b192c] px-1 py-0.5 rounded-[2px] shadow-inner">
            <span class="w-3.5 h-1 bg-[#38bdf8] block"></span>
            <span class="w-3.5 h-1 bg-[#38bdf8] block"></span>
          </span>
          <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm">Servidor:</span>
          <span class="text-[#4ade80] font-extrabold rpg-text-outline-sm">VPS Ubuntu 24.04 LTS</span>
        </div>

        <span class="text-[#85522d] font-bold hidden sm:inline">|</span>

        <!-- Orchestration Info -->
        <div class="hidden sm:flex items-center gap-2">
          <span class="text-base leading-none drop-shadow">🐳</span>
          <span class="text-[#f3dec0] font-semibold rpg-text-outline-sm">Orquestração:</span>
          <span class="text-[#fbbf24] font-extrabold rpg-text-outline-sm">Docker Compose</span>
        </div>
      </div>
    </div>

    <!-- Right: 3 RPG Square Control Buttons (Settings, Telemetry Chart, Power) -->
    <div class="flex items-center gap-2">
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
        <!-- Pixel Bar Chart Icon -->
        <span class="flex items-end gap-0.5 h-5">
          <span class="w-1.5 h-2.5 bg-[#fcd34d] border border-[#1e0d04]"></span>
          <span class="w-1.5 h-3.5 bg-[#fbbf24] border border-[#1e0d04]"></span>
          <span class="w-1.5 h-5 bg-[#f59e0b] border border-[#1e0d04]"></span>
        </span>
      </router-link>

      <button
        @click="reloadApp"
        class="pixel-btn-red w-11 h-11 flex items-center justify-center text-lg font-black"
        title="Recarregar Sistema"
      >
        ⏻
      </button>
    </div>
  </header>
</template>

<script setup>
const reloadApp = () => {
  window.location.reload()
}
</script>
