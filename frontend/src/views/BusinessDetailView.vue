<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import AgentChatDrawer from '@/components/AgentChatDrawer.vue'
import BusinessGrowthTab from '@/components/BusinessGrowthTab.vue'
import BusinessGalleryTab from '@/components/BusinessGalleryTab.vue'
import BusinessSettingsCredentialsTab from '@/components/BusinessSettingsCredentialsTab.vue'
import TaskDetailModal from '@/components/TaskDetailModal.vue'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'
import { groupDarkScripts } from '@/utils/scriptGrouping'

const route = useRoute()
const router = useRouter()
const businessStore = useBusinessStore()
const swal = useSwal()

const businessId = route.params.id
const activeTab = ref('canvas') // dark_studio | tiktok | gallery | credentials | tasks | canvas | automations | growth
const galleryCounts = ref({ videos: 0, files: 0 })
const isChatDrawerOpen = ref(false)
const miningInProgress = ref(false)
const tasks = ref([])
const loadingTasks = ref(false)
const executingTaskId = ref(null)
const executingAllTasks = ref(false)
const selectedTaskForDetail = ref(null)
const showTaskDetailModal = ref(false)

// Dark Channel Studio States
const darkScripts = ref([])
const darkTopics = ref([])
const loadingDarkStudio = ref(false)
const generatingDarkScript = ref(false)
const showNewScriptModal = ref(false)
const selectedDarkScript = ref(null)
const newScriptForm = ref({
  title: '',
  topic: '',
  format_type: 'short',
  target_platform: 'youtube_shorts',
  tone: 'Misterioso, instigante e com suspense crescente',
  visual_style: 'Cinemático 8k hiper-realista, iluminação dramática, Unreal Engine 5 render style',
  voice_persona: 'Voz masculina profunda e documental, ritmo pausado',
})

const darkScriptsViewMode = ref('grouped') // 'grouped' | 'flat'
const expandedGroupKeys = ref(new Set())

const displayDarkScripts = computed(() => {
  if (darkScriptsViewMode.value === 'flat') {
    return darkScripts.value
  }
  return groupDarkScripts(darkScripts.value)
})

const groupedStats = computed(() => {
  const groups = displayDarkScripts.value
  const totalSeries = groups.filter((g) => g.isGroup).length
  const totalStandalone = groups.filter((g) => !g.isGroup).length
  return {
    totalSeries,
    totalStandalone,
    totalCards: groups.length,
    totalScenes: darkScripts.value.length,
  }
})

function toggleGroupExpand(key) {
  if (expandedGroupKeys.value.has(key)) {
    expandedGroupKeys.value.delete(key)
  } else {
    expandedGroupKeys.value.add(key)
  }
}

function isGroupExpanded(key) {
  return expandedGroupKeys.value.has(key)
}

function openScriptDetail(scriptOrGroup) {
  if (scriptOrGroup.isGroup) {
    const consolidatedScenes = []
    let sceneIdx = 1
    for (const item of scriptOrGroup.items) {
      if (item.scenes && item.scenes.length > 0) {
        for (const sc of item.scenes) {
          consolidatedScenes.push({
            ...sc,
            scene_number: sc.scene_number || sceneIdx++,
            origin_item_title: item.parsedSceneTitle || item.title,
          })
        }
      } else {
        consolidatedScenes.push({
          scene_number: item.parsedSceneNumber || sceneIdx++,
          timestamp: `Cena #${item.parsedSceneNumber || sceneIdx}`,
          narration: item.full_narration || item.hook || item.title,
          visual_prompt: item.visual_prompt || item.content?.visual_prompt || 'Visual prompt cinemático para IA',
          on_screen_text: item.parsedSceneTitle || item.title,
          b_roll_description: item.b_roll_description || item.content?.b_roll_description || '',
          origin_item_title: item.parsedSceneTitle || item.title,
        })
      }
    }
    selectedDarkScript.value = {
      ...scriptOrGroup,
      scenes: consolidatedScenes,
    }
  } else {
    selectedDarkScript.value = scriptOrGroup
  }
}

const isDarkChannel = computed(() => {
  const arch = business.value?.archetype || business.value?.type
  return arch === 'canal_dark' || arch === 'dark_channel_automation'
})

onMounted(async () => {
  await loadBusiness()
  await Promise.all([loadTasks(), loadGallerySummary()])
  if (isDarkChannel.value) {
    activeTab.value = 'dark_studio'
    await loadDarkStudio()
  } else {
    activeTab.value = 'tiktok'
  }
  if (route.query.tab && typeof route.query.tab === 'string') {
    activeTab.value = route.query.tab
  }
})

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string') {
      activeTab.value = newTab
    }
  }
)

async function loadGallerySummary() {
  try {
    const res = await api.get('/v1/storage/outputs', { params: { business_id: Number(businessId) } })
    galleryCounts.value = {
      videos: res.data?.videos_count || (res.data?.videos || []).length || 0,
      files: res.data?.total_files || (res.data?.files || []).length || 0,
    }
  } catch {
    // silencioso
  }
}

async function loadDarkStudio() {
  loadingDarkStudio.value = true
  try {
    const [scriptsRes, topicsRes] = await Promise.all([
      api.get(`/businesses/${businessId}/dark-studio/scripts`),
      api.get(`/businesses/${businessId}/dark-studio/topics`),
    ])
    darkScripts.value = scriptsRes.data.data || []
    darkTopics.value = topicsRes.data.data || []
  } catch (err) {
    console.error('Erro ao carregar estúdio dark:', err)
  } finally {
    loadingDarkStudio.value = false
  }
}

