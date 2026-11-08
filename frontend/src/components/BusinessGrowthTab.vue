<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'

const props = defineProps({
  businessId: {
    type: [String, Number],
    required: true,
  },
  business: {
    type: Object,
    required: true,
  },
})

const swal = useSwal()
const loading = ref(true)
const metrics = ref({
  business: {},
  funnel: {
    total_views: 0,
    total_clicks: 0,
    total_leads: 0,
    abandoned_checkouts: 0,
    total_sales: 0,
    total_revenue: 0,
    conversion_rate: 0,
  },
  winning_assets: [],
  losing_assets: [],
  recent_conversions: [],
  learnings: [],
  optimization_cycles: [],
})

const activeWebhookDoc = ref('kiwify')
const optimizing = ref(false)

onMounted(async () => {
  await loadGrowthMetrics()
})

async function loadGrowthMetrics() {
  loading.value = true
  try {
    const res = await api.get(`/businesses/${props.businessId}/growth-metrics`)
    metrics.value = {
      ...metrics.value,
      ...res.data,
      learnings: res.data.learnings || [],
      optimization_cycles: res.data.optimization_cycles || [],
      winning_assets: res.data.winning_assets || [],
      recent_conversions: res.data.recent_conversions || [],
    }
  } catch (err) {
    swal.toast('Erro ao carregar métricas de ROI e Growth', 'error')
  } finally {
    loading.value = false
  }
}

const webhookUrl = computed(() => {
  const token = metrics.value.business?.webhook_secret_token || props.business?.webhook_secret_token || ''
  const origin = window.location.origin
  return `${origin}/api/webhooks/in/${token}`
})

function copyWebhookUrl() {
  navigator.clipboard.writeText(webhookUrl.value)
  swal.toast('URL de Webhook copiada para a área de transferência!', 'success')
}

function copyUtmLink(trackingCode) {
  const link = `https://seusite.com/produto?utm_content=${trackingCode}&utm_source=tiktok`
  navigator.clipboard.writeText(link)
  swal.toast(`Link parametrizado copiado: utm_content=${trackingCode}`, 'success')
}

async function handleOptimizeNow() {
  optimizing.value = true
  try {
    await api.post(`/businesses/${props.businessId}/optimize-growth`)
    swal.fire({
      icon: 'success',
      title: 'Ciclo OODA Disparado!',
      text: 'O Gemini 3.8 está analisando os ativos vencedores, diagnosticando gargalos de checkout e criando novas variações criativas.',
      confirmButtonText: 'Excelente',
      confirmButtonColor: '#10b981',
      background: '#0f172a',
      color: '#f8fafc',
    })
    setTimeout(loadGrowthMetrics, 3000)
  } catch (err) {
    swal.error('Falha ao disparar otimização', err.response?.data?.message || err.message)
  } finally {
    optimizing.value = false
  }
}

async function handleScaleAsset(asset) {
  try {
    const res = await api.post(`/businesses/${props.businessId}/optimize-growth`)
    swal.toast(`Comando enviado! O agente está gerando novas variações para ${asset.tracking_code}.`, 'success')
    setTimeout(loadGrowthMetrics, 3000)
  } catch (err) {
    swal.error('Erro ao solicitar escalação', err.message)
  }
}

