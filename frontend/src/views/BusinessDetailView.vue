<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import AgentChatDrawer from '@/components/AgentChatDrawer.vue'
import BusinessGrowthTab from '@/components/BusinessGrowthTab.vue'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'

const route = useRoute()
const router = useRouter()
const businessStore = useBusinessStore()
const swal = useSwal()

const businessId = route.params.id
const activeTab = ref('canvas') // canvas | tiktok | automations | tasks
const isChatDrawerOpen = ref(false)
const miningInProgress = ref(false)
const tasks = ref([])
const loadingTasks = ref(false)

onMounted(async () => {
  await loadBusiness()
  await loadTasks()
})

async function loadBusiness() {
  await businessStore.fetchBusiness(businessId)
}

async function loadTasks() {
  loadingTasks.value = true
  try {
    const res = await api.get('/tasks', { params: { business_id: businessId } })
    tasks.value = res.data.data || []
  } catch {
    tasks.value = []
  } finally {
    loadingTasks.value = false
  }
}

const business = computed(() => businessStore.currentBusiness || {})

const canvasData = computed(() => {
  return business.value?.canvas || {
    value_propositions: ['Produtos testados com alta conversão e apelo visual direto.'],
    customer_segments: ['Jovens e adultos entre 18 e 35 anos que compram por impulso no TikTok.'],
    channels: ['TikTok Orgânico', 'TikTok Shop Showcase', 'Shorts / Reels'],
    customer_relationships: ['Comunicação dinâmica nos comentários, senso de comunidade e reviews sinceros.'],
    revenue_streams: ['Comissão de afiliados (15% a 25%) em produtos físicos.'],
    key_resources: ['Conta TikTok Shop Afiliado ativa', 'Cérebro Gemini 3.8 para roteirização e mineração.'],
    key_activities: ['Mineração algorítmica diária', 'Gravação e aprovação de 3 roteiros diários', 'Publicação nos horários de pico.'],
    key_partners: ['Lojas parceiras com selo de envio rápido', 'Plataforma TikTok Creator Marketplace.'],
    cost_structure: ['Custo de amostras de produtos (quando necessário)', 'VPS e infraestrutura de automação.'],
  }
})

const brandRules = computed(() => {
  return business.value?.brand_rules || {
    tone_of_voice: 'Persuasivo, enérgico, confiável e focado em resolver uma dor imediata nos primeiros 3 segundos.',
    target_audience: 'Consumidores de compras por impulso no TikTok Brasil.',
    guidelines: ['Sempre incluir demonstração do produto em ação', 'Nunca fazer promessas falsas de entrega', 'Adicionar chamada clara para o link amarelo.'],
  }
})

const tiktokProducts = computed(() => {
  return business.value?.tiktok_products || []
})

const automations = computed(() => {
  return business.value?.automations || []
})

async function handleToggleStatus() {
  try {
    if (business.value.status === 'active') {
      await businessStore.pauseBusiness(businessId)
      swal.toast('Venture pausado com sucesso.', 'info')
    } else {
      await businessStore.activateBusiness(businessId)
      swal.toast('Venture ativado! Workers operando.', 'success')
    }
    await loadBusiness()
  } catch (err) {
    swal.error('Erro ao alterar status', err.response?.data?.message || err.message)
  }
}

async function handleMineNow() {
  miningInProgress.value = true
  try {
    await api.post(`/businesses/${businessId}/mine`)
    swal.toast('Job de mineração despachado na fila! Novos produtos aparecerão em breve.', 'success')
    setTimeout(async () => {
      await loadBusiness()
    }, 4000)
  } catch (err) {
    swal.error('Erro ao acionar mineração', err.response?.data?.message || err.message)
  } finally {
    miningInProgress.value = false
  }
}

