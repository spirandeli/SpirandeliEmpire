<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <!-- 1. TOP KPI METRICS CARDS ROW (4 Cards) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <!-- KPI 1: Negócios no Ecossistema -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
            <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span class="truncate">Negócios no Ecossistema</span>
          </div>

          <div class="text-3xl font-bold font-mono text-white my-1.5">
            {{ displayBusinessesCount }}
          </div>

          <div class="text-xs font-semibold text-emerald-400 font-mono tracking-tight">
            TikTok Shop + 4 Ativos
          </div>
        </div>

        <div class="w-12 h-12 rounded-xl bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-xl shrink-0">
          💼
        </div>
      </div>

      <!-- KPI 2: Orçamento Mensal -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
            <span class="w-2 h-2 rounded-full bg-amber-400"></span>
            <span class="truncate">Orçamento Mensal</span>
          </div>

          <div class="my-1.5 flex items-baseline gap-1.5 flex-wrap">
            <span class="text-2xl sm:text-[26px] font-bold font-mono text-amber-400">
              R$ {{ formatBrl(financials.budget?.current_spent_brl ?? 0) }}
            </span>
            <span class="text-xs font-mono text-slate-400">
              / R$ {{ financials.budget?.monthly_limit_brl ?? 200 }}
            </span>
          </div>

          <div class="text-xs text-slate-400 font-medium">
            Teto estrito de segurança
          </div>
        </div>

        <div class="w-12 h-12 rounded-xl bg-amber-950/60 border border-amber-800/60 flex items-center justify-center text-xl shrink-0">
          💰
        </div>
      </div>

      <!-- KPI 3: Receita Confirmada -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span class="truncate">Receita Confirmada</span>
          </div>

          <div class="text-2xl sm:text-[26px] font-bold font-mono text-emerald-400 my-1.5">
            R$ {{ formatBrl(financials.total_revenue_brl ?? 0) }}
          </div>

          <div class="text-xs text-slate-400 font-medium">
            Sem projeções fictícias
          </div>
        </div>

        <div class="w-12 h-12 rounded-xl bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center text-xl shrink-0">
          📈
        </div>
      </div>

      <!-- KPI 4: Consumo VPS -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
            <span class="w-2 h-2 rounded-full bg-blue-400"></span>
            <span class="truncate">Consumo VPS</span>
          </div>

          <div class="text-2xl sm:text-[26px] font-bold font-mono text-cyan-400 my-1.5">
            RAM {{ vps.memory?.percentage || 28 }}%
          </div>

          <div class="text-xs text-slate-400 font-mono">
            CPU {{ vps.cpu_percent || 7.8 }}% • SSD {{ vps.disk?.percentage || 14 }}%
          </div>
        </div>

        <div class="w-12 h-12 rounded-xl bg-blue-950/60 border border-blue-800/60 flex items-center justify-center text-xl shrink-0">
          ⚡
        </div>
      </div>
    </div>

    <!-- 2. STRATEGIC BUSINESSES DASHBOARD CONTAINER -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-5">
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-slate-800">
        <div>
          <h2 class="text-lg font-bold text-slate-100 flex items-center gap-2.5">
            <span>🛡️ Negócios Estratégicos & Gestão Autônoma</span>
            <span class="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              Jeffrey Operando
            </span>
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            Cada negócio possui suas próprias Contas Vinculadas e Parâmetros para gestão automatizada do Jeffrey AI
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            v-if="extraBusinesses.length > 0"
            @click="showAllBusinesses = !showAllBusinesses"
            class="text-xs font-semibold text-amber-400 hover:text-amber-300 font-mono transition"
          >
            {{ showAllBusinesses ? 'Ocultar Extras' : `+ ${extraBusinesses.length} Negócios Extras` }}
          </button>
          <router-link
            to="/businesses"
            class="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs uppercase tracking-wide transition shadow-sm shadow-amber-500/20"
          >
            ⚙️ Gerenciar Contas & Parâmetros →
          </router-link>
        </div>
      </div>

      <!-- 5 Strategic Business Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <div
          v-for="card in strategicCards"
          :key="card.slug"
          @click="$router.push('/businesses')"
          class="bg-slate-950/70 border rounded-xl p-4 flex flex-col justify-between cursor-pointer hover:border-amber-500/50 hover:bg-slate-900/60 transition shadow-md group"
          :class="card.slug === 'tiktok-shop-afiliados' ? 'border-amber-500/40 bg-slate-900/40' : 'border-slate-800'"
        >
          <div class="space-y-3">
            <!-- Top Ribbon Banner & Status -->
            <div class="flex items-center justify-between gap-1">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30">
                {{ card.ribbon }}
              </span>
              <span
                class="px-2 py-0.5 text-[9px] font-mono font-bold rounded uppercase"
                :class="card.autoEnabled ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400 border border-slate-700'"
              >
                {{ card.autoEnabled ? '● AUTO' : 'PRONTO' }}
              </span>
            </div>

            <!-- Business Brand Icon + Name -->
            <div class="flex items-center gap-2.5">
              <div
                v-if="card.badgeType === 'tiktok'"
                class="w-7 h-7 rounded-lg bg-black border border-pink-500/40 flex items-center justify-center text-cyan-400 text-xs font-bold shrink-0"
              >
                ♪
              </div>
              <div
                v-else-if="card.badgeType === 'youtube'"
                class="w-7 h-7 rounded-lg bg-red-950 border border-red-700 flex items-center justify-center text-red-300 text-xs font-bold shrink-0"
              >
                ▶
              </div>
              <div
                v-else-if="card.badgeType === 'kdp'"
                class="w-7 h-7 rounded-lg bg-amber-950 border border-amber-700 flex items-center justify-center text-amber-300 font-serif text-sm font-bold shrink-0"
              >
                a
              </div>
              <div
                v-else-if="card.badgeType === 'pdf'"
                class="w-7 h-7 rounded-lg bg-rose-950 border border-rose-800 flex items-center justify-center text-rose-300 text-[9px] font-bold shrink-0"
              >
                PDF
              </div>
              <div
                v-else
                class="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs shrink-0"
              >
                🖨️
              </div>

              <h3 class="font-bold text-sm text-slate-100 group-hover:text-amber-400 transition leading-tight truncate">
                {{ card.name }}
              </h3>
            </div>

            <!-- Business Description -->
            <p class="text-xs text-slate-400 leading-relaxed min-h-[42px] line-clamp-3">
              {{ card.description }}
            </p>

            <!-- Linked Accounts & Goal Pill -->
            <div class="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1 font-mono">
              <div class="truncate text-slate-300">
                <span class="text-slate-500">Contas:</span> <span class="text-amber-400 font-semibold">{{ card.primaryHandle }}</span>
              </div>
              <div class="truncate text-slate-400 text-[11px]">
                Meta: <strong class="text-white">{{ card.dailyGoal }}/dia</strong> • Teto: R$ {{ formatBrl(card.budget_limit_brl) }}
              </div>
            </div>
          </div>

          <!-- Bottom Footer -->
          <div class="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
            <span>{{ card.storage_path }}</span>
            <span class="text-amber-400 group-hover:translate-x-0.5 transition">→</span>
          </div>
        </div>
      </div>

      <!-- Optional Expandable Row for Extra Businesses -->
      <div
        v-if="showAllBusinesses && extraBusinesses.length > 0"
        class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-800"
      >
        <div
          v-for="biz in extraBusinesses"
          :key="biz.id || biz.slug"
          @click="$router.push('/businesses')"
          class="bg-slate-950/70 border border-slate-800 rounded-xl p-4 flex flex-col justify-between cursor-pointer hover:border-slate-700 transition"
        >
          <div>
            <div class="mb-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-amber-400 border border-slate-700">
                {{ biz.category || 'AFILIADOS' }}
              </span>
            </div>
            <h4 class="font-bold text-sm text-slate-100">{{ biz.name }}</h4>
            <p class="text-xs text-slate-400 mt-1 line-clamp-2">{{ biz.description }}</p>
          </div>
          <div class="border-t border-slate-800 mt-3 pt-2 text-[11px] font-mono text-slate-500">
            Teto: R$ {{ formatBrl(biz.budget_limit_brl) }} | storage/{{ biz.storage_path }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const showAllBusinesses = ref(false)

const summary = ref({
  total_businesses: 5,
  active_businesses: 5,
  paused_businesses: 0,
  running_tasks: 0,
})

const financials = ref({
  total_revenue_brl: 0,
  total_expenses_brl: 0,
  estimated_profit_brl: 0,
  budget: {
    monthly_limit_brl: 200,
    current_spent_brl: 0,
    remaining_brl: 200,
    percentage_used: 0,
    warning_triggered: false,
  },
})

const vps = ref({
  cpu_percent: 7.8,
  memory: { percentage: 28, used_gb: 1.1, total_gb: 4 },
  disk: { percentage: 14, used_gb: 11, total_gb: 80 },
})

const businesses = ref([])

const defaultStrategicCards = [
  {
    slug: 'tiktok-shop-afiliados',
    ribbon: '🔥 TIKTOK SHOP',
    badgeType: 'tiktok',
    name: 'TikTok Shop Afiliados',
    description: 'Mineração de produtos virais, roteiros de alta conversão e vídeos Anti-Ban para TikTok Shop.',
    budget_limit_brl: 50,
    storage_path: 'businesses/tiktok-shop-afiliados',
    sprite: '/assets/sprites/biz-youtube.png',
    defaultHandle: '@achadinhos.spirandeli',
    defaultGoal: 5,
  },
  {
    slug: 'risada-exe',
    ribbon: 'YOUTUBE DARK',
    badgeType: 'youtube',
    name: 'RISADA.exe',
    description: 'Canal de histórias bíblicas com ilustrações originais, voz brasileira e roteiros fiéis.',
    budget_limit_brl: 60,
    storage_path: 'businesses/risada-exe',
    sprite: '/assets/sprites/biz-youtube.png',
    defaultHandle: '@risada.exe',
    defaultGoal: 2,
  },
  {
    slug: 'kdp-factory',
    ribbon: 'AMAZON KDP',
    badgeType: 'kdp',
    name: 'KDP Factory',
    description: 'Pipeline automatizado de produção de eBooks, devocionais e estudos para Amazon KDP.',
    budget_limit_brl: 50,
    storage_path: 'businesses/kdp-factory',
    sprite: '/assets/sprites/biz-kdp.png',
    defaultHandle: 'Spirandeli Publishing',
    defaultGoal: 1,
  },
  {
    slug: 'digital-products',
    ribbon: 'PDFS & PLANNERS',
    badgeType: 'pdf',
    name: 'Digital Products',
    description: 'Estudos bíblicos em PDF, cronologias e materiais devocionais de alta conversão.',
    budget_limit_brl: 60,
    storage_path: 'businesses/digital-products',
    sprite: '/assets/sprites/biz-pdf.png',
    defaultHandle: '@spirandeli.digital',
    defaultGoal: 2,
  },
  {
    slug: 'printable-factory',
    ribbon: 'PRINTABLES',
    badgeType: 'printable',
    name: 'Printable Factory',
    description: 'Quadros, cartões e artes originais de alta resolução para impressão.',
    budget_limit_brl: 30,
    storage_path: 'businesses/printable-factory',
    sprite: '/assets/sprites/biz-printable.png',
    defaultHandle: '@spirandeli.printables',
    defaultGoal: 3,
  },
]

const strategicCards = computed(() => {
  return defaultStrategicCards.map((def) => {
    const found = businesses.value.find((b) => b.slug === def.slug)
    if (!found) {
      return {
        ...def,
        primaryHandle: def.defaultHandle,
        dailyGoal: def.defaultGoal,
        autoEnabled: true,
      }
    }
    const accs = found.accounts_list || found.accounts || found.settings?.accounts || []
    const params = found.automation_config || found.automation_params || found.settings?.automation_params || {}
    return {
      ...def,
      name: found.name || def.name,
      description: found.description || def.description,
      budget_limit_brl: found.budget_limit_brl ?? def.budget_limit_brl,
      storage_path: found.storage_path || def.storage_path,
      primaryHandle: accs[0]?.handle || def.defaultHandle,
      dailyGoal: params.daily_deliverables_goal ?? def.defaultGoal,
      autoEnabled: params.auto_enabled !== false,
    }
  })
})

const extraBusinesses = computed(() => {
  const coreSlugs = new Set(defaultStrategicCards.map((c) => c.slug))
  return businesses.value.filter((b) => !coreSlugs.has(b.slug))
})

const displayBusinessesCount = computed(() => {
  return Math.max(summary.value.total_businesses || 5, businesses.value.length || 5)
})

const formatBrl = (val) => {
  const num = Number(val || 0)
  return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const fetchDashboardData = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/dashboard')
    if (res.data) {
      if (res.data.summary) summary.value = res.data.summary
      if (res.data.financials) financials.value = res.data.financials
      if (res.data.vps) vps.value = res.data.vps
      if (res.data.businesses) businesses.value = res.data.businesses
    }
  } catch (err) {
    console.error('Falha ao obter telemetria do Dashboard:', err)
  } finally {
    loading.value = false
  }
}

let timer = null
onMounted(() => {
  fetchDashboardData()
  timer = setInterval(fetchDashboardData, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
