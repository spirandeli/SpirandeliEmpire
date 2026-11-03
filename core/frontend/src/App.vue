<template>
  <div class="flex h-screen bg-[#120a06] text-[#f7e6c4] overflow-hidden font-pixel-body select-none">
    <!-- RPG Sidebar -->
    <Sidebar />

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <Header />
      <main class="flex-1 overflow-y-auto p-6 bg-[#160c07] bg-[radial-gradient(#26140b_1px,transparent_1px)] [background-size:16px_16px]">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Header from './components/Header.vue'
</script>
