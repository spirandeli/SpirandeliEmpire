<template>
  <div
    class="relative flex h-screen w-screen overflow-hidden select-none p-2.5 sm:p-3.5 gap-3 sm:gap-4 bg-[#1a2e12] bg-cover bg-center"
    style="background-image: url('/assets/rpg-village-bg.jpg');"
  >
    <!-- Subtle warm vignette so UI panels pop clearly over the village -->
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/25 z-0"></div>

    <!-- Left Column: Profile + RPG Sidebar + Bottom Jeffrey Status -->
    <Sidebar class="relative z-20 shrink-0" />

    <!-- Right Column: Top Server Bar + Main Content Area -->
    <div class="relative z-10 flex-1 flex flex-col min-w-0 h-full overflow-hidden gap-3">
      <Header class="shrink-0" />
      <main class="flex-1 overflow-y-auto pr-1 pb-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Header from './components/Header.vue'
</script>
