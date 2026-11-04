<template>
  <div class="space-y-6 max-w-7xl mx-auto pb-10">
    <!-- 1. TOP GUILD HALL BANNER & COMANDANTE PROFILE -->
    <div class="pixel-wood p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center space-x-4">
        <div class="w-16 h-16 bg-[#160c07] border-4 border-[#5a381f] shadow-[inset_3px_3px_0_#0a0503,0_4px_0_#000] flex items-center justify-center text-3xl relative">
          👑
          <span class="absolute -bottom-2 -right-2 bg-[#d97706] text-[#1c0e05] border-2 border-[#120803] font-pixel-title text-[8px] px-1 py-0.5">
            NV.30
          </span>
        </div>

        <div>
          <div class="flex items-center gap-2">
            <h2 class="font-pixel-title text-sm sm:text-base text-[#fde68a] uppercase tracking-wider">
              Feudo Central do Império
            </h2>
            <span class="text-[9px] font-pixel-title px-1.5 py-0.5 bg-[#15803d] text-[#dcfce7] border border-[#14532d]">
              SISTEMA OPERACIONAL v3.0
            </span>
          </div>
          <p class="font-pixel-body text-xs text-[#d6b88d] mt-1">
            SpirandeliEmpire OS • Comandante Soberano • Orquestração Ativa: Jeffrey AI
          </p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center space-x-3">
        <button
          @click="fetchDashboardData"
          :disabled="loading"
          class="pixel-btn-wood py-2.5 px-3 flex items-center gap-1.5 text-xs"
        >
          <span :class="{'animate-spin': loading}">↻</span> ATUALIZAR TELEMETRIA
        </button>
        <router-link
          to="/jeffrey"
          class="pixel-btn-wood py-2.5 px-3 flex items-center gap-1.5 text-xs"
        >
          <span>🧙‍♂️</span> AUDIÊNCIA COM JEFFREY
        </router-link>
        <router-link
          to="/factory"
          class="pixel-btn-gold py-2.5 px-3 flex items-center gap-1.5 text-xs"
        >
          <span>⚒️</span> FORJAR NEGÓCIO
        </router-link>
      </div>
    </div>

    <!-- 2. TELEMETRY & SYSTEM HEALTH (CPU, RAM, DISK, BUDGET) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Infra HP (Status) -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">❤️</span>
            <span class="font-pixel-title text-[9px] text-[#fca5a5]">HP INFRAESTRUTURA</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">100%</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-hp h-full w-[100%] transition-all duration-500"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>{{ summary.active_businesses }} Negócios Ativos</span>
          <span class="text-[#86efac]">● {{ summary.running_tasks }} Tarefas Rodando</span>
        </div>
      </div>

      <!-- 2. CPU / RAM -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">⚡</span>
            <span class="font-pixel-title text-[9px] text-[#86efac]">ENERGIA / RAM</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">{{ vps.memory?.percentage || 0 }}%</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-energy h-full transition-all duration-500" :style="{ width: (vps.memory?.percentage || 0) + '%' }"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>CPU: {{ vps.cpu_percent || 0 }}%</span>
          <span>Disco: {{ vps.disk?.percentage || 0 }}%</span>
        </div>
      </div>

      <!-- 3. AI Gateway Status -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">🔮</span>
            <span class="font-pixel-title text-[9px] text-[#67e8f9]">MANA DE IA</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">ONLINE</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-mana h-full w-[100%] transition-all duration-500"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>Gemini + OpenAI + Llama</span>
          <span class="text-[#38bdf8]">Híbrido</span>
        </div>
      </div>

      <!-- 4. Budget Ceil R$ 200/month -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">🪙</span>
            <span class="font-pixel-title text-[9px] text-[#fcd34d]">COFRE (R$ 200/MÊS)</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#f59e0b]">R$ {{ financials.budget?.current_spent_brl || '0.00' }}</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div
            class="pixel-bar-gold h-full transition-all duration-500"
            :style="{ width: Math.min(100, financials.budget?.percentage_used || 0) + '%' }"
          ></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>Restante: R$ {{ financials.budget?.remaining_brl || '200.00' }}</span>
          <span :class="financials.budget?.warning_triggered ? 'text-red-400 font-bold' : 'text-[#86efac]'">
            {{ financials.budget?.percentage_used || 0 }}% Usado
          </span>
        </div>
      </div>
    </div>

    <!-- 3. REAL BUSINESSES DIRECTORY -->
    <div class="pixel-wood p-5">
      <div class="flex justify-between items-center mb-4 border-b-2 border-[#3d2415] pb-2">
        <div class="flex items-center space-x-2">
          <span class="text-lg">📜</span>
          <h3 class="font-pixel-title text-xs text-[#fde68a] uppercase">Feudos Digitais em Operação</h3>
        </div>
        <router-link to="/businesses" class="text-xs text-[#38bdf8] hover:underline font-pixel-body">
          Ver Gerenciador Completo →
        </router-link>
      </div>

      <div v-if="loading && businesses.length === 0" class="text-center py-8 text-[#d6b88d] text-xs">
        Consultando banco de dados do Império...
      </div>

      <div v-else-if="businesses.length === 0" class="text-center py-8 text-[#d6b88d] text-xs">
        Nenhum negócio digital cadastrado. Utilize o botão "FORJAR NEGÓCIO" para iniciar.
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="biz in businesses"
          :key="biz.id"
          class="bg-[#120904] border-2 border-[#3d2415] p-3.5 flex flex-col justify-between shadow-[inset_2px_2px_0_#000]"
        >
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-base">{{ getBusinessIcon(biz.category) }}</span>
              <span
                class="text-[8px] font-pixel-title px-1.5 py-0.5 border"
                :class="biz.status === 'active' ? 'bg-[#14532d] text-[#86efac] border-[#22c55e]' : 'bg-[#78350f] text-[#fde68a] border-[#d97706]'"
              >
                {{ biz.status }}
              </span>
            </div>
            <h4 class="font-pixel-title text-[11px] text-[#fde68a]">{{ biz.name }}</h4>
            <p class="font-pixel-body text-[11px] text-[#d6b88d] mt-1 line-clamp-2">
              {{ biz.description }}
            </p>
          </div>

          <div class="mt-3 pt-2 border-t border-[#26140b] flex justify-between items-center text-[10px] font-pixel-body">
            <span class="text-[#a16207]">Teto: R$ {{ biz.budget_limit_brl }}</span>
            <span class="text-[#38bdf8]">{{ biz.tasks_count || 0 }} Tarefas</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 4. RECENT TASKS & DECISIONS -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Recent Agent Tasks -->
      <div class="pixel-wood p-4">
        <div class="flex items-center space-x-2 mb-3 border-b-2 border-[#3d2415] pb-2">
          <span class="text-base">⚔️</span>
          <h3 class="font-pixel-title text-xs text-[#fde68a] uppercase">Tarefas Recentes dos Agentes</h3>
        </div>
        <div class="space-y-2 text-xs font-pixel-body">
          <div
            v-for="task in recentTasks"
            :key="task.id"
            class="p-2.5 bg-[#120904] border border-[#3d2415] flex items-center justify-between"
          >
            <div>
              <div class="text-[#fde68a] font-semibold">{{ task.title }}</div>
              <div class="text-[10px] text-[#a16207]">{{ task.agent_name }} • {{ task.type }}</div>
            </div>
            <span
              class="text-[9px] px-1.5 py-0.5 border"
              :class="task.status === 'completed' ? 'text-[#86efac] border-[#22c55e]' : 'text-[#fcd34d] border-[#d97706]'"
            >
              {{ task.status }}
            </span>
          </div>
          <div v-if="recentTasks.length === 0" class="text-center py-4 text-[#a16207]">
            Nenhuma tarefa executada recentemente.
          </div>
        </div>
      </div>

      <!-- Recent Decisions Audit -->
      <div class="pixel-wood p-4">
        <div class="flex items-center space-x-2 mb-3 border-b-2 border-[#3d2415] pb-2">
          <span class="text-base">📜</span>
          <h3 class="font-pixel-title text-xs text-[#fde68a] uppercase">Auditoria de Decisões de Jeffrey</h3>
        </div>
        <div class="space-y-2 text-xs font-pixel-body">
          <div
            v-for="dec in recentDecisions"
            :key="dec.id"
            class="p-2.5 bg-[#120904] border border-[#3d2415]"
          >
            <div class="flex justify-between items-center text-[10px] text-[#38bdf8]">
              <span>{{ dec.agent_name }} ({{ dec.action_type }})</span>
              <span class="text-[#a16207]">{{ dec.created_at ? new Date(dec.created_at).toLocaleTimeString() : '' }}</span>
            </div>
            <div class="text-[#d6b88d] mt-1">{{ dec.justification }}</div>
          </div>
          <div v-if="recentDecisions.length === 0" class="text-center py-4 text-[#a16207]">
            Nenhum registro de auditoria no momento.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const summary = ref({
  total_businesses: 0,
  active_businesses: 0,
  paused_businesses: 0,
  running_tasks: 0,
  pending_approvals: 0,
  total_projects: 0,
  total_conversations: 0,
})

