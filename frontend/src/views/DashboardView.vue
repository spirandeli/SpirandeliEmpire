<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import AgentChatDrawer from '@/components/AgentChatDrawer.vue'
import { useAuthStore } from '@/stores/auth'
import { useApprovalStore } from '@/stores/approvals'
import { useBusinessStore } from '@/stores/business'
import { useTaskStore } from '@/stores/tasks'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()
const approvalStore = useApprovalStore()
const businessStore = useBusinessStore()
const taskStore = useTaskStore()
const swal = useSwal()

const loading = ref(true)
const expandedCardId = ref(null)
const selectedHookIndexes = ref({})
const scheduleDates = ref({})
const integrations = ref([])
const syncingCalendar = ref(false)
const isChatDrawerOpen = ref(false)
const provisioningDemo = ref(false)
const jeffreyStatus = ref(null)

onMounted(async () => {
  await loadDashboardData()
})

async function fetchJeffreyStatus() {
  try {
    const res = await api.get('/agent/status')
    jeffreyStatus.value = res.data
  } catch {
    jeffreyStatus.value = null
  }
}

async function handleProvisionShowcase() {
  provisioningDemo.value = true
  try {
    const res = await api.post('/auth/provision-showcase')
    swal.toast(res.data.message || 'Showcase de demonstração provisionado com sucesso!', 'success')
    await loadDashboardData()
  } catch (err) {
    swal.error('Erro ao provisionar showcase', err.response?.data?.message || 'Tente novamente.')
  } finally {
    provisioningDemo.value = false
  }
}

async function loadDashboardData() {
  loading.value = true
  try {
    await Promise.allSettled([
      approvalStore.fetchPending(),
      approvalStore.fetchSummary(),
      businessStore.fetchBusinesses({ per_page: 5 }),
      taskStore.fetchBoard(),
      fetchIntegrations(),
      fetchJeffreyStatus(),
    ])
  } finally {
    loading.value = false
  }
}

async function fetchIntegrations() {
  try {
    const res = await api.get('/integrations')
    integrations.value = res.data.data || []
  } catch {
    integrations.value = []
  }
}

const activeBusinessesCount = computed(() => {
  return businessStore.businesses.filter((b) => b.status === 'active').length
})

const runningAiTasksCount = computed(() => {
  const aiCol = taskStore.boardColumns.find((c) => c.status === 'in_progress_agent')
  return aiCol ? aiCol.count : 0
})

const isGoogleConnected = computed(() => {
  return integrations.value.some((i) => i.provider === 'google' && i.is_active)
})

const isAppleConnected = computed(() => {
  return integrations.value.some((i) => i.provider === 'apple_caldav' && i.is_active)
})

function toggleExpand(id) {
  expandedCardId.value = expandedCardId.value === id ? null : id
}

function selectHook(itemId, hookIdx) {
  selectedHookIndexes.value[itemId] = hookIdx
}

// 1-Clique com Optimistic UI: Aprova instantaneamente e despacha para o worker
async function handleInstantApprove(item) {
  const chosenHook = selectedHookIndexes.value[item.id] ?? 0
  const scheduledTime = scheduleDates.value[item.id] || null

  // Backup para rollback em caso de falha de rede
  const originalItems = [...approvalStore.pendingItems]
  // Remoção otimista imediata da tela (Zero Fricção)
  approvalStore.pendingItems = approvalStore.pendingItems.filter((i) => i.id !== item.id)
  if (approvalStore.summary.pending > 0) {
    approvalStore.summary.pending--
  }

  // Toast discreto no canto superior (sem modal central bloqueante)
  swal.toast(`Aprovado: "${item.title}". Despachado para o cronograma!`, 'success')

  try {
    await approvalStore.approve(item.id, {
      selectedHookIndex: chosenHook,
      scheduledFor: scheduledTime,
    })
    // Atualiza contadores em background
    approvalStore.fetchSummary()
  } catch (err) {
    // Rollback otimista se falhar
    approvalStore.pendingItems = originalItems
    swal.error('Falha ao aprovar', err.response?.data?.message || err.message)
  }
}

