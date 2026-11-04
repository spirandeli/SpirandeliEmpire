<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Business Manager
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
            {{ businesses.length }} Negócios
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">Gerenciamento isolado e controle orçamentário independente de cada negócio digital</p>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="fetchBusinesses"
          :disabled="loading"
          class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{'animate-spin': loading}">↻</span> Atualizar
        </button>
        <router-link
          to="/factory"
          class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition shadow-md flex items-center gap-1.5 font-mono"
        >
          <span>+</span> Novo Negócio Digital
        </router-link>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && businesses.length === 0" class="text-center py-12 text-slate-500 text-xs font-mono">
      Carregando negócios do banco de dados...
    </div>

    <!-- Empty State -->
    <div v-else-if="businesses.length === 0" class="bg-slate-900/80 rounded-2xl border border-slate-800 p-8 text-center">
      <div class="text-3xl mb-2">📜</div>
      <h3 class="text-sm font-bold text-slate-200">Nenhum negócio digital cadastrado</h3>
      <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
        Utilize a Business Factory para criar seu primeiro negócio com estrutura de diretórios e governança automatizada.
      </p>
      <router-link
        to="/factory"
        class="mt-4 inline-block px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition font-mono"
      >
        Forjar Primeiro Negócio →
      </router-link>
    </div>

    <!-- Businesses List Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="biz in businesses"
        :key="biz.id"
        class="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 flex flex-col justify-between shadow-xl"
      >
        <div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-amber-400 font-semibold border border-slate-700">
              {{ biz.category }}
            </span>
            <span
              class="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase border"
              :class="biz.status === 'active' 
                ? 'bg-emerald-950 text-emerald-400 border-emerald-800' 
                : (biz.status === 'paused' ? 'bg-amber-950 text-amber-400 border-amber-800' : 'bg-slate-800 text-slate-400 border-slate-700')"
            >
              {{ biz.status }}
            </span>
          </div>

          <h3 class="text-lg font-bold text-slate-100 flex items-center justify-between">
            <span>{{ biz.name }}</span>
            <span class="text-xs font-mono text-slate-500 font-normal">#{{ biz.slug }}</span>
          </h3>
          <p class="text-xs text-slate-400 mt-2 leading-relaxed">{{ biz.description }}</p>

          <div class="grid grid-cols-2 gap-3 mt-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 text-xs font-mono">
            <div>
              <span class="text-slate-500 block text-[10px]">Teto Orçamento:</span>
              <span class="text-amber-400 font-semibold">R$ {{ biz.budget_limit_brl }}</span>
            </div>
            <div>
              <span class="text-slate-500 block text-[10px]">Gasto no Mês:</span>
              <span class="text-slate-300">R$ {{ biz.current_month_cost_brl || '0.00' }}</span>
            </div>
            <div class="col-span-2 pt-1 border-t border-slate-800">
              <span class="text-slate-500 block text-[10px]">Volume Isolado no Disco:</span>
              <span class="text-slate-300 truncate block text-[11px]">{{ biz.storage_path }}</span>
            </div>
          </div>
        </div>

        <!-- Actions Bar -->
        <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center space-x-2">
            <button
              @click="toggleStatus(biz)"
              :disabled="updatingId === biz.id"
              class="px-3 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <span v-if="updatingId === biz.id">Salvando...</span>
              <span v-else>{{ biz.status === 'active' ? 'Pausar' : 'Ativar' }}</span>
            </button>
            <router-link
              to="/jeffrey"
              class="px-3 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 transition flex items-center gap-1"
            >
              <span>🧙‍♂️ Falar com Jeffrey</span>
            </router-link>
          </div>

          <button
            @click="deleteBusiness(biz)"
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
import { ref, onMounted } from 'vue'
import axios from 'axios'

const businesses = ref([])
const loading = ref(false)
const updatingId = ref(null)

const fetchBusinesses = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/businesses')
    if (res.data?.businesses) {
      businesses.value = res.data.businesses
    }
  } catch (err) {
    console.error('Falha ao carregar negócios:', err)
  } finally {
    loading.value = false
  }
}

const toggleStatus = async (biz) => {
  updatingId.value = biz.id
  const nextStatus = biz.status === 'active' ? 'paused' : 'active'
  try {
    const res = await axios.patch(`/api/v1/businesses/${biz.id}/status`, {
      status: nextStatus,
    })
    if (res.data?.business) {
      biz.status = res.data.business.status
    }
  } catch (err) {
    alert('Erro ao atualizar status do negócio: ' + (err.response?.data?.message || err.message))
  } finally {
    updatingId.value = null
  }
}

const deleteBusiness = async (biz) => {
  if (!confirm(`Tem certeza que deseja remover o negócio "${biz.name}"?`)) return
  try {
    await axios.delete(`/api/v1/businesses/${biz.id}`)
    businesses.value = businesses.value.filter(b => b.id !== biz.id)
  } catch (err) {
    alert('Erro ao excluir negócio: ' + (err.response?.data?.message || err.message))
  }
}

onMounted(() => {
  fetchBusinesses()
})
</script>