const financials = ref({
  total_revenue_brl: '0.00',
  total_expenses_brl: '0.00',
  estimated_profit_brl: '0.00',
  budget: {
    monthly_limit_brl: 200,
    current_spent_brl: 0,
    remaining_brl: 200,
    percentage_used: 0,
    warning_triggered: false,
  },
})

const vps = ref({
  cpu_percent: 0,
  memory: { percentage: 0, used_gb: 0, total_gb: 0 },
  disk: { percentage: 0, used_gb: 0, total_gb: 0 },
})

const businesses = ref([])
const recentTasks = ref([])
const recentDecisions = ref([])

const fetchDashboardData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/dashboard')
    if (res.data) {
      if (res.data.summary) summary.value = res.data.summary
      if (res.data.financials) financials.value = res.data.financials
      if (res.data.vps) vps.value = res.data.vps
      if (res.data.businesses) businesses.value = res.data.businesses
      if (res.data.recent_tasks) recentTasks.value = res.data.recent_tasks
      if (res.data.recent_decisions) recentDecisions.value = res.data.recent_decisions
    }
  } catch (err) {
    console.error('Falha ao obter telemetria do Dashboard:', err)
  } finally {
    loading.value = false
  }
}

const getBusinessIcon = (category) => {
  if (category?.includes('YouTube')) return '🎬'
  if (category?.includes('KDP')) return '📖'
  if (category?.includes('Digital')) return '🧪'
  if (category?.includes('Printable')) return '🖼️'
  return '📦'
}

let timer = null
onMounted(() => {
  fetchDashboardData()
  timer = setInterval(fetchDashboardData, 30000) // 30s auto-refresh
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