async function openSimulateModal() {
  const assetsOptions = (metrics.value.winning_assets || [])
    .map(a => `<option value="${a.tracking_code}">${a.tracking_code} - ${a.title || a.type}</option>`)
    .join('')

  const { value: formValues } = await swal.fire({
    title: 'Simulador de Conversão / Webhook',
    html: `
      <div class="text-left space-y-3 text-xs text-slate-300">
        <p class="text-slate-400">Envie um webhook falso para testar o receptor, a atribuição ao criativo e o cálculo de ROI em tempo real.</p>
        <div>
          <label class="block font-semibold mb-1 text-slate-200">Plataforma</label>
          <select id="sim-platform" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100">
            <option value="kiwify">Kiwify</option>
            <option value="hotmart">Hotmart</option>
            <option value="stripe">Stripe</option>
            <option value="tiktok_shop">TikTok Shop</option>
            <option value="shopify">Shopify</option>
          </select>
        </div>
        <div>
          <label class="block font-semibold mb-1 text-slate-200">Tipo de Evento</label>
          <select id="sim-event" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100">
            <option value="sale_approved">Venda Aprovada (sale_approved)</option>
            <option value="pix_generated">PIX Gerado (Aguardando Pagamento)</option>
            <option value="checkout_abandoned">Carrinho Abandonado (checkout_abandoned)</option>
          </select>
        </div>
        <div>
          <label class="block font-semibold mb-1 text-slate-200">Valor Bruto (R$)</label>
          <input id="sim-amount" type="number" step="0.01" value="197.00" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100" />
        </div>
        <div>
          <label class="block font-semibold mb-1 text-slate-200">Atribuir ao Ativo (Tracking Code)</label>
          <select id="sim-tracking" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100">
            <option value="">Sem Atribuição (Orgânico Geral)</option>
            ${assetsOptions}
          </select>
        </div>
        <div>
          <label class="block font-semibold mb-1 text-slate-200">Nome do Comprador</label>
          <input id="sim-name" type="text" value="Rodrigo Mendes" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100" />
        </div>
      </div>
    `,
    focusConfirm: false,
    showCancelButton: true,
    confirmButtonText: 'Disparar Webhook Falso',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#475569',
    background: '#0b132b',
    color: '#f8fafc',
    preConfirm: () => {
      return {
        source_platform: document.getElementById('sim-platform').value,
        event_type: document.getElementById('sim-event').value,
        gross_amount: parseFloat(document.getElementById('sim-amount').value || '0'),
        tracking_code: document.getElementById('sim-tracking').value,
        customer_name: document.getElementById('sim-name').value,
        customer_email: 'lead_teste@exemplo.com',
        external_transaction_id: 'SIM-' + Date.now(),
      }
    },
  })

  if (formValues) {
    try {
      await api.post(`/businesses/${props.businessId}/webhooks/simulate`, formValues)
      swal.toast('Evento simulado processado com sucesso!', 'success')
      await loadGrowthMetrics()
    } catch (err) {
      swal.error('Erro na simulação', err.response?.data?.message || err.message)
    }
  }
}

