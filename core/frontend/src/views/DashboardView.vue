<template>
  <div class="space-y-4 max-w-[1400px] w-full">
    <!-- 1. TOP KPI PARCHMENT CARDS ROW (4 Cards) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5">
      <!-- KPI 1: Negócios no Ecossistema -->
      <div class="rpg-kpi-frame rpg-rivets">
        <div class="rpg-parchment-inner p-3 h-full flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 text-[12px] font-bold text-[#2b1507]">
              <span class="inline-flex items-end gap-0.5 h-3.5">
                <span class="w-1 h-2 bg-[#2563eb] border border-[#1e0d04]"></span>
                <span class="w-1 h-3 bg-[#3b82f6] border border-[#1e0d04]"></span>
                <span class="w-1 h-3.5 bg-[#60a5fa] border border-[#1e0d04]"></span>
              </span>
              <span class="truncate">Negócios no Ecossistema</span>
            </div>

            <div class="text-3xl font-black text-[#1e0e04] leading-tight my-0.5 pl-1">
              {{ displayBusinessesCount }}
            </div>

            <div class="text-[12px] font-extrabold text-[#4ade80] rpg-text-outline-sm tracking-wide">
              TikTok Shop + 4 Ativos
            </div>
          </div>

          <img
            src="/assets/sprites/kpi-businesses.png"
            alt="Negócios"
            class="w-14 h-12 object-contain shrink-0 drop-shadow-[0_2px_2px_rgba(0,0,0,0.35)]"
          />
        </div>
      </div>

      <!-- KPI 2: Orçamento Mensal -->
      <div class="rpg-kpi-frame rpg-rivets">
        <div class="rpg-parchment-inner p-3 h-full flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 text-[12px] font-bold text-[#2b1507]">
              <span class="w-3.5 h-3.5 rounded-full bg-[#fbbf24] border border-[#3a1e0b] inline-flex items-center justify-center text-[9px] font-black text-[#3a1e0b]">$</span>
              <span class="truncate">Orçamento Mensal</span>
            </div>

            <div class="leading-tight my-1 flex items-baseline gap-1 flex-wrap">
              <span class="text-2xl sm:text-[26px] font-black text-[#fbbf24] rpg-text-outline">
                R$ {{ formatBrl(financials.budget?.current_spent_brl ?? 0) }}
              </span>
              <span class="text-sm font-extrabold text-white rpg-text-outline-sm">
                / R$ {{ financials.budget?.monthly_limit_brl ?? 200 }}
              </span>
            </div>

            <div class="text-[11px] font-bold text-[#3b1f0b]">
              Teto estrito de segurança
            </div>
          </div>

          <img
            src="/assets/sprites/kpi-budget.png"
            alt="Orçamento"
            class="w-12 h-13 object-contain shrink-0 drop-shadow-[0_2px_2px_rgba(0,0,0,0.35)]"
          />
        </div>
      </div>

      <!-- KPI 3: Receita Confirmada -->
      <div class="rpg-kpi-frame rpg-rivets">
        <div class="rpg-parchment-inner p-3 h-full flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 text-[12px] font-bold text-[#2b1507]">
              <span class="w-3.5 h-3.5 rounded-full bg-[#22c55e] border border-[#14532d] inline-flex items-center justify-center text-[9px] font-black text-white">✓</span>
              <span class="truncate">Receita Confirmada</span>
            </div>

            <div class="text-2xl sm:text-[26px] font-black text-[#4ade80] rpg-text-outline leading-tight my-1">
              R$ {{ formatBrl(financials.total_revenue_brl ?? 0) }}
            </div>

            <div class="text-[11px] font-bold text-[#3b1f0b]">
              Sem projeções fictícias
            </div>
          </div>

          <img
            src="/assets/sprites/kpi-revenue.png"
            alt="Receita"
            class="w-12 h-13 object-contain shrink-0 drop-shadow-[0_2px_2px_rgba(0,0,0,0.35)]"
          />
        </div>
      </div>

      <!-- KPI 4: Consumo VPS -->
      <div class="rpg-kpi-frame rpg-rivets">
        <div class="rpg-parchment-inner p-3 h-full flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 text-[12px] font-bold text-[#2b1507]">
              <span class="w-3.5 h-3.5 rounded-full bg-[#38bdf8] border border-[#0c4a6e] inline-block"></span>
              <span class="truncate">Consumo VPS</span>
            </div>

            <div class="text-2xl sm:text-[26px] font-black text-[#60a5fa] rpg-text-outline leading-tight my-1">
              RAM {{ vps.memory?.percentage || 28 }}%
            </div>

            <div class="text-[11px] font-extrabold text-[#2b1507]">
              CPU {{ vps.cpu_percent || 7.8 }}% • SSD {{ vps.disk?.percentage || 14 }}%
            </div>
          </div>

          <img
            src="/assets/sprites/kpi-vps.png"
            alt="Consumo VPS"
            class="w-13 h-12 object-contain shrink-0 drop-shadow-[0_2px_2px_rgba(0,0,0,0.35)]"
          />
        </div>
      </div>
    </div>

    <!-- 2. STRATEGIC BUSINESSES WOODEN BOARD -->
    <div class="relative pt-3">
      <!-- Raised Wooden Nameplate Tab (Top-Left) -->
      <div class="inline-flex items-center gap-2 pixel-wood rpg-rivets px-3 sm:px-4 py-1 sm:py-1.5 ml-2 sm:ml-3 -mb-3 relative z-20 max-w-[90%]">
        <img
          src="/assets/sprites/icon-shop.png"
          alt="Loja"
          class="w-6 h-5 sm:w-7 sm:h-6 object-contain shrink-0"
        />
        <h2 class="font-extrabold text-xs sm:text-sm md:text-[15px] text-[#fff6e0] tracking-wide rpg-text-outline-sm truncate">
          Negócios Estratégicos & Gestão Autônoma
        </h2>
      </div>

      <!-- Main Wooden Container Frame -->
      <div class="pixel-wood rpg-rivets p-2.5 sm:p-3.5 pt-4 sm:pt-5">
        <!-- Top Wooden Horizontal Beam Decoration -->
        <div class="flex items-center justify-between mb-3 px-1 flex-wrap gap-2">
          <span class="text-[11px] text-[#d9bc8c] font-medium">
            Cada negócio possui suas próprias Contas Vinculadas e Parâmetros para gestão automatizada do Jeffrey AI
          </span>
          <div class="flex items-center gap-3">
            <button
              v-if="extraBusinesses.length > 0"
              @click="showAllBusinesses = !showAllBusinesses"
              class="text-[11px] font-bold text-[#fbbf24] hover:underline"
            >
              {{ showAllBusinesses ? 'Ocultar Extras' : `+ ${extraBusinesses.length} Negócios Extras` }}
            </button>
            <router-link
              to="/businesses"
              class="pixel-btn-gold px-3 py-1 text-[11px] font-extrabold uppercase"
            >
              ⚙️ Gerenciar Contas & Parâmetros →
            </router-link>
          </div>
        </div>

        <!-- 5 Strategic Business Parchment Cards Grid (TikTok Shop Featured #1) -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          <div
            v-for="card in strategicCards"
            :key="card.slug"
            @click="$router.push('/businesses')"
            class="rpg-parchment-inner p-3.5 pt-3 flex flex-col justify-between cursor-pointer hover:brightness-[1.03] transition-all border-[3px] shadow-[0_4px_0_#1c0c03]"
            :class="card.slug === 'tiktok-shop-afiliados' ? 'border-[#d97706] ring-2 ring-[#fbbf24]/60' : 'border-[#2b1507]'"
          >
            <div>
              <!-- Top Ribbon Banner -->
              <div class="text-center mb-2.5 flex items-center justify-between gap-1">
                <span class="rpg-ribbon">
                  {{ card.ribbon }}
                </span>
                <span
                  class="px-1.5 py-0.5 text-[9px] font-black rounded uppercase"
                  :class="card.autoEnabled ? 'bg-emerald-800 text-emerald-100' : 'bg-[#3b200e] text-[#fde68a]'"
                >
                  {{ card.autoEnabled ? '🤖 AUTO ON' : '⚙️ PRONTO' }}
                </span>
              </div>

              <!-- Business Brand Icon + Name -->
              <div class="flex items-center gap-2 mb-2">
                <div
                  v-if="card.badgeType === 'tiktok'"
                  class="w-8 h-7 rounded-[4px] bg-[#0f172a] border-2 border-[#ec4899] flex items-center justify-center text-[#38bdf8] text-xs font-black shadow-sm shrink-0"
                >
                  ♪
                </div>
                <div
                  v-else-if="card.badgeType === 'youtube'"
                  class="w-8 h-6 rounded-[4px] bg-[#dc2626] border-2 border-[#2b1507] flex items-center justify-center text-white text-[10px] font-black shadow-sm shrink-0"
                >
                  ▶
                </div>
                <div
                  v-else-if="card.badgeType === 'kdp'"
                  class="w-7 h-7 rounded-[4px] bg-[#2b1507] text-[#fbbf24] flex flex-col items-center justify-center font-serif font-black text-lg leading-none shrink-0"
                >
                  <span>a</span>
                </div>
                <div
                  v-else-if="card.badgeType === 'pdf'"
                  class="w-7 h-8 rounded-[3px] bg-[#dc2626] border-2 border-[#2b1507] flex items-center justify-center text-white text-[9px] font-black tracking-tighter shrink-0"
                >
                  PDF
                </div>
                <div
                  v-else
                  class="w-8 h-7 rounded-[4px] bg-[#334155] border-2 border-[#1e293b] flex items-center justify-center text-white text-sm shrink-0"
                >
                  🖨️
                </div>

                <h3 class="font-extrabold text-[14px] text-[#1e0d04] leading-tight truncate">
                  {{ card.name }}
                </h3>
              </div>

              <!-- Business Description -->
              <p class="text-[11.5px] text-[#3a1f0d] font-medium leading-snug min-h-[44px] line-clamp-3">
                {{ card.description }}
              </p>

              <!-- Linked Accounts & Goal Pill -->
              <div class="mt-2 p-1.5 rounded bg-[#f5e3c3] border border-[#b88746] text-[10.5px] text-[#2b1507] space-y-0.5">
                <div class="truncate font-bold">
                  🔐 Contas: <span class="text-[#78350f]">{{ card.primaryHandle }}</span>
                </div>
                <div class="truncate">
                  🎯 Meta: <strong>{{ card.dailyGoal }}/dia</strong> • Teto: R$ {{ formatBrl(card.budget_limit_brl) }}
                </div>
              </div>
            </div>

            <!-- Bottom Pixel-Art Scene Illustration -->
            <div class="mt-2.5 pt-1 flex items-end justify-center h-12 overflow-hidden">
              <img
                :src="card.sprite"
                :alt="card.name"
                class="h-full w-auto object-contain"
              />
            </div>
          </div>
        </div>

        <!-- Optional Expandable Row for Extra Businesses -->
        <div
          v-if="showAllBusinesses && extraBusinesses.length > 0"
          class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mt-3 pt-3 border-t-2 border-[#3b200e]"
        >
          <div
            v-for="biz in extraBusinesses"
            :key="biz.id || biz.slug"
            @click="$router.push('/businesses')"
            class="rpg-parchment-inner p-3 flex flex-col justify-between cursor-pointer hover:brightness-[1.03] transition border-2 border-[#2b1507]"
          >
            <div>
              <div class="text-center mb-2">
                <span class="rpg-ribbon">{{ biz.category || 'AFILIADOS' }}</span>
              </div>
              <h4 class="font-extrabold text-sm text-[#1e0d04]">{{ biz.name }}</h4>
              <p class="text-[11px] text-[#3a1f0d] mt-1 line-clamp-2">{{ biz.description }}</p>
            </div>
            <div class="border-t border-[#b88746] mt-2 pt-1.5 text-[10.5px] font-semibold text-[#2b1507]">
              Teto: R$ {{ formatBrl(biz.budget_limit_brl) }} | storage/{{ biz.storage_path }}
            </div>
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