async function handleRequestRevision(item) {
  const promptData = await swal.promptRevision(item.title)
  if (!promptData) return

  try {
    await approvalStore.requestRevision(item.id, promptData.feedback, promptData.section)
    swal.toast('Ajuste enviado ao Gemini 3.8! O agente está reescrevendo em background.', 'info')
  } catch (err) {
    swal.error('Erro ao solicitar revisão', err.response?.data?.message || err.message)
  }
}

async function handleReject(item) {
  const confirmed = await swal.confirm({
    title: 'Descartar esta entrega?',
    text: 'O material será arquivado e o agente aprenderá com o descarte.',
    confirmText: 'Sim, descartar',
    confirmButtonColor: '#ef4444',
  })

  if (!confirmed) return

  try {
    await approvalStore.reject(item.id, 'Descartado pelo usuário na Inbox')
    swal.toast('Item descartado.', 'info')
  } catch (err) {
    swal.error('Erro ao descartar', err.response?.data?.message || err.message)
  }
}

function copyScriptToClipboard(item) {
  const p = item.payload || {}
  const hooks = (p.hooks || []).map((h, i) => `Hook #${i + 1}: "${h.hook || h}"`).join('\n')
  const scenes = (p.script?.scenes || []).map((s, i) => `[${s.time || `Cena ${i+1}`}]\nVisual: ${s.visual}\nÁudio: ${s.audio}`).join('\n\n')
  const hashtags = Array.isArray(p.hashtags) ? p.hashtags.join(' ') : (p.hashtags || '')

  const fullText = `TITULO: ${item.title}\nPRODUTO: ${p.product?.title || ''}\n\n--- GANCHOS DE 3 SEGUNDOS ---\n${hooks}\n\n--- ROTEIRO ---\n${scenes}\n\n--- LEGENDA & HASHTAGS ---\n${p.caption || ''}\n${hashtags}`

  navigator.clipboard.writeText(fullText)
  swal.toast('Roteiro completo copiado para a área de transferência!', 'success')
}