async function toggleAutomation(automation) {
  try {
    const currentState = automation.is_enabled ?? automation.is_active ?? true
    const updatedStatus = !currentState
    await api.put(`/businesses/${businessId}/automations/${automation.id}`, {
      is_enabled: updatedStatus,
      is_active: updatedStatus,
    })
    automation.is_enabled = updatedStatus
    automation.is_active = updatedStatus
    swal.toast(
      updatedStatus ? 'Automação ativada!' : 'Automação pausada.',
      updatedStatus ? 'success' : 'info'
    )
  } catch (err) {
    swal.error('Erro ao alterar automação', err.response?.data?.message || err.message)
  }
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex items-center space-x-3">
        <router-link to="/businesses" class="text-slate-400 hover:text-white transition">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </router-link>
        <div>
          <h1 class="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>{{ business.name || 'Carregando negócio...' }}</span>
            <span
              v-if="business.status"
              class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
              :class="business.status === 'active'
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                : 'bg-slate-800 text-slate-400 border-slate-700'"
            >
              {{ business.status === 'active' ? 'Ativo' : 'Pausado' }}
            </span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">
            Nicho: <span class="text-slate-200 font-semibold">{{ business.niche || 'Geral' }}</span> · Modelo: <span class="text-slate-200">{{ business.business_model || 'TikTok Shop Affiliate' }}</span>
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Top Action Bar -->
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <!-- Navegação por Abas -->
        <div class="flex items-center space-x-2 overflow-x-auto">
          <button
            @click="activeTab = 'growth'"
            class="px-3.5 py-2 text-xs font-bold rounded-xl transition flex items-center space-x-1.5"
            :class="activeTab === 'growth' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm' : 'text-slate-400 hover:text-slate-200'"
          >
            <span>⚡</span>
            <span>ROI & Auto-Otimização</span>
          </button>
          <button
            @click="activeTab = 'canvas'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition"
            :class="activeTab === 'canvas' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
          >
            Business Model Canvas & Marca
          </button>
          <button
            @click="activeTab = 'tiktok'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center space-x-1.5"
            :class="activeTab === 'tiktok' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
          >
            <span>Vitrine TikTok Shop</span>
            <span class="px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px]">
              {{ tiktokProducts.length }}
            </span>
          </button>
          <button
            @click="activeTab = 'automations'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center space-x-1.5"
            :class="activeTab === 'automations' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
          >
            <span>Automações Cron</span>
            <span class="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]">
              {{ automations.length }}
            </span>
          </button>
          <button
            @click="activeTab = 'tasks'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center space-x-1.5"
            :class="activeTab === 'tasks' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
          >
            <span>Operações & Tarefas</span>
            <span class="px-1.5 py-0.2 rounded-full bg-slate-700 text-slate-300 text-[10px]">
              {{ tasks.length }}
            </span>
          </button>
        </div>

        <!-- Botões de Ação Rápida -->
        <div class="flex items-center space-x-2">
          <button
            @click="isChatDrawerOpen = true"
            class="px-3.5 py-2 text-xs font-bold rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 transition flex items-center space-x-1.5 shadow-md shadow-indigo-600/20"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Conversar com COO IA</span>
          </button>

          <button
            @click="handleToggleStatus"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl border transition"
            :class="business.status === 'active'
              ? 'bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20'"
          >
            {{ business.status === 'active' ? 'Pausar Venture' : 'Ativar Venture' }}
          </button>
        </div>
      </div>

      <!-- ABA 0: ROI & Auto-Otimização (Growth Engine) -->
      <div v-if="activeTab === 'growth'">
        <BusinessGrowthTab :business-id="businessId" :business="business" />
      </div>

      <!-- ABA 1: Business Model Canvas & Regras da Marca -->
      <div v-if="activeTab === 'canvas'" class="space-y-6">
        <!-- Canvas Grid (9 Blocos Executivos) -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
          <!-- Coluna 1: Parcerias Chave -->
          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1">
              <span>Parcerias Chave</span>
            </h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.key_partners || []" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <!-- Coluna 2: Atividades Chave + Recursos Chave -->
          <div class="space-y-4">
            <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Atividades Chave</h4>
              <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                <li v-for="(item, idx) in canvasData.key_activities || []" :key="idx">{{ item }}</li>
              </ul>
            </div>
            <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Recursos Chave</h4>
              <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                <li v-for="(item, idx) in canvasData.key_resources || []" :key="idx">{{ item }}</li>
              </ul>
            </div>
          </div>

          <!-- Coluna 3: Proposta de Valor (Destaque Central) -->
          <div class="p-5 rounded-xl bg-indigo-950/20 border border-indigo-500/30 space-y-3">
            <h4 class="text-xs font-bold text-indigo-300 uppercase tracking-wider">Proposta de Valor</h4>
            <ul class="text-xs text-slate-200 space-y-2 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.value_propositions || []" :key="idx" class="font-medium">{{ item }}</li>
            </ul>
          </div>

          <!-- Coluna 4: Relacionamento + Canais -->
          <div class="space-y-4">
            <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Relacionamento</h4>
              <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                <li v-for="(item, idx) in canvasData.customer_relationships || []" :key="idx">{{ item }}</li>
              </ul>
            </div>
            <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Canais</h4>
              <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
                <li v-for="(item, idx) in canvasData.channels || []" :key="idx">{{ item }}</li>
              </ul>
            </div>
          </div>

          <!-- Coluna 5: Segmentos de Clientes -->
          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Segmentos de Clientes</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.customer_segments || []" :key="idx">{{ item }}</li>
            </ul>
          </div>
        </div>

        <!-- Linha Inferior do Canvas: Custos & Receitas -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-rose-400 uppercase tracking-wider">Estrutura de Custos</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.cost_structure || []" :key="idx">{{ item }}</li>
            </ul>
          </div>
          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Fontes de Receita</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.revenue_streams || []" :key="idx">{{ item }}</li>
            </ul>
          </div>
        </div>

        <!-- Diretrizes da Marca -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 class="text-sm font-bold text-white uppercase tracking-wider">Diretrizes da Marca & Tom de Voz (Brand Rules)</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span class="font-bold text-slate-400 uppercase">Tom de Voz:</span>
              <p class="text-slate-200 mt-1 leading-relaxed">{{ brandRules.tone_of_voice }}</p>
            </div>
            <div class="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span class="font-bold text-slate-400 uppercase">Público-Alvo Prioritário:</span>
              <p class="text-slate-200 mt-1 leading-relaxed">{{ brandRules.target_audience }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ABA 2: Vitrine TikTok Shop -->
      <div v-if="activeTab === 'tiktok'" class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold text-white">Produtos Minerados na TikTok Shop</h3>
            <p class="text-xs text-slate-400 mt-0.5">
              O worker autônomo analisa comissão, velocidade de vendas e viralidade para selecionar os vencedores.
            </p>
          </div>
          <button
            @click="handleMineNow"
            :disabled="miningInProgress"
            class="px-4 py-2 text-xs font-bold rounded-xl text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 transition shadow-md shadow-emerald-400/20 flex items-center space-x-2"
          >
            <span v-if="miningInProgress" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
            <span>{{ miningInProgress ? 'Minerando...' : 'Minerar Produtos Agora' }}</span>
          </button>
        </div>

        <!-- Estado Vazio -->
        <div v-if="tiktokProducts.length === 0" class="p-12 text-center rounded-2xl bg-slate-900/60 border border-slate-800 text-slate-400 text-xs">
          Nenhum produto minerado ainda. Clique em "Minerar Produtos Agora" ou aguarde a automação periódica em background.
        </div>

        <!-- Grid de Produtos Minerados -->
        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div
            v-for="prod in tiktokProducts"
            :key="prod.id"
            class="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col justify-between hover:border-slate-700 transition"
          >
            <div class="p-5">
              <div class="flex items-start space-x-3">
                <img
                  v-if="prod.image_url"
                  :src="prod.image_url"
                  alt="Produto"
                  class="w-16 h-16 rounded-xl object-cover bg-slate-950 border border-slate-800 shrink-0"
                />
                <div class="flex-1 min-w-0">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">{{ prod.category || 'Geral' }}</span>
                  <h4 class="text-sm font-bold text-white truncate mt-0.5" :title="prod.title">{{ prod.title }}</h4>
                  <p class="text-xs text-emerald-400 font-semibold mt-1">
                    Comissão: {{ prod.commission_rate }}% (R$ {{ prod.commission_value || '0.00' }})
                  </p>
                </div>
              </div>

              <!-- Scores -->
              <div class="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-slate-800/80 text-center">
                <div class="p-2 rounded-lg bg-slate-950">
                  <span class="text-[10px] text-slate-500 uppercase font-bold block">Viral Score</span>
                  <span class="text-xs font-bold text-indigo-400">{{ prod.viral_score || 95 }}/100</span>
                </div>
                <div class="p-2 rounded-lg bg-slate-950">
                  <span class="text-[10px] text-slate-500 uppercase font-bold block">Velocidade</span>
                  <span class="text-xs font-bold text-emerald-400">{{ prod.velocity_score || 88 }}/100</span>
                </div>
                <div class="p-2 rounded-lg bg-slate-950">
                  <span class="text-[10px] text-slate-500 uppercase font-bold block">Overall</span>
                  <span class="text-xs font-bold text-amber-300">{{ prod.overall_score || 92 }}/100</span>
                </div>
              </div>
            </div>

            <!-- Footer do Produto -->
            <div class="p-4 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span class="text-slate-400">Preço: <strong class="text-slate-200">R$ {{ prod.price }}</strong></span>
              <a
                v-if="prod.affiliate_link || prod.product_url"
                :href="prod.affiliate_link || prod.product_url"
                target="_blank"
                class="text-indigo-400 hover:underline font-semibold"
              >
                Ver na Loja &rarr;
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- ABA 3: Automações Cron -->
      <div v-if="activeTab === 'automations'" class="space-y-4">
        <h3 class="text-base font-bold text-white">Regras de Automação & Agendamento Contínuo</h3>
        <div class="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900">
          <div class="grid grid-cols-12 bg-slate-950 p-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800">
            <div class="col-span-4">Tipo de Automação</div>
            <div class="col-span-3">Frequência (Cron)</div>
            <div class="col-span-3">Próxima Execução</div>
            <div class="col-span-2 text-right">Status / Toggle</div>
          </div>
          <div class="divide-y divide-slate-800/60 text-xs">
            <div
              v-for="auto in automations"
              :key="auto.id"
              class="grid grid-cols-12 p-4 items-center text-slate-300"
            >
              <div class="col-span-4 font-semibold text-white">
                <span>{{ auto.type_label || auto.type }}</span>
                <p class="text-[10px] text-slate-500 font-normal mt-0.5">{{ auto.description || 'Executa job autônomo do agente.' }}</p>
              </div>
              <div class="col-span-3 font-mono text-indigo-400">
                {{ auto.cron_expression }}
              </div>
              <div class="col-span-3 text-slate-400">
                {{ auto.next_run_at ? new Date(auto.next_run_at).toLocaleString() : 'Calculando...' }}
              </div>
              <div class="col-span-2 text-right">
                <button
                  @click="toggleAutomation(auto)"
                  class="px-3 py-1 rounded-full text-xs font-semibold border transition"
                  :class="(auto.is_enabled ?? auto.is_active)
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'"
                >
                  {{ (auto.is_enabled ?? auto.is_active) ? 'Ativa' : 'Pausada' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ABA 4: Operações & Tarefas -->
      <div v-if="activeTab === 'tasks'" class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-base font-bold text-white">Tarefas Vinculadas a Este Venture</h3>
          <router-link to="/tasks" class="text-xs text-emerald-400 hover:underline font-semibold">
            Abrir Quadro Kanban Geral &rarr;
          </router-link>
        </div>

        <div v-if="tasks.length === 0" class="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
          Nenhuma tarefa cadastrada para este negócio.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs"
          >
            <div>
              <div class="flex items-center space-x-2">
                <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">{{ task.status }}</span>
                <span class="text-slate-500">Executor: <strong class="text-indigo-400">{{ task.assignee }}</strong></span>
              </div>
              <h4 class="text-sm font-bold text-white mt-1">{{ task.title }}</h4>
            </div>
            <span class="text-slate-400 font-mono">{{ task.priority }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer de Chat Contextualizado neste Negócio -->
    <AgentChatDrawer
      :is-open="isChatDrawerOpen"
      :business-id="Number(businessId)"
      @close="isChatDrawerOpen = false"
    />
  </AppLayout>
</template>