async function handleGenerateDarkScript() {
  if (!newScriptForm.value.title.trim() || !newScriptForm.value.topic.trim()) {
    swal.error('Campos obrigatórios', 'Por favor, informe o título e a premissa/tema do vídeo.')
    return
  }

  generatingDarkScript.value = true
  try {
    const res = await api.post(`/businesses/${businessId}/dark-studio/generate-script`, newScriptForm.value)
    swal.toast('Roteiro gerado com sucesso e submetido para supervisão!', 'success')
    showNewScriptModal.value = false
    newScriptForm.value = {
      title: '',
      topic: '',
      format_type: 'short',
      target_platform: 'youtube_shorts',
      tone: 'Misterioso, instigante e com suspense crescente',
      visual_style: 'Cinemático 8k hiper-realista, iluminação dramática, Unreal Engine 5 render style',
      voice_persona: 'Voz masculina profunda e documental, ritmo pausado',
    }
    await loadDarkStudio()
    await loadTasks()
    if (res.data?.data) {
      selectedDarkScript.value = res.data.data
    }
  } catch (err) {
    swal.error('Erro ao gerar roteiro', err.response?.data?.message || err.message)
  } finally {
    generatingDarkScript.value = false
  }
}

function selectTopicForScript(t) {
  newScriptForm.value.title = t.topic
  newScriptForm.value.topic = t.hook_angle
  newScriptForm.value.format_type = t.format_recommended || 'short'
  newScriptForm.value.target_platform = t.format_recommended === 'long' ? 'youtube_long' : 'youtube_shorts'
  showNewScriptModal.value = true
}

function copyPrompt(text) {
  if (!text) return
  navigator.clipboard.writeText(text)
  swal.toast('Prompt copiado para a área de transferência!', 'success')
}

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

async function handleExecuteTask(taskOrId) {
  const taskId = typeof taskOrId === 'object' ? taskOrId.id : taskOrId
  executingTaskId.value = taskId
  try {
    const res = await api.post(`/tasks/${taskId}/execute`)
    swal.toast(res.data?.message || 'Tarefa executada com sucesso pelo IA Worker!', 'success')
    await loadTasks()
    if (selectedTaskForDetail.value && selectedTaskForDetail.value.id === taskId) {
      const updated = tasks.value.find((t) => t.id === taskId)
      if (updated) selectedTaskForDetail.value = updated
    }
    if (isDarkChannel.value) {
      await loadDarkStudio()
    }
  } catch (err) {
    swal.error('Erro ao executar tarefa', err.response?.data?.detail || err.message)
  } finally {
    executingTaskId.value = null
  }
}

async function handleExecuteAllTasks() {
  executingAllTasks.value = true
  try {
    const res = await api.post('/tasks/execute-pending', null, { params: { business_id: businessId } })
    swal.toast(res.data?.message || 'Tarefas executadas com sucesso pelo IA Worker!', 'success')
    await loadTasks()
    if (isDarkChannel.value) {
      await loadDarkStudio()
    }
  } catch (err) {
    swal.error('Erro ao executar tarefas', err.response?.data?.detail || err.message)
  } finally {
    executingAllTasks.value = false
  }
}

async function handleApproveTask(taskId) {
  try {
    await api.patch(`/tasks/${taskId}/move`, { status: 'done' })
    swal.toast('Tarefa aprovada e concluída com sucesso!', 'success')
    await loadTasks()
    if (selectedTaskForDetail.value && selectedTaskForDetail.value.id === taskId) {
      const updated = tasks.value.find((t) => t.id === taskId)
      if (updated) selectedTaskForDetail.value = updated
    }
  } catch (err) {
    swal.error('Erro ao aprovar tarefa', err.message)
  }
}

async function handleMoveTask(task, targetStatus) {
  try {
    await api.patch(`/tasks/${task.id}/move`, { status: targetStatus })
    swal.toast(`Tarefa movida para "${targetStatus}"`, 'info')
    await loadTasks()
    if (selectedTaskForDetail.value && selectedTaskForDetail.value.id === task.id) {
      const updated = tasks.value.find((t) => t.id === task.id)
      if (updated) selectedTaskForDetail.value = updated
    }
  } catch (err) {
    swal.error('Movimento não permitido', err.response?.data?.message || err.message)
  }
}

async function handleDeleteTask(task) {
  const confirmed = await swal.confirm({
    title: 'Excluir esta tarefa?',
    text: `Você está excluindo "${task.title}".`,
    confirmText: 'Sim, excluir',
    confirmButtonColor: '#ef4444',
  })
  if (!confirmed) return
  try {
    await api.delete(`/tasks/${task.id}`)
    swal.toast('Tarefa excluída.', 'info')
    showTaskDetailModal.value = false
    await loadTasks()
  } catch (err) {
    swal.error('Erro ao excluir tarefa', err.response?.data?.message || err.message)
  }
}

function openTaskDetail(task) {
  selectedTaskForDetail.value = task
  showTaskDetailModal.value = true
}

function viewTaskResult(task) {
  openTaskDetail(task)
}

const business = computed(() => businessStore.currentBusiness || {})

const businessModelLabel = computed(() => {
  if (business.value?.business_model) return business.value.business_model
  if (isDarkChannel.value) return 'Canal Dark Automatizado (YouTube / TikTok)'
  const arch = business.value?.archetype || business.value?.type
  if (arch === 'affiliate_tiktok' || arch === 'tiktok_shop_affiliate') return 'TikTok Shop Afiliados'
  if (arch === 'infoproduct') return 'Infoprodutos'
  if (arch === 'saas') return 'SaaS Bootstrapped'
  if (arch === 'ecommerce') return 'E-commerce / Drop'
  return 'Venture Digital'
})