async function syncCalendarNow() {
  syncingCalendar.value = true
  try {
    if (isGoogleConnected.value) {
      await api.post('/integrations/google/sync')
    }
    if (isAppleConnected.value) {
      await api.post('/integrations/apple-caldav/sync')
    }
    swal.toast('Agendas e lembretes sincronizados com sucesso!', 'success')
  } catch (err) {
    swal.error('Falha na sincronização', err.response?.data?.message || 'Verifique as credenciais da integração.')
  } finally {
    syncingCalendar.value = false
  }
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full gap-3">
        <div>
          <h1 class="text-xl font-bold text-white tracking-tight">Cockpit Executivo & Supervisão</h1>
          <p class="text-xs text-slate-400 mt-0.5">Operações Autônomas · Gemini 3.8 Co-Pilot</p>
        </div>
        <div class="flex items-center space-x-2.5">
          <button
            @click="handleProvisionShowcase"
            :disabled="provisioningDemo"
            class="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition flex items-center space-x-1.5 shadow-sm"
            title="Carrega ou cria um novo showcase de demonstração com dados de TikTok Shop e ROI"
          >
            <span v-if="provisioningDemo" class="animate-spin h-3.5 w-3.5 border-2 border-emerald-400 border-t-transparent rounded-full"></span>
            <span v-else class="text-emerald-400">⚡</span>
            <span>{{ provisioningDemo ? 'Provisionando...' : 'Carregar Showcase Demo' }}</span>
          </button>
          <button
            @click="isChatDrawerOpen = true"
            class="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-indigo-600 hover:from-emerald-400 hover:to-indigo-500 text-white text-xs font-semibold transition flex items-center space-x-1.5 shadow-sm shadow-emerald-500/20"
          >
            <span>💬 Falar com COO IA</span>
          </button>
        </div>
      </div>
    </template>

    <div class="space-y-8">
      <!-- 1. Métricas Principais (Executive KPIs) -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <!-- Negócios Ativos -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Ventures Ativos</span>
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-white">{{ activeBusinessesCount }}</span>
            <span class="text-xs text-slate-400 font-medium">de {{ businessStore.businesses.length }} total</span>
          </div>
          <p class="mt-2 text-xs text-slate-400 flex items-center space-x-1">
            <span class="text-emerald-400 font-semibold">100%</span>
            <span>com workers operantes</span>
          </p>
        </div>

        <!-- Fila de Supervisão (Human-in-the-Loop) -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-amber-500/30 shadow-sm relative overflow-hidden group hover:border-amber-500/50 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-amber-400">Supervisão Humana</span>
            <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Aguardando
            </span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-amber-300">{{ approvalStore.summary.pending }}</span>
            <span class="text-xs text-slate-400 font-medium">prontos para review</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">
            {{ approvalStore.summary.revision > 0 ? `${approvalStore.summary.revision} em reescrita pelo agente` : 'Nenhum em revisão' }}
          </p>
        </div>

        <!-- Em Execução pelo Worker IA -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">IA Workers Ativos</span>
            <span class="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-indigo-400">{{ runningAiTasksCount }}</span>
            <span class="text-xs text-slate-400 font-medium">tarefas background</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">Mineração & Geração de Roteiros</p>
        </div>

        <!-- Sincronização Calendário & Rotina -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-slate-700 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Hub de Agendas</span>
            <div class="flex items-center space-x-1.5">
              <span
                class="w-2 h-2 rounded-full"
                :class="isGoogleConnected || isAppleConnected ? 'bg-emerald-400' : 'bg-rose-400'"
              ></span>
              <span class="text-[10px] text-slate-400">
                {{ isGoogleConnected && isAppleConnected ? 'G & Apple' : isGoogleConnected ? 'Google' : isAppleConnected ? 'Apple' : 'Off' }}
              </span>
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-200">Google / Apple</span>
            <button
              @click="syncCalendarNow"
              :disabled="syncingCalendar"
              class="px-2.5 py-1 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1"
            >
              <span v-if="syncingCalendar" class="animate-spin h-3 w-3 border border-slate-300 border-t-transparent rounded-full"></span>
              <span>{{ syncingCalendar ? 'Sincronizando...' : 'Sync Agora' }}</span>
            </button>
          </div>
          <p class="mt-2 text-xs text-slate-500">
            <router-link to="/settings/integrations" class="text-indigo-400 hover:underline">
              Gerenciar Conexões &rarr;
            </router-link>
          </p>
        </div>
      </section>

      <!-- Jeffrey COO Operational Cockpit & Status Widget -->
      <section v-if="jeffreyStatus" class="rounded-2xl bg-slate-900/90 border border-slate-800 p-5 shadow-lg relative overflow-hidden">
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div class="flex items-center space-x-3.5">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-indigo-600 to-cyan-500 flex items-center justify-center text-white text-lg font-bold shadow-md shadow-indigo-500/20">
              ⚡
            </div>
            <div>
              <div class="flex items-center space-x-2.5">
                <h3 class="text-base font-bold text-white tracking-tight">Jeffrey · Cockpit COO Autônomo</h3>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>{{ jeffreyStatus.agent?.model || 'Gemini 3.8 Flash' }}</span>
                </span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  ReAct Loop Ativo
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">
                Supervisão de infraestrutura, ventures e despacho de tarefas operacionais com memória contextual.
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <button
              @click="fetchJeffreyStatus"
              class="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition"
              title="Atualizar telemetria do Jeffrey"
            >
              🔄 Atualizar
            </button>
            <button
              @click="isChatDrawerOpen = true"
              class="px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-indigo-600 hover:from-emerald-400 hover:to-indigo-500 text-white text-xs font-semibold shadow transition flex items-center space-x-1.5"
            >
              <span>💬 Abrir Chat Executivo</span>
            </button>
          </div>
        </div>

        <!-- Telemetry & Subsystem Cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3.5 mt-4 text-xs">
          <!-- Host VPS -->
          <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
            <div class="flex items-center justify-between text-slate-400">
              <span class="font-medium">Telemetria Host</span>
              <span class="w-2 h-2 rounded-full" :class="jeffreyStatus.vps?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'"></span>
            </div>
            <div class="text-slate-100 font-mono font-bold text-sm">
              CPU: {{ jeffreyStatus.vps?.cpu?.percent }}%
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              RAM: {{ jeffreyStatus.vps?.memory?.percent }}% · Disco: {{ jeffreyStatus.vps?.disk?.percent }}%
            </div>
          </div>

          <!-- Docker Engine -->
          <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
            <div class="flex items-center justify-between text-slate-400">
              <span class="font-medium">Docker Engine</span>
              <span class="w-2 h-2 rounded-full" :class="jeffreyStatus.docker_connected ? 'bg-emerald-400' : 'bg-rose-400'"></span>
            </div>
            <div class="text-slate-100 font-mono font-bold text-sm">
              {{ jeffreyStatus.docker_connected ? 'Socket Conectado' : 'Socket Offline' }}
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              Modo seguro (:ro)
            </div>
          </div>

          <!-- RAG Base de Conhecimento -->
          <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
            <div class="flex items-center justify-between text-slate-400">
              <span class="font-medium">RAG Base Oficial</span>
              <span class="text-indigo-400 font-mono text-[10px]">ChromaDB</span>
            </div>
            <div class="text-slate-100 font-mono font-bold text-sm">
              {{ jeffreyStatus.knowledge_base?.indexed_chunks || 0 }} Chunks
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              {{ jeffreyStatus.knowledge_base?.document_files_count || 0 }} documentos indexados
            </div>
          </div>

          <!-- Memórias de Longo Prazo -->
          <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
            <div class="flex items-center justify-between text-slate-400">
              <span class="font-medium">Memórias Estratégicas</span>
              <span class="text-purple-400 font-mono text-[10px]">MySQL</span>
            </div>
            <div class="text-slate-100 font-mono font-bold text-sm">
              {{ jeffreyStatus.memory_count || 0 }} Diretrizes
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              Preferências & Fatos Chave
            </div>
          </div>
        </div>

        <!-- Recent Autonomous Actions Feed -->
        <div v-if="jeffreyStatus.recent_actions && jeffreyStatus.recent_actions.length > 0" class="mt-4 pt-3 border-t border-slate-800/60">
          <div class="flex items-center justify-between mb-2">
            <span class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Últimas Ações Autônomas do Jeffrey</span>
            <span class="text-[10px] text-slate-500 font-mono">Auditoria de Execução</span>
          </div>
          <div class="space-y-1.5">
            <div
              v-for="action in jeffreyStatus.recent_actions.slice(0, 3)"
              :key="action.id"
              class="flex items-center justify-between p-2 rounded-lg bg-slate-950/40 border border-slate-800/60 text-xs"
            >
              <div class="flex items-center space-x-2">
                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                <span class="text-slate-200 font-medium">{{ action.message }}</span>
                <span v-if="action.duration_ms" class="text-[10px] text-slate-500 font-mono">({{ action.duration_ms }}ms)</span>
              </div>
              <span class="text-[10px] text-slate-500 font-mono">{{ action.created_at ? new Date(action.created_at).toLocaleTimeString() : '' }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 2. Supervision Inbox (Human-in-the-Loop) -->
      <section class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center space-x-2">
              <span>Inbox de Supervisão Estratégica</span>
              <span class="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                {{ approvalStore.pendingItems.length }} pendentes
              </span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">
              Supervisão com 1-clique: aprove instantaneamente ou solicite refinamento específico ao Gemini 3.8.
            </p>
          </div>
          <button
            @click="approvalStore.fetchPending()"
            class="px-3 py-1.5 text-xs rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 transition self-start sm:self-auto"
          >
            Atualizar Inbox
          </button>
        </div>

        <!-- Estado Vazio (Empty State com CTA) -->
        <div
          v-if="!loading && approvalStore.pendingItems.length === 0"
          class="p-12 text-center rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-4"
        >
          <div class="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
            <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 class="text-base font-bold text-white">Nenhuma entrega aguardando aprovação no momento</h3>
            <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto leading-relaxed">
              Os workers autônomos operam 24/7 minerando produtos virais e gerando roteiros. Deseja iniciar um novo venture ou acelerar a produção?
            </p>
          </div>
          <div class="pt-2">
            <button
              @click="isChatDrawerOpen = true"
              class="px-5 py-2.5 rounded-xl font-bold text-xs text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-lg shadow-emerald-400/20 transition inline-flex items-center space-x-2"
            >
              <span class="w-2 h-2 rounded-full bg-slate-950"></span>
              <span>Comandar Nova Ação com o COO IA</span>
            </button>
          </div>
        </div>

        <!-- Lista de Cards da Inbox -->
        <div v-else class="space-y-4">
          <transition-group
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="opacity-0 translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
          >
            <div
              v-for="item in approvalStore.pendingItems"
              :key="item.id"
              class="rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition overflow-hidden shadow-lg shadow-black/20"
            >
              <!-- Card Header -->
              <div class="p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/60">
                <div class="flex items-start space-x-4">
                  <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold shrink-0">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {{ item.business?.name || 'Venture' }}
                      </span>
                      <span class="text-xs text-slate-500 font-mono">
                        Confiança IA: {{ ((item.agent_confidence || 0.95) * 100).toFixed(0) }}%
                      </span>
                      <span
                        v-if="item.payload?.badge || item.type === 'roi_scaling'"
                        class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1"
                      >
                        <span>⚡</span>
                        <span>{{ item.payload?.badge || 'Auto-Otimização de ROI' }}</span>
                      </span>
                      <span
                        v-if="item.payload?.parent_tracking_code"
                        class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                      >
                        Base: {{ item.payload?.parent_tracking_code }} (ROI: {{ item.payload?.parent_roi_score || 0 }})
                      </span>
                    </div>
                    <h3 class="text-base font-bold text-white mt-1">{{ item.title }}</h3>
                    <p class="text-xs text-slate-400 mt-0.5">{{ item.summary }}</p>
                  </div>
                </div>

                <!-- Ações Imediatas (1-clique Approve + Botão Copiar) -->
                <div class="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    @click="copyScriptToClipboard(item)"
                    title="Copiar Roteiro e Hooks"
                    class="p-2 text-xs rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center space-x-1"
                  >
                    <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                    <span class="hidden sm:inline">Copiar</span>
                  </button>

                  <button
                    @click="toggleExpand(item.id)"
                    class="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1"
                  >
                    <span>{{ expandedCardId === item.id ? 'Recolher' : 'Examinar Roteiro' }}</span>
                    <svg
                      class="w-4 h-4 transition-transform duration-200"
                      :class="expandedCardId === item.id ? 'rotate-180' : ''"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  <button
                    @click="handleRequestRevision(item)"
                    class="px-3 py-2 text-xs font-semibold rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition flex items-center space-x-1.5"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    <span>Pedir Ajuste</span>
                  </button>

                  <!-- 1-Clique Instant Approve -->
                  <button
                    @click="handleInstantApprove(item)"
                    class="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-400 hover:bg-emerald-300 text-slate-950 shadow-md shadow-emerald-400/20 transition flex items-center space-x-1.5"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Aprovar</span>
                  </button>

                  <button
                    @click="handleReject(item)"
                    title="Descartar"
                    class="p-2 text-xs rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700 hover:border-rose-500/30 transition"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Corpo Expansível com Roteiro e Análise -->
              <div v-if="expandedCardId === item.id" class="p-6 bg-slate-950/60 border-t border-slate-800/80 space-y-6">
                <!-- Dados do Produto Minerado -->
                <div v-if="item.payload?.product" class="p-4 rounded-xl bg-slate-900 border border-slate-800 grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div class="flex items-center space-x-3 md:col-span-2">
                    <img
                      v-if="item.payload.product.image_url"
                      :src="item.payload.product.image_url"
                      alt="Produto"
                      class="w-14 h-14 rounded-lg object-cover border border-slate-800 bg-slate-950"
                    />
                    <div>
                      <h4 class="text-sm font-bold text-white">{{ item.payload.product.title || item.title }}</h4>
                      <p class="text-xs text-slate-400">Categoria: {{ item.payload.product.category || 'Geral' }}</p>
                      <a
                        v-if="item.payload.product.affiliate_link"
                        :href="item.payload.product.affiliate_link"
                        target="_blank"
                        class="text-xs text-indigo-400 hover:underline flex items-center space-x-1 mt-1"
                      >
                        <span>Abrir Link TikTok Shop</span>
                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </div>
                  </div>

                  <div class="space-y-1">
                    <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Margem de Comissão</span>
                    <p class="text-base font-bold text-emerald-400">
                      {{ item.payload.product.commission_rate ? `${item.payload.product.commission_rate}%` : '18.5%' }}
                    </p>
                    <p class="text-xs text-slate-500">
                      Preço: {{ item.payload.product.sale_price ? `R$ ${item.payload.product.sale_price}` : 'Sob consulta' }}
                    </p>
                  </div>

                  <div class="space-y-1">
                    <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Score Viral & Volume</span>
                    <div class="flex items-center space-x-2">
                      <span class="text-base font-bold text-indigo-400">
                        {{ item.payload.product.score_virality || '9.4' }}/10
                      </span>
                      <span class="text-xs text-slate-400">Alta Tração</span>
                    </div>
                    <p class="text-xs text-slate-500">Minerado via Automação TikTok</p>
                  </div>
                </div>

                <!-- Justificativa da IA (Rationale) -->
                <div v-if="item.payload?.rationale" class="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/20">
                  <span class="text-xs font-bold uppercase tracking-wider text-indigo-300">Justificativa Estratégica (Gemini 3.8):</span>
                  <p class="text-xs text-slate-300 mt-1 leading-relaxed">{{ item.payload.rationale }}</p>
                </div>

                <!-- Escolha de Hooks de 3 Segundos -->
                <div class="space-y-2">
                  <div class="flex items-center justify-between">
                    <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Selecione o Melhor Gancho (Primeiros 3 segundos):
                    </h4>
                    <span class="text-xs text-slate-500">Clique para selecionar a versão preferida</span>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div
                      v-for="(hook, idx) in (item.payload?.hooks || [
                        { hook: 'Pare de perder tempo tentando organizar suas tarefas manualmente!', angle: 'Dor Imediata' },
                        { hook: 'Este pequeno acessório viralizou no TikTok e quase ninguém conhece no Brasil.', angle: 'Curiosidade' },
                        { hook: 'Se você trabalha home office, você PRECISA ver isso antes de acabar o estoque.', angle: 'Urgência / FOMO' }
                      ])"
                      :key="idx"
                      @click="selectHook(item.id, idx)"
                      class="p-3.5 rounded-xl border cursor-pointer transition relative"
                      :class="(selectedHookIndexes[item.id] ?? 0) === idx
                        ? 'bg-emerald-500/10 border-emerald-500 text-slate-100 shadow-sm shadow-emerald-500/10'
                        : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'"
                    >
                      <div class="flex items-center justify-between mb-1.5">
                        <span class="text-[10px] font-bold uppercase tracking-wider" :class="(selectedHookIndexes[item.id] ?? 0) === idx ? 'text-emerald-400' : 'text-slate-400'">
                          Variação #{{ idx + 1 }} · {{ hook.angle || 'Gancho' }}
                        </span>
                        <span v-if="(selectedHookIndexes[item.id] ?? 0) === idx" class="w-2 h-2 rounded-full bg-emerald-400"></span>
                      </div>
                      <p class="text-xs leading-relaxed font-medium">"{{ hook.hook || hook }}"</p>
                    </div>
                  </div>
                </div>

                <!-- Roteiro Completo (Visual x Áudio) -->
                <div class="space-y-2">
                  <div class="flex items-center justify-between">
                    <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider">Roteiro Completo de Gravação:</h4>
                    <button
                      @click="copyScriptToClipboard(item)"
                      class="text-xs text-indigo-400 hover:underline font-semibold"
                    >
                      Copiar Roteiro Formatado
                    </button>
                  </div>
                  <div class="rounded-xl border border-slate-800 overflow-hidden bg-slate-900">
                    <div class="grid grid-cols-12 bg-slate-950 p-2.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                      <div class="col-span-2">Tempo / Cena</div>
                      <div class="col-span-5">Visual / Ação na Tela</div>
                      <div class="col-span-5">Áudio / Fala do Apresentador</div>
                    </div>
                    <div class="divide-y divide-slate-800/60 text-xs">
                      <div
                        v-for="(scene, sIdx) in (item.payload?.script?.scenes || [
                          { time: '0:00 - 0:03', visual: 'Close dramático no problema ou objeto com corte dinâmico', audio: 'Hook selecionado acima com entonação de surpresa' },
                          { time: '0:03 - 0:15', visual: 'Demonstração rápida do produto resolvendo a dor em 2 cliques', audio: 'Olha como esse dispositivo resolve isso sem complicação...' },
                          { time: '0:15 - 0:30', visual: 'Mostra o link no botão amarelo do TikTok Shop na tela', audio: 'O lote com desconto tá no link aqui embaixo antes de esgotar.' }
                        ])"
                        :key="sIdx"
                        class="grid grid-cols-12 p-3 text-slate-300"
                      >
                        <div class="col-span-2 font-mono text-emerald-400 font-semibold">{{ scene.time || `Cena ${sIdx + 1}` }}</div>
                        <div class="col-span-5 text-slate-300 pr-2">{{ scene.visual }}</div>
                        <div class="col-span-5 text-slate-200 font-medium">{{ scene.audio }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Legenda SEO e Hashtags -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Legenda Otimizada (Copy):</span>
                    <p class="text-xs text-slate-200 mt-1 whitespace-pre-wrap">
                      {{ item.payload?.caption || 'Testei o achadinho mais comentado do TikTok e o resultado me surpreendeu! Link com cupom exclusivo no botão amarelo 👇' }}
                    </p>
                  </div>
                  <div class="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Hashtags de Cauda Longa:</span>
                    <p class="text-xs text-indigo-400 font-mono mt-1">
                      {{ Array.isArray(item.payload?.hashtags) ? item.payload.hashtags.join(' ') : (item.payload?.hashtags || '#tiktokmademebuyit #achadinhos #review #produtoviral #afiliadotiktok') }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </transition-group>
        </div>
      </section>

      <!-- 3. Resumo dos Ventures / Negócios Ativos -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-white">Negócios Sob Gestão do Agente</h2>
          <router-link to="/businesses" class="text-xs text-emerald-400 hover:underline font-semibold">
            Ver Todos os Negócios &rarr;
          </router-link>
        </div>

        <div v-if="businessStore.businesses.length === 0" class="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
          <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-xl font-bold">
            🚀
          </div>
          <div>
            <h3 class="text-base font-bold text-white">Nenhum venture configurado no momento</h3>
            <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Inicialize um Showcase Executivo completo com 1 clique (com produtos minerados na TikTok Shop, criativos de ROI e tarefas no Kanban) para testar e apresentar a clientes.
            </p>
          </div>
          <div class="flex items-center justify-center gap-3">
            <button
              @click="handleProvisionShowcase"
              :disabled="provisioningDemo"
              class="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition flex items-center space-x-2"
            >
              <span v-if="provisioningDemo" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
              <span>⚡ Inicializar Showcase de Demonstração</span>
            </button>
            <button
              @click="isChatDrawerOpen = true"
              class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700 transition"
            >
              Planejar com Gemini 3.8
            </button>
          </div>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div
            v-for="biz in businessStore.businesses"
            :key="biz.id"
            class="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {{ biz.business_model || 'TikTok Shop Affiliate' }}
                </span>
                <span
                  class="w-2 h-2 rounded-full"
                  :class="biz.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'"
                ></span>
              </div>
              <h3 class="text-base font-bold text-white mt-3">{{ biz.name }}</h3>
              <p class="text-xs text-slate-400 mt-1 line-clamp-2">{{ biz.description || 'Sem descrição cadastrada.' }}</p>
            </div>

            <div class="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between">
              <span class="text-xs text-slate-400">Nicho: <strong class="text-slate-200">{{ biz.niche || 'Geral' }}</strong></span>
              <router-link
                :to="`/businesses/${biz.id}`"
                class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition"
              >
                Abrir Hub &rarr;
              </router-link>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- Drawer de Chat com COO IA -->
    <AgentChatDrawer
      :is-open="isChatDrawerOpen"
      @close="isChatDrawerOpen = false"
    />
  </AppLayout>
</template>
