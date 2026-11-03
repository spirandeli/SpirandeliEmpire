<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Business Manager</h2>
        <p class="text-xs text-slate-400">Gerenciamento isolado e independente de cada negócio digital</p>
      </div>
      <router-link
        to="/factory"
        class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition"
      >
        + Criar Novo Negócio
      </router-link>
    </div>

    <!-- Businesses List -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="biz in businesses"
        :key="biz.id"
        class="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 flex flex-col justify-between"
      >
        <div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-amber-400 font-semibold border border-slate-700">
              {{ biz.category }}
            </span>
            <span
              class="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase"
              :class="biz.status === 'active' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'"
            >
              {{ biz.status }}
            </span>
          </div>

          <h3 class="text-lg font-bold text-slate-100">{{ biz.name }}</h3>
          <p class="text-xs text-slate-400 mt-2 leading-relaxed">{{ biz.description }}</p>

          <div class="grid grid-cols-2 gap-3 mt-4 p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 text-xs font-mono">
            <div>
              <span class="text-slate-500 block">Teto Orçamento:</span>
              <span class="text-amber-400 font-semibold">R$ {{ biz.budget_limit_brl }}</span>
            </div>
            <div>
              <span class="text-slate-500 block">Volume Isolado:</span>
              <span class="text-slate-300">{{ biz.storage_path }}</span>
            </div>
          </div>
        </div>

        <!-- Actions Bar -->
        <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center space-x-2">
            <button
              @click="toggleStatus(biz)"
              class="px-3 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              {{ biz.status === 'active' ? 'Pausar' : 'Ativar' }}
            </button>
            <button
              class="px-3 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              Backup
            </button>
          </div>
          <button
            class="px-3 py-1.5 text-xs font-mono rounded text-red-400 hover:bg-red-950/50 transition border border-red-900/40"
          >
            Remover
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const businesses = ref([
  {
    id: 1,
    name: 'RISADA.exe',
    slug: 'risada-exe',
    category: 'YouTube Dark (Histórias Bíblicas)',
    status: 'provisioning',
    description: 'Canal de histórias bíblicas com ilustrações originais, voz brasileira masculina e roteiros biblicamente fiéis.',
    budget_limit_brl: '60.00',
    storage_path: 'storage/businesses/risada-exe',
  },
  {
    id: 2,
    name: 'KDP Factory',
    slug: 'kdp-factory',
    category: 'Amazon KDP Publishing',
    status: 'provisioning',
    description: 'Pipeline completo de produção de eBooks, devocionais, planos de leitura bíblica e diagramação para Amazon KDP.',
    budget_limit_brl: '50.00',
    storage_path: 'storage/businesses/kdp-factory',
  },
  {
    id: 3,
    name: 'Digital Products Factory',
    slug: 'digital-products',
    category: 'Digital Goods & PDFs',
    status: 'provisioning',
    description: 'Estudos bíblicos em PDF, planners devocionais, quiz bíblico e apostilas de alta conversão.',
    budget_limit_brl: '40.00',
    storage_path: 'storage/businesses/digital-products',
  },
  {
    id: 4,
    name: 'Printable Factory',
    slug: 'printable-factory',
    category: 'Printables & Artes',
    status: 'provisioning',
    description: 'Quadros, cartões, atividades infantis e artes originais de alta resolução para impressão física.',
    budget_limit_brl: '30.00',
    storage_path: 'storage/businesses/printable-factory',
  },
])

const toggleStatus = (biz) => {
  biz.status = biz.status === 'active' ? 'paused' : 'active'
}
</script>

