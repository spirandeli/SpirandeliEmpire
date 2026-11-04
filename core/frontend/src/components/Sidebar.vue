<template>
  <aside class="w-64 bg-[#190e07] border-r-4 border-[#0c0603] flex flex-col justify-between select-none shadow-[4px_0_0_#080402] z-20">
    <div>
      <!-- Brand & Version -->
      <div class="p-4 border-b-4 border-[#0e0704] bg-[#24140b] flex items-center space-x-3">
        <div class="w-10 h-10 bg-[#f59e0b] border-2 border-[#120803] shadow-[inset_2px_2px_0_#fde68a,inset_-2px_-2px_0_#92400e,0_2px_0_#000] flex items-center justify-center text-xl">
          👑
        </div>
        <div>
          <h1 class="font-pixel-title text-[11px] tracking-wider text-[#fde68a] uppercase leading-tight">Spirandeli</h1>
          <div class="flex items-center gap-1.5 mt-1">
            <span class="text-[8px] font-pixel-title text-[#140b06] bg-[#f59e0b] px-1 py-0.5 border border-[#451a03]">RPG v2.0</span>
            <span class="text-[8px] font-pixel-title text-[#a3e635]">● ATIVO</span>
          </div>
        </div>
      </div>

      <!-- Quick Action: New Digital Business (Quest Button) -->
      <div class="p-3">
        <router-link
          to="/factory"
          class="pixel-btn-gold w-full py-3 px-3 flex items-center justify-center text-center uppercase tracking-wider block"
        >
          <span class="mr-1.5 text-sm">⚔️</span> FORJAR NEGÓCIO
        </router-link>
      </div>

      <!-- Main Navigation -->
      <nav class="px-2 space-y-1">
        <router-link
          v-for="item in menu"
          :key="item.path"
          :to="item.path"
          class="flex items-center px-3 py-2 text-xs font-pixel-body transition-all border-2"
          :class="$route.path === item.path 
            ? 'bg-[#3b2314] text-[#fde68a] border-[#f59e0b] shadow-[inset_2px_2px_0_#6e4326]' 
            : 'text-[#d6b88d] border-transparent hover:bg-[#25150c] hover:border-[#3d2415] hover:text-[#fff]'"
        >
          <span class="text-sm mr-2.5">{{ item.icon }}</span>
          <span class="text-xs font-semibold">{{ item.name }}</span>
          <span v-if="item.badge" class="ml-auto text-[8px] font-pixel-title px-1.5 py-0.5 bg-[#0e7490] text-[#cffafe] border border-[#083344]">
            {{ item.badge }}
          </span>
        </router-link>
      </nav>
    </div>

    <!-- Tavern NPC / Jeffrey Companion Card -->
    <div class="p-3 m-2 pixel-wood">
      <div class="flex items-center space-x-2.5 mb-2">
        <div class="w-9 h-9 bg-[#100804] border-2 border-[#5a381f] flex items-center justify-center text-lg shadow-[inset_1px_1px_0_#000]">
          🧙‍♂️
        </div>
        <div>
          <div class="font-pixel-title text-[9px] text-[#fcd34d]">JEFFREY AI</div>
          <div class="text-[10px] font-pixel-body text-[#38bdf8]">Mestre do Reino</div>
        </div>
      </div>

      <!-- Mini Stamina / Budget Bar -->
      <div class="space-y-1 pt-1 border-t border-[#452814]">
        <div class="flex justify-between text-[8px] font-pixel-title text-[#d6b88d]">
          <span>OURO DISP.</span>
          <span class="text-[#f59e0b]">200 G</span>
        </div>
        <div class="pixel-bar-bg h-2 w-full">
          <div class="pixel-bar-gold h-full w-[100%]"></div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
const menu = [
  { name: 'Feudo Central (Dashboard)', path: '/', icon: '🏰' },
  { name: 'Mestre Jeffrey (Chat & IA)', path: '/jeffrey', icon: '🧙‍♂️', badge: 'Active' },
  { name: 'Feudos Ativos (Businesses)', path: '/businesses', icon: '📜' },
  { name: 'Forja Mágica (Factory)', path: '/factory', icon: '⚒️' },
  { name: 'Projetos & Workspace', path: '/projects', icon: '💼' },
  { name: 'Motor de Magia (AI Engine)', path: '/ai-engine', icon: '⚡' },
  { name: 'Quadro de Missões (Approvals)', path: '/approvals', icon: '📌' },
  { name: 'Cofre do Tesouro (Analytics)', path: '/analytics', icon: '🪙' },
  { name: 'Muralhas da VPS (Admin)', path: '/vps', icon: '🛡️' },
]
</script>