const canvasData = computed(() => {
  const c = business.value?.canvas
  if (isDarkChannel.value) {
    if (c && c.customer_segments && !JSON.stringify(c).includes('impulso no TikTok') && !JSON.stringify(c).includes('Comissão de afiliados (15%')) {
      return c
    }
    return {
      value_propositions: [
        'Vídeos altamente magnéticos e documentais sem rosto, com retenção acima da média.',
        'Storytelling em múltiplos atos gerando curiosidade e visualizações em massa no YouTube e TikTok.',
      ],
      customer_segments: [
        'Público interessado em mistérios, fatos históricos, curiosidades e reflexões profundas.',
      ],
      channels: [
        'YouTube Shorts & Vídeos Longos (8-12 min)',
        'TikTok Vídeos Virais',
        'Instagram Reels',
      ],
      customer_relationships: [
        'Engajamento contínuo nos comentários, ganchos em partes (Parte 1, 2, 3) e senso de comunidade.',
      ],
      revenue_streams: [
        'YouTube AdSense (RPM qualificado)',
        'Fundo de Criadores do TikTok (Creator Rewards)',
        'Comissões de infoprodutos e afiliados recomendados na descrição/bio',
      ],
      key_resources: [
        'Cérebro Gemini 3.8 para Roteirização e Engenharia de Prompts',
        'Vozes Sintéticas Hiper-Realistas (TTS)',
        'Banco de Prompts Visuais e Renderizador de Vídeos',
      ],
      key_activities: [
        'Mineração diária de tópicos e ganchos de alta curiosidade',
        'Roteirização em 5 atos com ganchos de 3 segundos',
        'Produção de narrações, legendas dinâmicas e assets visuais',
        'Revisão na Fila de Supervisão e publicação programada',
      ],
      key_partners: [
        'YouTube Creator Studio & TikTok Creator Program',
        'Provedores de IA Generativa de Áudio e Imagem',
      ],
      cost_structure: [
        'Assinaturas de APIs de IA e Infraestrutura Cloud/VPS',
      ],
    }
  }

  return c || {
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
  const b = business.value?.brand_rules
  if (isDarkChannel.value) {
    if (b && b.guidelines && b.guidelines.length > 0 && !JSON.stringify(b).includes('link amarelo')) {
      return b
    }
    return {
      tone_of_voice: b?.tone_of_voice || 'Misterioso, imersivo, com pausas dramáticas e ritmo dinâmico de alta retenção.',
      target_audience: b?.target_audience || 'Audiência ávida por curiosidades, mistérios e histórias épicas no YouTube e TikTok.',
      guidelines: [
        'Gancho ultra impactante nos primeiros 3 segundos para quebrar a rolagem',
        'Ritmo narrativo com pausas dramáticas e trilha imersiva',
        'Dividir narrativas densas em partes (Part 1, 2, 3) para retenção e fidelização',
      ],
    }
  }

  return b || {
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

const configuredChannels = computed(() => {
  return business.value?.channels_configured || []
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

function formatTaskStatus(status) {
  const map = {
    'backlog': 'Backlog',
    'in_progress_agent': 'IA em Execução',
    'awaiting_supervision': 'Aguardando Supervisão',
    'todo_user': 'A Fazer (Humano)',
    'done': 'Concluído',
    'completed': 'Concluído',
  }
  return map[status] || status || 'Pendente'
}

function formatTaskAssignee(assignee) {
  const map = {
    'agent': 'Agente IA',
    'user': 'Você (Operador)',
  }
  return map[assignee] || assignee || 'Agente IA'
}

function formatTaskPriority(priority) {
  const map = {
    'urgent': 'Urgente',
    'high': 'Alta',
    'medium': 'Média',
    'low': 'Baixa',
  }
  return map[priority] || priority || 'Normal'
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
        <router-link to="/businesses" class="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition shrink-0 min-h-[36px] min-w-[36px] flex items-center justify-center" title="Voltar aos negócios">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </router-link>
        <div class="min-w-0 flex-1">
          <h1 class="text-base sm:text-xl font-bold text-white tracking-tight flex items-center space-x-2 truncate">
            <span class="truncate">{{ business.name || 'Carregando negócio...' }}</span>
            <span
              v-if="business.status"
              class="px-2 py-0.5 text-[10px] font-bold rounded-full border shrink-0"
              :class="business.status === 'active'
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                : 'bg-slate-800 text-slate-400 border-slate-700'"
            >
              {{ business.status === 'active' ? 'Ativo' : 'Pausado' }}
            </span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5 truncate">
            Nicho: <span class="text-slate-200 font-semibold">{{ business.niche || 'Geral' }}</span> · Modelo: <span class="text-slate-200 font-medium">{{ businessModelLabel }}</span>
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Card Executivo do Negócio: Resumo, Canais Conectados e Ações Rápidas (Separado das Abas) -->
      <div class="p-4 sm:p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-lg shadow-black/20">
        <div class="space-y-2 min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
              {{ businessModelLabel }}
            </span>
            <span
              class="px-2.5 py-1 text-[10px] font-bold rounded-lg border cursor-pointer transition"
              :class="configuredChannels.includes('youtube')
                ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'"
              @click="activeTab = 'credentials'"
              title="Configurar acesso do YouTube"
            >
              ▶️ YouTube: {{ configuredChannels.includes('youtube') ? (business.channels?.youtube?.handle || 'Conectado') : 'Sem acesso' }}
            </span>
            <span
              class="px-2.5 py-1 text-[10px] font-bold rounded-lg border cursor-pointer transition"
              :class="configuredChannels.includes('tiktok')
                ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'"
              @click="activeTab = 'credentials'"
              title="Configurar acesso do TikTok"
            >
              🎵 TikTok: {{ configuredChannels.includes('tiktok') ? (business.channels?.tiktok?.handle || 'Conectado') : 'Sem acesso' }}
            </span>
          </div>
          <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed">
            {{ business.description || 'Venture autônomo gerenciado pelo Gemini 3.8 com produção de mídia, roteiros e execução de tarefas.' }}
          </p>
        </div>

        <!-- Botões de Ação Rápida Isolados (Sem Colidir com as Abas) -->
        <div class="flex flex-wrap items-center gap-2 shrink-0">
          <button
            @click="activeTab = 'credentials'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
          >
            <span>🔐</span>
            <span>Acessos &amp; Contas</span>
          </button>

          <button
            @click="isChatDrawerOpen = true"
            class="px-4 py-2 text-xs font-bold rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 transition flex items-center justify-center gap-1.5 shadow-md shadow-indigo-600/20 min-h-[38px] whitespace-nowrap active:scale-95"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Conversar com COO IA</span>
          </button>

          <button
            @click="handleToggleStatus"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl border transition min-h-[38px] text-center whitespace-nowrap active:scale-95"
            :class="business.status === 'active'
              ? 'bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20'"
          >
            {{ business.status === 'active' ? 'Pausar Venture' : 'Ativar Venture' }}
          </button>
        </div>
      </div>

      <!-- Barra de Navegação por Abas (100% da Largura, Sem Textos Cortados) -->
      <div class="p-2 rounded-2xl bg-slate-900 border border-slate-800">
        <div class="flex flex-wrap items-center gap-1.5">
          <!-- 1. Estúdio Dark ou Vitrine TikTok -->
          <button
            v-if="isDarkChannel"
            @click="activeTab = 'dark_studio'"
            class="px-3.5 py-2 text-xs font-bold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'dark_studio' ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>🎬</span>
            <span>Estúdio Dark &amp; Roteiros</span>
            <span class="px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">
              {{ darkScripts.length }}
            </span>
          </button>
          <button
            v-else
            @click="activeTab = 'tiktok'"
            class="px-3.5 py-2 text-xs font-bold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'tiktok' ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>🛒</span>
            <span>Vitrine TikTok Shop</span>
            <span class="px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">
              {{ tiktokProducts.length }}
            </span>
          </button>

          <!-- 2. Galeria & Arquivos Deste Negócio -->
          <button
            @click="activeTab = 'gallery'"
            class="px-3.5 py-2 text-xs font-bold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'gallery' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>🎞️</span>
            <span>Galeria &amp; Vídeos</span>
            <span class="px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
              {{ galleryCounts.videos }}
            </span>
          </button>

          <!-- 3. Dados & Acessos (YouTube, TikTok, Config) -->
          <button
            @click="activeTab = 'credentials'"
            class="px-3.5 py-2 text-xs font-bold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'credentials' ? 'bg-amber-500/20 text-amber-200 border border-amber-500/30 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>🔐</span>
            <span>Dados &amp; Acessos</span>
            <span
              class="px-1.5 py-0.5 rounded-full text-[10px] font-mono"
              :class="configuredChannels.length > 0 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'"
            >
              {{ configuredChannels.length }}
            </span>
          </button>

          <!-- 4. Operações & Tarefas -->
          <button
            @click="activeTab = 'tasks'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'tasks' ? 'bg-slate-800 text-white border border-slate-700 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>📋</span>
            <span>Operações &amp; Tarefas</span>
            <span class="px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-300 text-[10px] font-mono">
              {{ tasks.length }}
            </span>
          </button>

          <!-- 5. Canvas & Marca -->
          <button
            @click="activeTab = 'canvas'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'canvas' ? 'bg-slate-800 text-white border border-slate-700 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>🧭</span>
            <span>Canvas &amp; Marca</span>
          </button>

          <!-- 6. Automações Cron -->
          <button
            @click="activeTab = 'automations'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'automations' ? 'bg-slate-800 text-white border border-slate-700 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>⏰</span>
            <span>Automações Cron</span>
            <span class="px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
              {{ automations.length }}
            </span>
          </button>

          <!-- 7. ROI & Auto-Otimização -->
          <button
            @click="activeTab = 'growth'"
            class="px-3.5 py-2 text-xs font-semibold rounded-xl transition flex items-center gap-1.5 min-h-[38px] whitespace-nowrap"
            :class="activeTab === 'growth' ? 'bg-slate-800 text-white border border-slate-700 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'"
          >
            <span>⚡</span>
            <span>ROI &amp; Growth</span>
          </button>
        </div>
      </div>

      <!-- ABA: Galeria de Vídeos & Arquivos Deste Negócio -->
      <div v-if="activeTab === 'gallery'">
        <BusinessGalleryTab
          :business-id="businessId"
          :business="business"
          @counts="(c) => { galleryCounts = c }"
        />
      </div>

      <!-- ABA: Dados Gerais & Acessos do Negócio (YouTube / TikTok / Integrações) -->
      <div v-if="activeTab === 'credentials'">
        <BusinessSettingsCredentialsTab
          :business-id="businessId"
          :business="business"
          @updated="loadBusiness"
        />
      </div>

      <!-- ABA 0: ROI & Auto-Otimização (Growth Engine) -->
      <div v-if="activeTab === 'growth'">
        <BusinessGrowthTab :business-id="businessId" :business="business" />
      </div>

      <!-- ABA 1: Business Model Canvas & Regras da Marca -->
      <div v-if="activeTab === 'canvas'" class="space-y-6">
        <!-- Proposta de Valor em Destaque -->
        <div class="p-5 rounded-2xl bg-indigo-950/25 border border-indigo-500/30 space-y-2">
          <h4 class="text-xs font-bold text-indigo-300 uppercase tracking-wider">💎 Proposta de Valor Central</h4>
          <ul class="text-xs text-slate-200 space-y-1.5 list-disc list-inside">
            <li v-for="(item, idx) in canvasData.value_propositions || []" :key="idx" class="font-medium">{{ item }}</li>
          </ul>
        </div>

        <!-- Canvas Grid Responsivo (3 Colunas Equilibradas) -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Segmentos de Clientes</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.customer_segments || []" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Canais de Distribuição</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.channels || []" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Relacionamento</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.customer_relationships || []" :key="idx">{{ item }}</li>
            </ul>
          </div>

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

          <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Parcerias Chave</h4>
            <ul class="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li v-for="(item, idx) in canvasData.key_partners || []" :key="idx">{{ item }}</li>
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

      <!-- ABA 2A: Estúdio Dark & Roteiros (Canais Dark / YouTube & TikTok) -->
      <div v-if="activeTab === 'dark_studio'" class="space-y-6">
        <!-- Top Banner Estúdio Dark -->
        <div class="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
          <div>
            <div class="flex items-center space-x-2">
              <span class="px-2.5 py-1 text-[10px] font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                🎬 Arquétipo: Canal Dark / YouTube & TikTok
              </span>
              <span class="text-xs text-slate-400">
                Nicho: <strong class="text-slate-200">{{ business.niche || 'Mistérios & Curiosidades' }}</strong>
              </span>
            </div>
            <h3 class="text-xl font-black text-white mt-2 tracking-tight flex items-center space-x-2">
              <span>Estúdio de Roteiros & Vídeos Faceless</span>
              <span class="text-indigo-400 text-sm">● Gemini 3.8 Ativo</span>
            </h3>
            <p class="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Crie roteiros virais completos em 5 atos ou shorts de 60 segundos com hooks hipnóticos, minutagem, narração em português e prompts visuais prontos para Midjourney e Runway.
            </p>
          </div>

          <div class="flex items-center space-x-3 shrink-0">
            <button
              @click="loadDarkStudio"
              :disabled="loadingDarkStudio"
              class="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
              title="Recarregar dados do estúdio"
            >
              <svg class="w-4 h-4" :class="{'animate-spin': loadingDarkStudio}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              @click="showNewScriptModal = true"
              class="px-4 py-2.5 rounded-xl text-xs font-black text-white bg-indigo-600 hover:bg-indigo-500 transition shadow-lg shadow-indigo-600/25 flex items-center space-x-2"
            >
              <span>⚡</span>
              <span>Gerar Novo Roteiro com IA</span>
            </button>
          </div>
        </div>

        <!-- Seção 1: Pautas e Ideação Viral Mineradas pelo Agente -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-white tracking-tight flex items-center space-x-2">
                <span>🔥 Pautas & Temas Virais Minerados</span>
                <span class="px-2 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-300 border border-rose-500/20 font-bold">Alta Demanda</span>
              </h4>
              <p class="text-xs text-slate-400 mt-0.5">
                Pautas ranqueadas por potencial de clique (CTR previsto) e retenção aos 30 segundos.
              </p>
            </div>
            <span class="text-xs text-slate-500 font-mono">{{ darkTopics.length }} tópicos minerados</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              v-for="(t, idx) in darkTopics"
              :key="idx"
              class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 hover:border-indigo-500/40 transition flex flex-col justify-between space-y-3 group"
            >
              <div>
                <div class="flex items-center justify-between">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono" :class="t.format_recommended === 'long' ? 'bg-indigo-500/10 text-indigo-300' : 'bg-emerald-500/10 text-emerald-300'">
                    {{ t.format_recommended === 'long' ? 'Vídeo Longo (8-12m)' : 'Shorts / TikTok (60s)' }}
                  </span>
                  <span class="text-[11px] font-bold text-emerald-400 font-mono">CTR: {{ t.predicted_ctr }}</span>
                </div>
                <h5 class="text-sm font-bold text-white mt-2 group-hover:text-indigo-300 transition">{{ t.topic }}</h5>
                <p class="text-xs text-slate-400 mt-1 leading-relaxed">{{ t.hook_angle }}</p>
              </div>

              <div class="pt-2 border-t border-slate-900 flex items-center justify-between">
                <span class="text-[10px] text-slate-500">Potencial: <strong class="text-slate-300">{{ t.estimated_views }}</strong></span>
                <button
                  @click="selectTopicForScript(t)"
                  class="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-indigo-600/30 text-indigo-200 hover:bg-indigo-600 hover:text-white transition"
                >
                  Roteirizar Pauta &rarr;
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Seção 2: Roteiros Produzidos & Fila de Produção -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div class="flex items-center space-x-2">
                <h4 class="text-sm font-bold text-white tracking-tight">Roteiros Prontos & Supervisão</h4>
                <span v-if="darkScriptsViewMode === 'grouped' && groupedStats.totalSeries > 0" class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  Agrupado por Produção ({{ groupedStats.totalSeries }} séries)
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">Roteiros completos com narração, minutagem e prompts de imagens para IA.</p>
            </div>

            <div class="flex items-center space-x-3">
              <!-- Seletor de Modo de Visualização (Agrupado vs Plano) -->
              <div class="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  type="button"
                  @click="darkScriptsViewMode = 'grouped'"
                  class="px-2.5 py-1 rounded-lg font-semibold transition flex items-center space-x-1.5"
                  :class="darkScriptsViewMode === 'grouped' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
                  title="Agrupar cenas do mesmo vídeo ou série em um card mestre"
                >
                  <span>🎬</span>
                  <span>Agrupado</span>
                </button>
                <button
                  type="button"
                  @click="darkScriptsViewMode = 'flat'"
                  class="px-2.5 py-1 rounded-lg font-semibold transition flex items-center space-x-1.5"
                  :class="darkScriptsViewMode === 'flat' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
                  title="Exibir cada cena como um card individual"
                >
                  <span>📄</span>
                  <span>Cenas Avulsas</span>
                </button>
              </div>

              <span class="text-xs text-slate-500 font-mono">
                {{ darkScriptsViewMode === 'grouped' ? `${displayDarkScripts.length} produções (${darkScripts.length} cenas)` : `${darkScripts.length} roteiros` }}
              </span>
            </div>
          </div>

          <!-- Estado Vazio -->
          <div v-if="darkScripts.length === 0" class="p-12 text-center rounded-xl bg-slate-950/40 border border-slate-800 text-xs text-slate-400 space-y-2">
            <p>Nenhum roteiro dark gerado ainda para esta venture.</p>
            <p class="text-slate-500">Clique em "Gerar Novo Roteiro com IA" ou escolha uma das pautas virais acima.</p>
          </div>

          <!-- Grid de Roteiros -->
          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="s in displayDarkScripts"
              :key="s.isGroup ? s.groupKey : s.id"
              class="p-5 rounded-xl bg-slate-950 border transition flex flex-col justify-between space-y-4 shadow-sm"
              :class="s.isGroup ? 'border-indigo-500/40 hover:border-indigo-500/80 bg-gradient-to-b from-indigo-950/10 to-slate-950 md:col-span-2' : 'border-slate-800 hover:border-slate-700'"
            >
              <div>
                <!-- Cabeçalho do Card (Agrupado vs Simples) -->
                <div class="flex items-center justify-between">
                  <div class="flex flex-wrap items-center gap-2">
                    <span
                      v-if="s.isGroup"
                      class="px-2.5 py-0.5 rounded text-[10px] font-black font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1 shadow-sm"
                    >
                      <span>🎬</span>
                      <span>SÉRIE / VÍDEO CONSOLIDADO</span>
                    </span>
                    <span
                      class="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase"
                      :class="s.format_type === 'long' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-emerald-500/20 text-emerald-300'"
                    >
                      {{ s.format_type === 'long' ? 'YouTube Longo' : 'Shorts / TikTok' }}
                    </span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      {{ s.status === 'supervision' ? 'Em Supervisão' : s.status === 'approved' ? 'Aprovado' : s.status }}
                    </span>
                  </div>
                  <span class="text-[11px] font-bold font-mono" :class="s.isGroup ? 'text-indigo-400 bg-indigo-950/40 px-2.5 py-0.5 rounded-full border border-indigo-500/20' : 'text-slate-500'">
                    {{ s.isGroup ? `${s.items.length} cenas agrupadas` : `${s.scenes_count || (s.scenes && s.scenes.length) || 0} cenas` }}
                  </span>
                </div>

                <!-- Título -->
                <h5 class="text-base font-black text-white mt-3 tracking-tight flex items-center space-x-2">
                  <span>{{ s.title }}</span>
                  <span v-if="s.isGroup" class="text-xs text-slate-400 font-normal">({{ s.items.length }} partes)</span>
                </h5>

                <!-- Gancho Destacado -->
                <div v-if="s.hook" class="mt-2.5 p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-xs">
                  <span class="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block mb-0.5">
                    {{ s.isGroup ? '⚡ Hook de Abertura da Produção:' : 'Hook Inicial (0-3s):' }}
                  </span>
                  <p class="text-slate-200 italic font-medium">"{{ s.hook }}"</p>
                </div>

                <p v-if="!s.isGroup && s.full_narration" class="text-xs text-slate-400 mt-2.5 line-clamp-2 leading-relaxed">
                  {{ s.full_narration }}
                </p>

                <!-- Tags SEO -->
                <div v-if="s.seo_tags && s.seo_tags.length" class="flex flex-wrap gap-1 mt-3">
                  <span
                    v-for="(tag, tidx) in s.seo_tags.slice(0, 6)"
                    :key="tidx"
                    class="px-2 py-0.5 rounded text-[10px] bg-slate-900 text-slate-400 font-mono"
                  >
                    #{{ tag }}
                  </span>
                </div>

                <!-- Gaveta Accordion de Cenas (Exclusivo para Grupos) -->
                <div v-if="s.isGroup" class="mt-4 pt-3 border-t border-slate-900/80">
                  <button
                    type="button"
                    @click="toggleGroupExpand(s.groupKey)"
                    class="w-full px-3 py-2 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 flex items-center justify-between text-xs text-slate-300 font-semibold transition group"
                  >
                    <span class="flex items-center space-x-2">
                      <span class="text-indigo-400">🎞️</span>
                      <span>{{ isGroupExpanded(s.groupKey) ? 'Recolher Lista de Cenas' : `Ver Todas as ${s.items.length} Cenas Deste Vídeo` }}</span>
                    </span>
                    <span class="text-[11px] text-slate-500 group-hover:text-slate-300 flex items-center space-x-1">
                      <span>{{ isGroupExpanded(s.groupKey) ? 'Ocultar' : 'Expandir' }}</span>
                      <svg
                        class="w-4 h-4 transition-transform duration-200"
                        :class="{'rotate-180': isGroupExpanded(s.groupKey)}"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </span>
                  </button>

                  <!-- Cenas Aninhadas Expandidas -->
                  <div v-if="isGroupExpanded(s.groupKey)" class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                      v-for="(subItem, subIdx) in s.items"
                      :key="subItem.id || subIdx"
                      class="p-3.5 rounded-xl bg-slate-900 border border-slate-800/90 hover:border-indigo-500/40 space-y-2 transition flex flex-col justify-between"
                    >
                      <div>
                        <div class="flex items-center justify-between">
                          <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-indigo-500/20 text-indigo-300">
                            Cena #{{ subItem.parsedSceneNumber || (subIdx + 1) }}
                          </span>
                          <span class="text-[10px] text-slate-400 font-mono">
                            {{ subItem.status === 'supervision' ? 'Em Supervisão' : subItem.status }}
                          </span>
                        </div>
                        <h6 class="text-xs font-bold text-white mt-1.5 line-clamp-1">
                          {{ subItem.parsedSceneTitle || subItem.title }}
                        </h6>
                        <p v-if="subItem.hook || subItem.full_narration" class="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                          "{{ subItem.hook || subItem.full_narration }}"
                        </p>
                      </div>

                      <div class="pt-2 border-t border-slate-950 flex items-center justify-end">
                        <button
                          type="button"
                          @click.stop="openScriptDetail(subItem)"
                          class="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 transition flex items-center space-x-1"
                        >
                          <span>Ver Cena & Prompts</span>
                          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Ações do Card -->
              <div class="pt-3 border-t border-slate-900 flex items-center justify-between">
                <span class="text-[10px] text-slate-500 font-mono">
                  {{ s.created_at ? new Date(s.created_at).toLocaleDateString('pt-BR') : 'Recente' }}
                </span>
                <div class="flex items-center space-x-2">
                  <button
                    @click="openScriptDetail(s)"
                    class="px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center space-x-1.5 shadow-sm"
                  >
                    <span>{{ s.isGroup ? 'Ver Roteiro Consolidado' : 'Ver Cenas & Prompts' }}</span>
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <router-link
                    v-if="s.approval_queue_id || (s.items && s.items.some(it => it.approval_queue_id))"
                    to="/approvals"
                    class="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 transition"
                    title="Aprovar na fila de supervisão"
                  >
                    Supervisão &rarr;
                  </router-link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ABA 2B: Vitrine TikTok Shop (Apenas para Arquétipos TikTok Affiliate) -->
      <div v-if="!isDarkChannel && activeTab === 'tiktok'" class="space-y-4">
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
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-white">Tarefas Vinculadas a Este Venture</h3>
            <p class="text-xs text-slate-400">Demandas operacionais executadas por IA Workers ou Operador</p>
          </div>
          <div class="flex items-center space-x-3">
            <button
              @click="handleExecuteAllTasks"
              :disabled="executingAllTasks"
              class="px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition flex items-center space-x-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <span v-if="executingAllTasks" class="animate-spin">⏳</span>
              <span v-else>⚡</span>
              <span>{{ executingAllTasks ? 'Executando Tarefas...' : 'Executar Tarefas com IA' }}</span>
            </button>
            <router-link to="/tasks" class="text-xs text-emerald-400 hover:underline font-semibold">
              Abrir Kanban Geral &rarr;
            </router-link>
          </div>
        </div>

        <div v-if="tasks.length === 0" class="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
          Nenhuma tarefa cadastrada para este negócio.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="task in tasks"
            :key="task.id"
            @click="openTaskDetail(task)"
            class="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/60 cursor-pointer transition flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs group"
          >
            <div class="space-y-1.5 flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span
                  class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border tracking-wide"
                  :class="{
                    'bg-indigo-500/20 text-indigo-300 border-indigo-500/30': task.status === 'in_progress_agent',
                    'bg-amber-500/20 text-amber-300 border-amber-500/30': task.status === 'awaiting_supervision',
                    'bg-emerald-500/20 text-emerald-300 border-emerald-500/30': task.status === 'done' || task.status === 'completed',
                    'bg-slate-800 text-slate-300 border-slate-700': task.status === 'backlog' || task.status === 'todo_user'
                  }"
                >
                  {{ task.status_label || formatTaskStatus(task.status) }}
                </span>
                <span class="text-slate-400 text-[11px] flex items-center space-x-1">
                  <span>Executor:</span>
                  <strong class="text-indigo-400 font-medium">{{ task.assignee_label || formatTaskAssignee(task.assignee) }}</strong>
                </span>
                <span class="text-slate-600 text-[10px]">·</span>
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-semibold border"
                  :class="{
                    'bg-rose-500/20 text-rose-300 border-rose-500/30': task.priority === 'urgent',
                    'bg-amber-500/20 text-amber-300 border-amber-500/30': task.priority === 'high',
                    'bg-slate-800 text-slate-400 border-slate-700': task.priority !== 'urgent' && task.priority !== 'high'
                  }"
                >
                  Prioridade {{ formatTaskPriority(task.priority) }}
                </span>
                <span
                  v-if="task.result?.video_url || task.result?.media?.video?.url"
                  class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>🎬</span>
                  <span>Vídeo 9:16</span>
                </span>
                <span
                  v-else-if="task.result"
                  class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>📄</span>
                  <span>Entregável Pronto</span>
                </span>
                <span
                  v-if="task.failure_reason"
                  class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>⚠️</span>
                  <span>Falha</span>
                </span>
              </div>
              <h4 class="text-sm font-bold text-white group-hover:text-emerald-400 transition">{{ task.title }}</h4>
              <p v-if="task.description" class="text-slate-400 text-xs line-clamp-2 leading-relaxed">{{ task.description }}</p>
              <div v-if="task.result?.summary" class="text-emerald-400/90 text-[11px] bg-emerald-950/30 border border-emerald-500/20 rounded-lg p-2 mt-2">
                <strong>✓ Entregável IA:</strong> {{ task.result.summary }}
              </div>
            </div>

            <!-- Botões de Ação na Tarefa -->
            <div class="flex items-center space-x-2 shrink-0 self-end md:self-center" @click.stop>
              <button
                @click.stop="openTaskDetail(task)"
                class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1"
                title="Abrir detalhes e entregável da tarefa"
              >
                <span>{{ task.result ? '📄' : '🔍' }}</span>
                <span>{{ task.result ? 'Ver Entregável' : 'Detalhes' }}</span>
              </button>

              <button
                v-if="task.assignee === 'agent' && task.status !== 'done'"
                @click.stop="handleExecuteTask(task.id)"
                :disabled="executingTaskId === task.id"
                class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition flex items-center space-x-1 shadow-md shadow-indigo-600/20 disabled:opacity-50"
              >
                <span v-if="executingTaskId === task.id" class="animate-spin">⏳</span>
                <span v-else>⚡</span>
                <span>{{ executingTaskId === task.id ? 'Gerando...' : (task.result ? 'Reexecutar IA' : 'Executar com IA') }}</span>
              </button>

              <button
                v-if="task.status === 'awaiting_supervision'"
                @click.stop="handleApproveTask(task.id)"
                class="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 font-semibold transition flex items-center space-x-1"
                title="Aprovar entrega da IA e concluir tarefa"
              >
                <span>✓</span>
                <span>Aprovar</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL 1: Gerar Novo Roteiro Dark com IA -->
    <div
      v-if="showNewScriptModal"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
    >
      <div class="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-4 my-8">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div class="flex items-center space-x-2">
            <span class="text-xl">⚡</span>
            <div>
              <h3 class="text-base font-bold text-white">Gerar Roteiro Dark com Gemini 3.8</h3>
              <p class="text-[11px] text-slate-400">Roteirização hipnótica com minutagem, narração e prompts de IA.</p>
            </div>
          </div>
          <button @click="showNewScriptModal = false" class="text-slate-400 hover:text-white">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="handleGenerateDarkScript" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Título do Vídeo (Alto CTR)</label>
            <input
              v-model="newScriptForm.title"
              type="text"
              required
              placeholder="Ex: O Exército Fantasma que Enganou uma Guerra Inteira"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Premissa / Tese Central da Pauta</label>
            <textarea
              v-model="newScriptForm.topic"
              rows="2"
              required
              placeholder="Ex: Como soldados aliados usaram tanques infláveis e transmissões de rádio falsas para enganar o exército alemão..."
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            ></textarea>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Formato</label>
              <select
                v-model="newScriptForm.format_type"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="short">Short / TikTok (30-60 segundos)</option>
                <option value="long">Vídeo Longo (8-12 minutos, 5 atos)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Plataforma Principal</label>
              <select
                v-model="newScriptForm.target_platform"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="youtube_shorts">YouTube Shorts</option>
                <option value="tiktok">TikTok Orgânico</option>
                <option value="youtube_long">YouTube Vídeo Longo</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Estilo Visual dos Prompts de Imagem (Midjourney / Runway)</label>
            <input
              v-model="newScriptForm.visual_style"
              type="text"
              placeholder="Ex: Cinemático hiper-realista 8k, iluminação dramática, Unreal Engine 5 render style"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Persona da Voz (ElevenLabs / TTS)</label>
            <input
              v-model="newScriptForm.voice_persona"
              type="text"
              placeholder="Ex: Voz masculina profunda e documental, ritmo pausado"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div class="pt-3 border-t border-slate-800 flex items-center justify-end space-x-3">
            <button
              type="button"
              @click="showNewScriptModal = false"
              class="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancelar
            </button>
            <button
              type="submit"
              :disabled="generatingDarkScript"
              class="px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition shadow-md shadow-indigo-600/20 disabled:opacity-50 flex items-center space-x-2"
            >
              <span v-if="generatingDarkScript" class="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full"></span>
              <span>{{ generatingDarkScript ? 'Gerando com Gemini 3.8...' : 'Gerar Roteiro Completo' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL 2: Visualizador Detalhado de Roteiro & Cenas de B-Roll -->
    <div
      v-if="selectedDarkScript"
      class="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto"
    >
      <div class="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-5 my-8 max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
          <div>
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {{ selectedDarkScript.format_type === 'long' ? 'Vídeo Longo (8-12m)' : 'Shorts / TikTok (60s)' }}
              </span>
              <span class="text-xs text-slate-400 font-mono">{{ selectedDarkScript.target_platform }}</span>
            </div>
            <h3 class="text-lg font-black text-white mt-1">{{ selectedDarkScript.title }}</h3>
          </div>
          <button @click="selectedDarkScript = null" class="text-slate-400 hover:text-white p-1">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Conteúdo Scrollável -->
        <div class="space-y-4 overflow-y-auto pr-1 flex-1">
          <!-- Hook Card -->
          <div v-if="selectedDarkScript.hook" class="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30">
            <span class="text-[10px] font-black uppercase tracking-wider text-indigo-300 block mb-1">
              ⚡ Hook Hipnótico Inicial (0 a 3 segundos):
            </span>
            <p class="text-sm font-semibold text-white italic">
              "{{ selectedDarkScript.hook }}"
            </p>
          </div>

          <!-- Trilha Sonora & Voz -->
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div v-if="selectedDarkScript.suggested_music" class="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span class="text-[10px] text-slate-500 font-bold uppercase block">Trilha de Fundo Sugerida:</span>
              <p class="text-slate-200 mt-0.5 font-medium">{{ selectedDarkScript.suggested_music }}</p>
            </div>
            <div v-if="selectedDarkScript.voice_persona" class="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span class="text-[10px] text-slate-500 font-bold uppercase block">Direção de Voz (TTS):</span>
              <p class="text-slate-200 mt-0.5 font-medium">{{ selectedDarkScript.voice_persona }}</p>
            </div>
          </div>

          <!-- Tabela de Cenas / B-Roll Prompts -->
          <div>
            <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span>Cenas & Prompts para Midjourney / Runway</span>
              <span class="text-[10px] text-slate-500">{{ (selectedDarkScript.scenes || []).length }} cenas</span>
            </h4>

            <div class="space-y-3">
              <div
                v-for="(scene, sidx) in (selectedDarkScript.scenes || [])"
                :key="sidx"
                class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5 text-xs"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-2">
                    <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold text-[10px]">
                      Cena #{{ scene.scene_number || (sidx + 1) }}
                    </span>
                    <span v-if="scene.origin_item_title" class="px-2 py-0.5 rounded bg-slate-800 text-indigo-300 font-medium text-[10px] truncate max-w-[220px]" :title="scene.origin_item_title">
                      {{ scene.origin_item_title }}
                    </span>
                    <span class="text-slate-400 font-mono text-[11px]">{{ scene.timestamp }}</span>
                  </div>
                  <span v-if="scene.on_screen_text" class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-bold">
                    Texto: {{ scene.on_screen_text }}
                  </span>
                </div>

                <!-- Narração -->
                <div>
                  <span class="text-[10px] font-bold uppercase text-slate-500">Narração em Português:</span>
                  <p class="text-slate-200 mt-0.5 leading-relaxed font-medium">{{ scene.narration }}</p>
                </div>

                <!-- Prompt Visual para IA -->
                <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold uppercase text-emerald-400 font-mono flex items-center space-x-1">
                      <span>🎨</span>
                      <span>Prompt Visual (Midjourney / Runway / Leonardo):</span>
                    </span>
                    <button
                      @click="copyPrompt(scene.visual_prompt)"
                      class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 transition flex items-center space-x-1"
                    >
                      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      <span>Copiar Prompt</span>
                    </button>
                  </div>
                  <p class="text-slate-300 font-mono text-[11px] leading-relaxed break-words">
                    {{ scene.visual_prompt }}
                  </p>
                </div>

                <div v-if="scene.b_roll_description" class="text-[11px] text-slate-400">
                  <span class="text-slate-500 font-semibold">Câmera / B-Roll:</span> {{ scene.b_roll_description }}
                </div>
              </div>
            </div>
          </div>

          <!-- Narração Completa Fluída -->
          <div v-if="selectedDarkScript.full_narration" class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span class="text-[10px] font-bold uppercase text-slate-500">Texto Integral da Narração:</span>
            <p class="text-xs text-slate-300 leading-relaxed whitespace-pre-line">{{ selectedDarkScript.full_narration }}</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="pt-3 border-t border-slate-800 flex items-center justify-between shrink-0">
          <div class="flex items-center space-x-2">
            <router-link
              to="/approvals"
              class="px-4 py-2 text-xs font-bold rounded-xl bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 transition flex items-center space-x-1.5"
            >
              <span>⚖️</span>
              <span>Revisar na Fila de Supervisão</span>
            </router-link>
          </div>
          <button
            @click="selectedDarkScript = null"
            class="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL DETALHADO DA TAREFA (COMPONENTE COMPARTILHADO) -->
    <TaskDetailModal
      :is-open="showTaskDetailModal"
      :task="selectedTaskForDetail"
      :is-executing="executingTaskId === selectedTaskForDetail?.id"
      @close="showTaskDetailModal = false"
      @execute="handleExecuteTask"
      @move="(task, status) => { handleMoveTask(task, status); showTaskDetailModal = false; }"
      @delete="(task) => { handleDeleteTask(task); }"
    />

    <!-- Drawer de Chat Contextualizado neste Negócio -->
    <AgentChatDrawer
      :is-open="isChatDrawerOpen"
      :business-id="Number(businessId)"
      @close="isChatDrawerOpen = false"
    />
  </AppLayout>
</template>

