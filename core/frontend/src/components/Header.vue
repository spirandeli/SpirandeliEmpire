<template>
  <header class="h-20 bg-[#1e1108] border-b-4 border-[#0e0704] flex items-center justify-between px-6 z-10 shadow-[0_4px_0_#080402]">
    <!-- Left: Realm & Guild Info -->
    <div class="flex items-center space-x-4">
      <div class="flex items-center space-x-2 bg-[#120904] px-3 py-1.5 border-2 border-[#381e0e] shadow-[inset_2px_2px_0_#000]">
        <span class="text-base">🏰</span>
        <div class="leading-none">
          <div class="text-[9px] font-pixel-title text-[#a16207]">REINO / SERVIDOR</div>
          <div class="text-xs font-pixel-title text-[#fbbf24] mt-0.5">VPS IMPERIAL [ONLINE]</div>
        </div>
      </div>

      <div class="hidden sm:flex items-center space-x-2 bg-[#120904] px-3 py-1.5 border-2 border-[#381e0e] shadow-[inset_2px_2px_0_#000]">
        <span class="text-base">🧙‍♂️</span>
        <div class="leading-none">
          <div class="text-[9px] font-pixel-title text-[#0284c7]">MESTRE DA GUILDA</div>
          <div class="text-xs font-pixel-title text-[#38bdf8] mt-0.5">JEFFREY AI v2.0</div>
        </div>
      </div>
    </div>

    <!-- Right: Stardew Valley Style Clock & Gold HUD -->
    <div class="flex items-center space-x-3">
      <!-- Stardew Clock & Season Widget -->
      <div class="stardew-clock px-3 py-1.5 flex items-center space-x-3">
        <div class="w-8 h-8 rounded bg-[#100804] border-2 border-[#452310] flex items-center justify-center text-lg shadow-[inset_1px_1px_0_#000]">
          ☀️
        </div>
        <div class="leading-tight">
          <div class="text-[8px] font-pixel-title text-[#fcd34d]">ANO 2026 • ESTAÇÃO 1</div>
          <div class="text-xs font-pixel-title text-[#ffffff]">{{ currentTime }}</div>
        </div>
      </div>

      <!-- Gold Coin Purse (Stardew Valley / Graveyard Keeper Currency) -->
      <div class="bg-[#100804] px-3 py-1.5 border-2 border-[#4a2810] shadow-[inset_2px_2px_0_#000] flex items-center space-x-2">
        <span class="text-lg animate-bounce">🪙</span>
        <div class="text-right">
          <div class="text-[8px] font-pixel-title text-[#92400e]">BURSA REAL</div>
          <div class="text-xs font-pixel-title text-[#f59e0b]">200 <span class="text-[9px] text-[#fde68a]">OURO/MÊS</span></div>
        </div>
      </div>

      <!-- Player Avatar Frame -->
      <div class="w-10 h-10 bg-[#3a2010] border-2 border-[#120803] shadow-[inset_2px_2px_0_#6d3e1e,0_2px_0_#000] flex items-center justify-center text-lg cursor-pointer hover:bg-[#4a2a16] transition" title="Comandante do Império">
        👑
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const currentTime = ref('14:00')

const updateClock = () => {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  currentTime.value = `${hours}:${minutes}`
}

let timer = null
onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