function formatBRL(val) {
  return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function getArchetypeLabel(arch) {
  const map = {
    canal_dark: '🎬 Canal Dark (YouTube & TikTok)',
    dark_channel_automation: '🎬 Canal Dark (YouTube & TikTok)',
    affiliate_tiktok: 'Afiliados & TikTok Shop',
    infoproduct: 'Infoprodutos & Lançamentos',
    saas: 'SaaS & Assinaturas',
    ecommerce: 'E-commerce & Dropshipping',
  }
  return map[arch] || arch || 'Geral'
}
</script>

<template>
  <div class="space-y-6">
    <!-- Top KPI & Actions Bar -->
    <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-xl">
      <div>
        <div class="flex items-center space-x-2">
          <span class="px-2.5 py-1 text-[11px] font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {{ getArchetypeLabel(business.archetype || business.type) }}
          </span>
          <span class="text-xs text-slate-400">
            North Star: <strong class="text-slate-200 uppercase font-mono">{{ business.north_star_metric || 'commission_volume' }}</strong>
          </span>
        </div>
        <h2 class="text-xl font-black text-white mt-2 tracking-tight flex items-center space-x-2">
          <span>Sala de Guerra & Auto-Otimização de ROI</span>
          <span class="text-emerald-400 text-sm">● Operando</span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          O Gemini 3.8 cruza eventos reais de receita (webhooks) com cada ativo criativo para escalar o que dá lucro.
        </p>
      </div>

      <div class="flex items-center space-x-3 shrink-0">
        <button
          @click="openSimulateModal"
          class="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition flex items-center space-x-1.5 shadow-sm"
        >
          <span>🎯</span>
          <span>Simular Venda / Webhook</span>
        </button>

        <button
          @click="handleOptimizeNow"
          :disabled="optimizing"
          class="px-5 py-2.5 rounded-xl text-xs font-black text-slate-950 bg-gradient-to-r from-emerald-400 to-teal-300 hover:from-emerald-300 hover:to-teal-200 transition shadow-lg shadow-emerald-500/20 flex items-center space-x-2 disabled:opacity-50"
        >
          <span v-if="optimizing" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
          <span>⚡</span>
          <span>{{ optimizing ? 'Executando OODA...' : 'Rodar Ciclo OODA Agora' }}</span>
        </button>
      </div>
    </div>

    <!-- Funil Visual de Conversão -->
    <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-base font-bold text-white tracking-tight">Funil de Atribuição Universal</h3>
          <p class="text-xs text-slate-400">Performance acumulada da audiência até a conversão final em faturamento.</p>
        </div>
        <div class="text-right">
          <span class="text-xs text-slate-400">Receita Total Rastreada</span>
          <div class="text-xl font-black text-emerald-400">{{ formatBRL(metrics.funnel.total_revenue) }}</div>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
        <!-- 1. Visualizações -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">1. Atração (Views)</span>
          <div class="text-2xl font-black text-white mt-1">{{ metrics.funnel.total_views.toLocaleString('pt-BR') }}</div>
          <p class="text-[10px] text-slate-400 mt-1">Topo de Funil</p>
        </div>

        <!-- 2. Cliques -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span class="text-[10px] font-bold uppercase tracking-wider text-indigo-400">2. Cliques / Tráfego</span>
          <div class="text-2xl font-black text-indigo-300 mt-1">{{ metrics.funnel.total_clicks.toLocaleString('pt-BR') }}</div>
          <p class="text-[10px] text-slate-400 mt-1">
            CTR: {{ metrics.funnel.total_views > 0 ? ((metrics.funnel.total_clicks / metrics.funnel.total_views) * 100).toFixed(1) : 0 }}%
          </p>
        </div>

        <!-- 3. Leads -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span class="text-[10px] font-bold uppercase tracking-wider text-teal-400">3. Leads / Cadastros</span>
          <div class="text-2xl font-black text-teal-300 mt-1">{{ metrics.funnel.total_leads.toLocaleString('pt-BR') }}</div>
          <p class="text-[10px] text-slate-400 mt-1">Meio de Funil</p>
        </div>

        <!-- 4. Abandono de Checkout / PIX -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-amber-500/20 bg-amber-500/5">
          <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400">4. Checkouts / PIX</span>
          <div class="text-2xl font-black text-amber-300 mt-1">{{ metrics.funnel.abandoned_checkouts }}</div>
          <p class="text-[10px] text-amber-400/80 mt-1">Recuperação IA Ativa</p>
        </div>

        <!-- 5. Vendas Aprovadas -->
        <div class="p-4 rounded-xl bg-slate-950/60 border border-emerald-500/30 bg-emerald-500/5 col-span-2 md:col-span-1">
          <span class="text-[10px] font-bold uppercase tracking-wider text-emerald-400">5. Vendas Concluídas</span>
          <div class="text-2xl font-black text-emerald-300 mt-1">{{ metrics.funnel.total_sales }}</div>
          <p class="text-[10px] text-emerald-400/80 mt-1">
            CVR: {{ metrics.funnel.conversion_rate }}%
          </p>
        </div>
      </div>
    </div>

    <!-- Leaderboard de Criativos & Ativos Vencedores -->
    <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-base font-bold text-white tracking-tight">Creative Leaderboard (Ranking de ROI)</h3>
          <p class="text-xs text-slate-400">Identificação automática dos ativos com maior retorno para alavancagem.</p>
        </div>
        <span class="text-xs text-slate-500 font-mono">{{ metrics.winning_assets?.length || 0 }} ativos rankeados</span>
      </div>

      <div v-if="!metrics.winning_assets?.length" class="p-8 text-center rounded-xl bg-slate-950/40 border border-slate-800 text-xs text-slate-400">
        Nenhum ativo com conversão registrada ainda. Simule uma venda ou aguarde webhooks externos com o código de rastreio (ex: <code>AST-XXXX</code>).
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="asset in metrics.winning_assets"
          :key="asset.id"
          class="p-4 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
        >
          <div class="flex items-start space-x-3">
            <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center font-mono font-bold text-xs text-indigo-400 shrink-0">
              #{{ asset.id }}
            </div>
            <div>
              <div class="flex items-center space-x-2">
                <span class="px-2 py-0.5 rounded font-mono font-bold text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {{ asset.tracking_code }}
                </span>
                <span class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {{ asset.angle_category || 'dor_direta' }}
                </span>
                <span class="text-xs text-slate-500">
                  {{ asset.funnel_stage || 'tof_attraction' }}
                </span>
              </div>
              <h4 class="text-sm font-bold text-white mt-1">{{ asset.title || 'Roteiro de Conversão' }}</h4>
              <p class="text-xs text-slate-400 mt-0.5 line-clamp-1">{{ asset.body }}</p>
            </div>
          </div>

          <!-- Métricas e Ações do Ativo -->
          <div class="flex flex-wrap items-center gap-4 shrink-0 justify-between md:justify-end">
            <div class="text-right">
              <span class="text-[10px] text-slate-400 block">Vendas / Faturamento</span>
              <span class="text-xs font-bold text-slate-200">{{ asset.total_sales_count }} vendas</span>
              <span class="text-xs font-black text-emerald-400 ml-1.5">{{ formatBRL(asset.total_revenue_brl) }}</span>
            </div>

            <!-- ROI Score Pill -->
            <div class="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-center min-w-[70px]">
              <span class="text-[9px] text-slate-400 block uppercase font-bold">ROI Score</span>
              <span
                class="text-sm font-black"
                :class="asset.roi_score >= 60 ? 'text-emerald-400' : asset.roi_score >= 30 ? 'text-amber-400' : 'text-slate-400'"
              >
                {{ asset.roi_score }}/100
              </span>
            </div>

            <div class="flex items-center space-x-2">
              <button
                @click="copyUtmLink(asset.tracking_code)"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
                title="Copiar link com parâmetro UTM"
              >
                Copiar UTM
              </button>

              <button
                @click="handleScaleAsset(asset)"
                class="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/20 transition flex items-center space-x-1"
              >
                <span>⚡</span>
                <span>Mandar IA Escalar</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Webhook & Postback Center -->
    <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div>
          <h3 class="text-base font-bold text-white tracking-tight">Centro de Webhooks & Postback de Receita</h3>
          <p class="text-xs text-slate-400">Conecte sua plataforma de vendas para alimentar a auto-otimização 24/7.</p>
        </div>
        <div class="flex items-center space-x-2">
          <button
            @click="copyWebhookUrl"
            class="px-4 py-2 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 transition flex items-center space-x-1.5 shadow-md shadow-emerald-400/20"
          >
            <span>📋</span>
            <span>Copiar Endpoint de Webhook</span>
          </button>
        </div>
      </div>

      <!-- Caixa da URL -->
      <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-400 flex items-center justify-between break-all">
        <span>{{ webhookUrl }}</span>
      </div>

      <!-- Tabs de Plataformas -->
      <div class="pt-2">
        <div class="flex items-center space-x-2 border-b border-slate-800 pb-2">
          <button
            v-for="plat in ['kiwify', 'hotmart', 'stripe', 'shopify', 'tiktok_shop', 'custom']"
            :key="plat"
            @click="activeWebhookDoc = plat"
            class="px-3 py-1 text-xs font-semibold rounded-lg capitalize transition"
            :class="activeWebhookDoc === plat ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'"
          >
            {{ plat.replace('_', ' ') }}
          </button>
        </div>

        <div class="mt-3 text-xs text-slate-300 leading-relaxed">
          <div v-if="activeWebhookDoc === 'kiwify'">
            Cole esta URL em <strong>Kiwify &rarr; Apps &rarr; Webhooks</strong>. O sistema processa automaticamente eventos de venda aprovada, PIX pendente e atribui ao criativo através dos parâmetros <code>src</code>, <code>sck</code> ou <code>utm_content</code>.
          </div>
          <div v-else-if="activeWebhookDoc === 'hotmart'">
            Cole esta URL no <strong>Hotmart Webhook (Postback)</strong>. O sistema captura eventos <code>PURCHASE_APPROVED</code> e rastreia o criativo pelo campo <code>tracking.source</code> ou <code>sck</code>.
          </div>
          <div v-else-if="activeWebhookDoc === 'stripe'">
            Cole em <strong>Stripe Dashboard &rarr; Webhooks</strong> para eventos <code>checkout.session.completed</code>. O sistema extrai o tracking de <code>metadata.tracking_code</code> ou <code>client_reference_id</code>.
          </div>
          <div v-else-if="activeWebhookDoc === 'shopify'">
            Configure no <strong>Shopify Admin &rarr; Notificações &rarr; Webhooks</strong> para <code>orders/paid</code>. O sistema localiza o tracking code em <code>note_attributes</code> ou <code>landing_site_ref</code>.
          </div>
          <div v-else-if="activeWebhookDoc === 'tiktok_shop'">
            Conecte o App do <strong>TikTok Shop Partner / Webhook</strong>. O sistema processa notificações de pedidos e calcula comissões de afiliados automaticamente.
          </div>
          <div v-else>
            Envie qualquer payload JSON contendo <code>event_type</code>, <code>gross_amount</code> e <code>tracking_code</code> (ex: <code>AST-XXXX</code>).
          </div>
        </div>
      </div>
    </div>

    <!-- Grid de Sala de Inteligência: Aprendizados do Agente e Conversões Recentes -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Aprendizados do Agente (agent_learnings) -->
      <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <h3 class="text-base font-bold text-white flex items-center space-x-2">
          <span>🧠 Memória Contínua & Aprendizados do Agente</span>
        </h3>
        <p class="text-xs text-slate-400">Teses validadas pelo Gemini 3.8 com base nos testes A/B e conversões reais.</p>

        <div v-if="metrics.learnings.length === 0" class="p-6 text-center rounded-xl bg-slate-950/40 text-xs text-slate-500">
          Nenhum aprendizado formulado ainda. O agente registra teses automaticamente a cada ciclo OODA.
        </div>

        <div v-else class="space-y-2.5">
          <div
            v-for="learning in metrics.learnings"
            :key="learning.id"
            class="p-3.5 rounded-xl bg-slate-950 border border-slate-800"
          >
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-indigo-300">{{ learning.topic }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                {{ learning.confidence_score }}% Confiança
              </span>
            </div>
            <p class="text-xs text-slate-300 mt-1.5 leading-relaxed">{{ learning.insight }}</p>
          </div>
        </div>
      </div>

      <!-- Conversões Recentes do Ledger -->
      <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <h3 class="text-base font-bold text-white flex items-center space-x-2">
          <span>🧾 Ledger de Eventos de Conversão</span>
        </h3>
        <p class="text-xs text-slate-400">Últimos disparos recebidos e validados pelo sistema.</p>

        <div v-if="metrics.recent_conversions.length === 0" class="p-6 text-center rounded-xl bg-slate-950/40 text-xs text-slate-500">
          Nenhum evento registrado no Ledger até o momento.
        </div>

        <div v-else class="space-y-2 max-h-[360px] overflow-y-auto pr-1">
          <div
            v-for="ev in metrics.recent_conversions"
            :key="ev.id"
            class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
          >
            <div>
              <div class="flex items-center space-x-2">
                <span class="font-bold uppercase text-slate-300">{{ ev.source_platform }}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                  {{ ev.event_type }}
                </span>
                <span v-if="ev.content_asset" class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300">
                  {{ ev.content_asset.tracking_code }}
                </span>
              </div>
              <p class="text-[11px] text-slate-400 mt-1">
                {{ ev.customer_metadata?.name || ev.customer_metadata?.email || 'Lead' }} · {{ new Date(ev.occurred_at).toLocaleTimeString('pt-BR') }}
              </p>
            </div>

            <div class="text-right">
              <span class="font-bold text-emerald-400">{{ formatBRL(ev.gross_amount) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

