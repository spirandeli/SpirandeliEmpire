<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import TaskDetailModal from '@/components/TaskDetailModal.vue'
import { useTaskStore } from '@/stores/tasks'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'
import { groupKanbanTasks } from '@/utils/scriptGrouping'

const taskStore = useTaskStore()
const businessStore = useBusinessStore()
const swal = useSwal()

const selectedBusinessId = ref('')
const selectedAssignee = ref('')
const showCreateModal = ref(false)
const showLogsDrawer = ref(false)
const isCreatingTask = ref(false)
const activeMobileCol = ref('all')
const executingTaskId = ref(null)
const selectedTaskForDetail = ref(null)
const showDetailModal = ref(false)
const groupTasksByProject = ref(true)
const expandedTaskGroups = ref(new Set())

function toggleTaskGroup(groupKey) {
  if (expandedTaskGroups.value.has(groupKey)) {
    expandedTaskGroups.value.delete(groupKey)
  } else {
    expandedTaskGroups.value.add(groupKey)
  }
}

function isTaskGroupExpanded(groupKey) {
  return expandedTaskGroups.value.has(groupKey)
}

function getColumnTasks(col) {
  if (!col?.tasks) return []
  if (!groupTasksByProject.value) return col.tasks
  return groupKanbanTasks(col.tasks)
}

const newTask = ref({
  business_id: '',
  title: '',
  description: '',
  priority: 'medium',
  assignee: 'agent',
})

onMounted(async () => {
  await Promise.all([
    businessStore.fetchBusinesses(),
    loadBoard(),
  ])
  // Inicia o polling incremental de logs do agente
  taskStore.startLogPolling(null, 3000)
})

onUnmounted(() => {
  taskStore.stopLogPolling()
})

async function loadBoard() {
  const params = {}
  if (selectedBusinessId.value) params.business_id = selectedBusinessId.value
  if (selectedAssignee.value) params.assignee = selectedAssignee.value
  await taskStore.fetchBoard(params)
}

function handleFilterChange() {
  loadBoard()
}

async function handleCreateTask() {
  if (!newTask.value.title.trim()) {
    swal.error('Campo obrigatório', 'Por favor, informe o título da tarefa.')
    return
  }

  let bizId = newTask.value.business_id
  if (!bizId) {
    if (businessStore.businesses.length > 0) {
      bizId = businessStore.businesses[0].id
    } else {
      swal.error('Venture obrigatório', 'Crie um negócio primeiro no Hub de Negócios para associar tarefas.')
      return
    }
  }

  isCreatingTask.value = true
  try {
    await taskStore.createTask({
      business_id: Number(bizId),
      title: newTask.value.title.trim(),
      description: newTask.value.description,
      priority: newTask.value.priority,
      assignee: newTask.value.assignee,
    })
    swal.toast('Tarefa criada com sucesso!', 'success')
    showCreateModal.value = false
    newTask.value = {
      business_id: '',
      title: '',
      description: '',
      priority: 'medium',
      assignee: 'agent',
    }
    await loadBoard()
  } catch (err) {
    swal.error('Erro ao criar tarefa', err.response?.data?.message || err.message)
  } finally {
    isCreatingTask.value = false
  }
}

async function handleMove(task, targetStatus) {
  try {
    await taskStore.moveTask(task.id, targetStatus)
    swal.toast(`Tarefa movida para "${targetStatus}"`, 'info')
    await loadBoard()
  } catch (err) {
    swal.error('Movimento não permitido', err.response?.data?.message || err.message)
    await loadBoard()
  }
}

async function handleExecuteTask(task) {
  executingTaskId.value = task.id
  try {
    const res = await api.post(`/tasks/${task.id}/execute`)
    swal.toast(res.data?.message || 'Tarefa executada com sucesso pelo IA Worker!', 'success')
    await loadBoard()
    if (selectedTaskForDetail.value && selectedTaskForDetail.value.id === task.id) {
      const allTasks = taskStore.boardColumns.flatMap((c) => c.tasks || [])
      const updated = allTasks.find((t) => t.id === task.id)
      if (updated) selectedTaskForDetail.value = updated
    }
  } catch (err) {
    swal.error('Erro ao executar tarefa', err.response?.data?.detail || err.message)
    await loadBoard()
  } finally {
    executingTaskId.value = null
  }
}

function openTaskDetail(task) {
  selectedTaskForDetail.value = task
  showDetailModal.value = true
}

function copyText(text) {
  if (!text) return
  navigator.clipboard.writeText(text)
  swal.toast('Copiado para a área de transferência!', 'success')
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
    await taskStore.deleteTask(task.id)
    swal.toast('Tarefa excluída.', 'info')
    await loadBoard()
  } catch (err) {
    swal.error('Erro ao excluir tarefa', err.response?.data?.message || err.message)
  }
}

function getColumnTitle(status) {
  switch (status) {
    case 'backlog':
      return '1. Backlog Geral'
    case 'in_progress_agent':
      return '2. IA Worker (Gemini 3.8)'
    case 'awaiting_supervision':
      return '3. Supervisão (Revisar)'
    case 'todo_user':
      return '4. A Fazer (Humano)'
    case 'done':
    case 'completed':
      return '5. Concluído'
    default:
      return status
  }
}

function getColumnBadgeColor(status) {
  switch (status) {
    case 'backlog':
      return 'bg-slate-800 text-slate-300 border-slate-700'
    case 'in_progress_agent':
      return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
    case 'awaiting_supervision':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/30'
    case 'todo_user':
      return 'bg-sky-500/20 text-sky-300 border-sky-500/30'
    case 'done':
    case 'completed':
      return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
    default:
      return 'bg-slate-800 text-slate-300'
  }
}

function getTaskVideoProgress(task) {
  if (!task) return null

  const p = task.payload?.video_progress
  const hasRealVideo = Boolean(
    task.result?.video_url ||
    task.result?.media?.video?.url ||
    (p && p.stage === 'done' && !task.result?.media_error)
  )

  if (task.result?.media_error || p?.stage === 'failed') {
    return {
      percent: 0,
      statusText: task.status_log || task.failure_reason || `Erro na mídia: ${task.result?.media_error || 'Falha FFmpeg'}`,
      stage: 'failed',
      isCompleted: false,
      isRunning: false,
      isFailed: true,
    }
  }

  // 1. Do payload estruturado
  if (p && typeof p.percent === 'number') {
    const pct = Math.min(100, Math.max(0, p.percent))
    const isCompleted = (pct >= 100 && hasRealVideo) || p.stage === 'done'
    return {
      percent: pct,
      statusText: p.status_log || p.status_text || (isCompleted ? 'Concluído. Arquivo salvo em /app/storage/output/ (100%)' : 'Processando vídeo na VPS...'),
      stage: p.stage || (isCompleted ? 'done' : 'running'),
      isCompleted,
      isRunning: !isCompleted && (task.status === 'in_progress_agent' || task.status === 'in_progress' || (p.stage && p.stage !== 'pending')),
    }
  }

  // 2. Extrai da descrição ou status_log (ex: "Gerando imagens (Cena 5/20)... (25%)")
  const fullText = `${task.status_log || ''} \n ${task.description || ''}`
  const match = fullText.match(/(Iniciando[^\n\(\)]+|Gerando[^\n\(\)]+|Renderizando[^\n\(\)]+|Concluído[^\n\(\)]+|Processando[^\n\(\)]+)\s*\((?:(\d+(?:\.\d+)?)%)\)/i)
  if (match) {
    const rawStage = match[1].trim()
    const pct = parseFloat(match[2])
    const isCompleted = (pct >= 100 || rawStage.toLowerCase().includes('concluído')) && !task.result?.media_error
    return {
      percent: Math.min(100, Math.max(0, pct)),
      statusText: `${rawStage} (${Math.round(pct)}%)`,
      stage: isCompleted ? 'done' : 'running',
      isCompleted,
      isRunning: !isCompleted && (task.status === 'in_progress_agent' || task.status === 'in_progress'),
    }
  }

  // 3. Fallback para tarefas de vídeo em andamento
  const isVideo = (task.title + ' ' + (task.description || '')).toLowerCase().includes('vídeo') ||
                  (task.title + ' ' + (task.description || '')).toLowerCase().includes('video')
  if (isVideo) {
    if ((task.status === 'done' || task.status === 'completed') && hasRealVideo) {
      return {
        percent: 100,
        statusText: 'Concluído. Arquivo salvo em /app/storage/output/ (100%)',
        stage: 'done',
        isCompleted: true,
        isRunning: false,
      }
    }
    if (task.status === 'in_progress_agent' || task.status === 'in_progress') {
      return {
        percent: 25,
        statusText: 'Gerando imagens na VPS (Cena 5/20)... (25%)',
        stage: 'running',
        isCompleted: false,
        isRunning: true,
      }
    }
  }

  return null
}

const isDispatchingSeries = ref(false)

async function handleDispatchSeries() {
  const bizId = selectedBusinessId.value || (businessStore.businesses[0]?.id)
  if (!bizId) {
    swal.warning('Venture obrigatório', 'Selecione ou crie um negócio para associar as tarefas da série.')
    return
  }

  const confirmed = await swal.confirm({
    title: 'Iniciar Série 01 - A Queda de Lúcifer?',
    text: 'O ABVOS criará automaticamente 3 tarefas no Kanban:\n1. [Vídeo] Série 01 - Parte 1\n2. [Vídeo] Série 01 - Parte 2\n3. [Vídeo] Série 01 - Parte 3',
    confirmText: 'Sim, criar 3 tarefas no Kanban',
    confirmButtonColor: '#10b981',
  })

  if (!confirmed) return

  isDispatchingSeries.value = true
  try {
    const res = await api.post('/v1/storage/series/dispatch', {
      business_id: Number(bizId),
      series_title: 'Série 01 - A Queda de Lúcifer',
      parts_count: 3,
      auto_execute_part_1: false,
    })
    swal.toast(res.data.message || 'Tarefas da série criadas com sucesso no Kanban!', 'success')
    await loadBoard()
  } catch (err) {
    swal.error('Erro ao despachar série', err.response?.data?.detail || err.message)
  } finally {
    isDispatchingSeries.value = false
  }
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full gap-3">
        <div class="hidden sm:block">
          <h1 class="text-lg sm:text-xl font-bold text-white tracking-tight">Quadro Operacional & Tarefas (Kanban)</h1>
          <p class="text-xs text-slate-400 mt-0.5">Distribuição Híbrida: Tarefas do Agente Autônomo vs. Ações Humanas</p>
        </div>
        <div class="flex items-center space-x-2">
          <!-- Botão Disparar Série -->
          <button
            @click="handleDispatchSeries"
            :disabled="isDispatchingSeries"
            class="w-full sm:w-auto px-3.5 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/20 transition flex items-center justify-center space-x-1.5 min-h-[44px] disabled:opacity-50"
            title="Criar automaticamente as 3 tarefas no Kanban para Série 01 - A Queda de Lúcifer"
          >
            <span>🎬</span>
            <span>{{ isDispatchingSeries ? 'Criando Série...' : 'Iniciar Série (Partes 1, 2 e 3)' }}</span>
          </button>

          <!-- Botão Nova Tarefa -->
          <button
            @click="showCreateModal = true"
            class="w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-lg shadow-emerald-400/20 transition flex items-center justify-center space-x-1.5 min-h-[44px]"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Nova Tarefa</span>
          </button>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Filtros Responsivos -->
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:items-center gap-3 w-full">
          <!-- Filtro por Negócio -->
          <div class="flex-1">
            <label class="block text-[11px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              Venture:
            </label>
            <select
              v-model="selectedBusinessId"
              @change="handleFilterChange"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500 min-h-[42px]"
            >
              <option value="">Todos os Negócios</option>
              <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
                {{ b.name }}
              </option>
            </select>
          </div>

          <!-- Filtro por Atribuído a -->
          <div class="flex-1">
            <label class="block text-[11px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
              Executor:
            </label>
            <select
              v-model="selectedAssignee"
              @change="handleFilterChange"
              class="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500 min-h-[42px]"
            >
              <option value="">Todos (IA + Humano)</option>
              <option value="agent">Agente (Gemini 3.8)</option>
              <option value="user">Humano (Você)</option>
            </select>
          </div>
        </div>

        <!-- Ações e Toggles de Visualização -->
        <div class="pt-1 flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2">
          <!-- Toggle Agrupamento de Tarefas por Projeto/Série -->
          <button
            type="button"
            @click="groupTasksByProject = !groupTasksByProject"
            class="w-full sm:w-auto px-3.5 py-2 text-xs font-semibold rounded-xl border transition flex items-center justify-center space-x-2 min-h-[42px]"
            :class="groupTasksByProject
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'"
            title="Agrupar tarefas que pertencem ao mesmo vídeo ou projeto"
          >
            <span>{{ groupTasksByProject ? '🎬 Agrupado por Vídeo/Série' : '📄 Todas as Tarefas (Avulsas)' }}</span>
          </button>

          <!-- Toggle do Drawer de Logs -->
          <button
            @click="showLogsDrawer = !showLogsDrawer"
            class="w-full sm:w-auto px-3.5 py-2 text-xs font-semibold rounded-xl border transition flex items-center justify-center space-x-2 min-h-[42px]"
            :class="showLogsDrawer
              ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300'
              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'"
          >
            <span class="w-2 h-2 rounded-full" :class="taskStore.isPollingLogs ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'"></span>
            <span>{{ showLogsDrawer ? 'Ocultar Terminal de Logs da IA' : 'Ver Terminal de Logs da IA' }}</span>
          </button>
        </div>
      </div>

      <!-- Mobile Column Selector (Dropdown Nativo para evitar abas cortadas) -->
      <div class="md:hidden space-y-1.5">
        <div class="flex items-center justify-between">
          <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Coluna do Quadro:
          </label>
          <span class="text-[11px] font-mono text-emerald-400 font-semibold">
            {{ activeMobileCol === 'all' ? '5 Colunas' : getColumnTitle(activeMobileCol) }}
          </span>
        </div>
        <div class="relative">
          <select
            v-model="activeMobileCol"
            class="w-full appearance-none px-4 py-3 bg-slate-900 border border-slate-700 rounded-2xl text-sm font-semibold text-white focus:outline-none focus:border-emerald-500 shadow-md pr-10 min-h-[48px]"
          >
            <option value="all">⚡ Todas as Colunas (Visão Completa)</option>
            <option
              v-for="col in taskStore.boardColumns"
              :key="col.status"
              :value="col.status"
            >
              {{ getColumnTitle(col.status) }} ({{ col.count || col.tasks?.length || 0 }} tarefas)
            </option>
          </select>
          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-emerald-400">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Kanban Board (5 Colunas) -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 items-start">
        <div
          v-for="col in taskStore.boardColumns"
          :key="col.status"
          class="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col min-h-[450px]"
          :class="{'hidden md:flex': activeMobileCol !== 'all' && activeMobileCol !== col.status}"
        >
          <!-- Cabeçalho da Coluna -->
          <div class="p-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-bold text-white tracking-wide">
                {{ getColumnTitle(col.status) }}
              </span>
            </div>
            <span
              class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
              :class="getColumnBadgeColor(col.status)"
            >
              {{ col.count || col.tasks?.length || 0 }}
            </span>
          </div>

          <!-- Lista de Tarefas -->
          <div class="p-3 space-y-3 flex-1 overflow-y-auto">
            <div
              v-if="!col.tasks || col.tasks.length === 0"
              class="h-32 flex items-center justify-center text-[11px] text-slate-500 border border-dashed border-slate-800/80 rounded-xl"
            >
              Nenhuma tarefa
            </div>

            <!-- Iteração sobre Tarefas (Agrupadas ou Individuais) -->
            <template v-for="task in getColumnTasks(col)" :key="task.id">
              <!-- CASO 1: Card Mestre de Tarefas Agrupadas (Série/Vídeo/Projeto) -->
              <div
                v-if="task.isGroup"
                class="p-3.5 rounded-xl bg-slate-950 border border-indigo-500/40 hover:border-indigo-500/80 transition space-y-2.5 shadow-md shadow-indigo-950/20 group"
              >
                <!-- Top Tags do Grupo -->
                <div class="flex items-center justify-between text-[10px]">
                  <span class="font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1">
                    <span>🎬</span>
                    <span>PRODUÇÃO / SÉRIE</span>
                  </span>
                  <span
                    class="font-bold uppercase"
                    :class="{
                      'text-rose-400': task.priority === 'urgent' || task.priority === 'high',
                      'text-amber-400': task.priority === 'medium',
                      'text-slate-400': task.priority === 'low'
                    }"
                  >
                    {{ task.priority }}
                  </span>
                </div>

                <!-- Título do Grupo -->
                <div>
                  <h4 class="text-xs font-black text-white group-hover:text-indigo-300 transition leading-snug">
                    {{ task.title }}
                  </h4>
                  <div v-if="task.business" class="text-[10px] text-slate-500 truncate mt-0.5">
                    Venture: <strong class="text-slate-400">{{ task.business.name }}</strong>
                  </div>
                </div>

                <!-- Resumo & Barra de Progresso de Cenas -->
                <div class="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                  <div class="flex items-center justify-between text-[10px]">
                    <span class="text-slate-400 font-semibold">{{ task.subtasks.length }} subtarefas / cenas</span>
                    <span class="font-mono font-bold text-indigo-300">{{ task.completedCount }}/{{ task.totalCount }}</span>
                  </div>
                  <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                    <div
                      class="bg-gradient-to-r from-indigo-500 to-emerald-400 h-1.5 rounded-full transition-all duration-300"
                      :style="{ width: `${task.progressPercent}%` }"
                    ></div>
                  </div>
                </div>

                <!-- Botão Toggle de Subtarefas -->
                <button
                  type="button"
                  @click.stop="toggleTaskGroup(task.groupKey)"
                  class="w-full px-2.5 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-900 border border-slate-800 flex items-center justify-between text-[11px] text-slate-300 transition"
                >
                  <span class="flex items-center space-x-1.5">
                    <span class="text-indigo-400">🎞️</span>
                    <span>{{ isTaskGroupExpanded(task.groupKey) ? 'Ocultar Cenas' : `Ver ${task.subtasks.length} Cenas da Série` }}</span>
                  </span>
                  <svg
                    class="w-3.5 h-3.5 transition-transform duration-200"
                    :class="{'rotate-180': isTaskGroupExpanded(task.groupKey)}"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <!-- Subtarefas Expandidas -->
                <div v-if="isTaskGroupExpanded(task.groupKey)" class="space-y-2 pt-1">
                  <div
                    v-for="sub in task.subtasks"
                    :key="sub.id"
                    @click="openTaskDetail(sub)"
                    class="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-850 cursor-pointer transition space-y-1.5"
                  >
                    <div class="flex items-center justify-between text-[10px]">
                      <span class="font-mono text-indigo-300 font-bold">
                        Cena #{{ sub.parsedSceneNumber || '•' }}
                      </span>
                      <span
                        class="px-1.5 py-0.2 rounded font-semibold text-[9px] uppercase"
                        :class="sub.assignee === 'agent' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-sky-500/10 text-sky-400'"
                      >
                        {{ sub.assignee === 'agent' ? '🤖 IA' : '👤 Humano' }}
                      </span>
                    </div>

                    <h5 class="text-[11px] font-bold text-slate-200 line-clamp-1">
                      {{ sub.parsedSceneTitle || sub.title }}
                    </h5>

                    <!-- Barra de Progresso da Subtarefa/Cena -->
                    <div v-if="getTaskVideoProgress(sub)" class="space-y-1 pt-0.5">
                      <div class="flex items-center justify-between text-[9px]">
                        <span class="text-slate-400 truncate max-w-[150px]">{{ getTaskVideoProgress(sub).statusText }}</span>
                        <span class="font-mono font-bold text-indigo-300">{{ Math.round(getTaskVideoProgress(sub).percent) }}%</span>
                      </div>
                      <div class="w-full bg-slate-950 rounded-full h-1 overflow-hidden">
                        <div
                          class="h-1 rounded-full transition-all duration-300"
                          :class="getTaskVideoProgress(sub).isCompleted ? 'bg-emerald-400' : 'bg-indigo-500 animate-pulse'"
                          :style="{ width: `${getTaskVideoProgress(sub).percent}%` }"
                        ></div>
                      </div>
                    </div>

                    <!-- Ações da Subtarefa -->
                    <div class="pt-1.5 border-t border-slate-950 flex items-center justify-between text-[10px]" @click.stop>
                      <div class="flex items-center space-x-1">
                        <button
                          v-if="col.status !== 'backlog'"
                          @click.stop="handleMove(sub, (col.status === 'done' || col.status === 'completed') ? 'awaiting_supervision' : col.status === 'todo_user' ? 'in_progress_agent' : col.status === 'awaiting_supervision' ? 'in_progress_agent' : 'backlog')"
                          title="Mover para trás"
                          class="p-1 rounded bg-slate-950 hover:bg-slate-800 text-slate-400"
                        >
                          &larr;
                        </button>
                        <button
                          v-if="col.status !== 'done' && col.status !== 'completed'"
                          @click.stop="handleMove(sub, col.status === 'backlog' ? (sub.assignee === 'agent' ? 'in_progress_agent' : 'todo_user') : col.status === 'in_progress_agent' ? 'awaiting_supervision' : 'done')"
                          title="Avançar etapa"
                          class="p-1 rounded bg-slate-950 hover:bg-slate-800 text-emerald-400 font-bold"
                        >
                          &rarr;
                        </button>
                      </div>

                      <button
                        v-if="sub.assignee === 'agent' && sub.status !== 'done'"
                        @click.stop="handleExecuteTask(sub)"
                        :disabled="executingTaskId === sub.id"
                        class="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-semibold flex items-center space-x-1 transition disabled:opacity-50"
                      >
                        <span v-if="executingTaskId === sub.id" class="animate-spin">⏳</span>
                        <span v-else>⚡</span>
                        <span>Executar</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- CASO 2: Card de Tarefa Individual Normal (Clicável) -->
              <div
                v-else
                @click="openTaskDetail(task)"
                class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/40 cursor-pointer transition space-y-2.5 shadow-sm group"
              >
              <!-- Tags de Topo -->
              <div class="flex items-center justify-between text-[10px]">
                <span
                  class="font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
                  :class="task.assignee === 'agent' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-sky-500/10 text-sky-400'"
                >
                  {{ task.assignee === 'agent' ? '🤖 Gemini IA' : '👤 Humano' }}
                </span>
                <span
                  class="font-bold uppercase"
                  :class="{
                    'text-rose-400': task.priority === 'urgent' || task.priority === 'high',
                    'text-amber-400': task.priority === 'medium',
                    'text-slate-400': task.priority === 'low'
                  }"
                >
                  {{ task.priority }}
                </span>
              </div>

              <!-- Título & Descrição -->
              <h4 class="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition leading-snug">
                {{ task.title }}
              </h4>
              <p v-if="task.description" class="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                {{ task.description }}
              </p>

              <!-- Negócio Vinculado -->
              <div v-if="task.business" class="text-[10px] text-slate-500 truncate">
                Venture: <strong class="text-slate-400">{{ task.business.name }}</strong>
              </div>

              <!-- BARRA DE PROGRESSO DINÂMICA DE VÍDEO (PIPELINE ABVOS) -->
              <div
                v-if="getTaskVideoProgress(task)"
                class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2"
              >
                <div class="flex items-center justify-between text-[10px]">
                  <span class="flex items-center space-x-1.5 font-bold text-slate-300">
                    <span v-if="getTaskVideoProgress(task).isRunning" class="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
                    <span v-else-if="getTaskVideoProgress(task).isCompleted" class="text-emerald-400">✓</span>
                    <span v-else class="text-slate-500">🎬</span>
                    <span class="truncate max-w-[170px]" :title="getTaskVideoProgress(task).statusText">
                      {{ getTaskVideoProgress(task).statusText }}
                    </span>
                  </span>
                  <span
                    class="font-mono font-bold px-1.5 py-0.2 rounded text-[10px]"
                    :class="getTaskVideoProgress(task).isCompleted ? 'bg-emerald-500/20 text-emerald-300' : 'bg-indigo-500/20 text-indigo-300'"
                  >
                    {{ Math.round(getTaskVideoProgress(task).percent) }}%
                  </span>
                </div>

                <!-- Barra com gradiente dinâmico -->
                <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden p-0.5 border border-slate-800">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    :class="getTaskVideoProgress(task).isCompleted
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-sm shadow-emerald-500/30'
                      : 'bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 animate-pulse'"
                    :style="{ width: `${getTaskVideoProgress(task).percent}%` }"
                  ></div>
                </div>

                <!-- Ação Rápida quando Concluído (100%): Assistir na Galeria -->
                <div v-if="getTaskVideoProgress(task).isCompleted" class="pt-1 flex items-center justify-between text-[10px]">
                  <span class="text-emerald-400 font-semibold flex items-center space-x-1">
                    <span>Pronto em</span>
                    <code class="text-[9px] bg-slate-950 px-1 py-0.5 rounded text-slate-300">/app/storage/output</code>
                  </span>
                  <RouterLink
                    to="/storage-viewer"
                    class="text-indigo-400 hover:text-indigo-300 font-bold underline decoration-dotted flex items-center space-x-1"
                    @click.stop
                  >
                    <span>Ver Vídeo</span>
                    <span>&rarr;</span>
                  </RouterLink>
                </div>
              </div>

              <!-- Indicadores Visuais de Entregável & Status -->
              <div v-if="task.result || task.failure_reason" class="flex flex-wrap items-center gap-1.5 pt-0.5">
                <span
                  v-if="task.result?.video_url || task.result?.media?.video?.url"
                  class="px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>🎬</span>
                  <span>Vídeo 9:16</span>
                </span>

                <span
                  v-else-if="task.result"
                  class="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>📄</span>
                  <span>Entregável Pronto</span>
                </span>

                <span
                  v-if="task.failure_reason"
                  class="px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-semibold flex items-center space-x-1"
                >
                  <span>⚠️</span>
                  <span>Falha</span>
                </span>
              </div>

              <!-- Controles Rápidos de Movimentação & Execução -->
              <div class="pt-2 border-t border-slate-900 flex items-center justify-between text-[11px]" @click.stop>
                <div class="flex items-center space-x-1">
                  <!-- Mover para Trás -->
                  <button
                    v-if="col.status !== 'backlog'"
                    @click.stop="handleMove(task, (col.status === 'done' || col.status === 'completed') ? 'awaiting_supervision' : col.status === 'todo_user' ? 'in_progress_agent' : col.status === 'awaiting_supervision' ? 'in_progress_agent' : 'backlog')"
                    title="Mover para coluna anterior"
                    class="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                  >
                    &larr;
                  </button>
                  <!-- Mover para Frente -->
                  <button
                    v-if="col.status !== 'done' && col.status !== 'completed'"
                    @click.stop="handleMove(task, col.status === 'backlog' ? (task.assignee === 'agent' ? 'in_progress_agent' : 'todo_user') : col.status === 'in_progress_agent' ? 'awaiting_supervision' : 'done')"
                    title="Avançar etapa"
                    class="p-1 rounded bg-slate-900 hover:bg-slate-800 text-emerald-400 font-bold"
                  >
                    &rarr;
                  </button>
                </div>

                <div class="flex items-center space-x-1.5">
                  <button
                    v-if="task.assignee === 'agent' && task.status !== 'done'"
                    @click.stop="handleExecuteTask(task)"
                    :disabled="executingTaskId === task.id"
                    class="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-semibold flex items-center space-x-1 transition shadow-sm disabled:opacity-50"
                    :title="task.result ? 'Reexecutar tarefa com IA' : 'Executar tarefa com IA Worker'"
                  >
                    <span v-if="executingTaskId === task.id" class="animate-spin">⏳</span>
                    <span v-else>⚡</span>
                    <span>{{ executingTaskId === task.id ? 'Gerando...' : (task.result ? 'Reexecutar' : 'Executar') }}</span>
                  </button>

                  <button
                    @click.stop="handleDeleteTask(task)"
                    class="text-slate-600 hover:text-rose-400 text-[10px] transition px-1"
                    title="Excluir"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Console de Logs do Agente em Tempo Real (Terminal Dark) -->
      <div v-if="showLogsDrawer" class="rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden shadow-2xl">
        <div class="p-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="flex space-x-1.5">
              <span class="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
            </div>
            <span class="text-xs font-mono font-bold text-slate-200">Terminal de Execução Autônoma · Logs do Gemini 3.8</span>
          </div>

          <div class="flex items-center space-x-3 text-xs">
            <span class="text-slate-400 text-[11px] font-mono">
              {{ taskStore.agentLogs.length }} eventos registrados
            </span>
            <button
              @click="taskStore.isPollingLogs ? taskStore.stopLogPolling() : taskStore.startLogPolling(null, 3000)"
              class="px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider border transition"
              :class="taskStore.isPollingLogs
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'"
            >
              {{ taskStore.isPollingLogs ? '● Live Polling ON' : '○ Polling Pausado' }}
            </button>
          </div>
        </div>

        <div class="p-4 font-mono text-[11px] leading-relaxed max-h-60 overflow-y-auto space-y-1.5 bg-slate-950 text-slate-300">
          <div v-if="taskStore.agentLogs.length === 0" class="text-slate-500 italic">
            Nenhum evento registrado ainda. Quando o Gemini 3.8 executar chamadas de ferramentas (Tools) ou rotinas de mineração, os logs aparecerão aqui ao vivo.
          </div>
          <div
            v-for="log in taskStore.agentLogs"
            :key="log.id"
            class="flex items-start space-x-2 hover:bg-slate-900/60 p-1 rounded transition"
          >
            <span class="text-slate-500 shrink-0">[{{ new Date(log.created_at).toLocaleTimeString() }}]</span>
            <span
              class="px-1 rounded text-[10px] font-bold uppercase shrink-0"
              :class="{
                'bg-emerald-500/20 text-emerald-300': log.level === 'info',
                'bg-indigo-500/20 text-indigo-300': log.level === 'action' || log.action?.includes('tool'),
                'bg-amber-500/20 text-amber-300': log.level === 'warning',
                'bg-rose-500/20 text-rose-300': log.level === 'error'
              }"
            >
              {{ log.level }}
            </span>
            <span class="text-slate-300">{{ log.message }}</span>
            <span v-if="log.action" class="text-indigo-400 font-semibold shrink-0">({{ log.action }})</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Nova Tarefa (Bottom Sheet no Mobile) -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
    >
      <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-2xl shadow-2xl p-5 sm:p-6 space-y-4 max-h-[90dvh] overflow-y-auto safe-bottom">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div class="flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <h3 class="text-base font-bold text-white">Nova Tarefa Operacional</h3>
          </div>
          <button @click="showCreateModal = false" class="text-slate-400 hover:text-white p-2 min-h-[44px] min-w-[44px] flex items-center justify-center">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="handleCreateTask" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Título da Tarefa</label>
            <input
              v-model="newTask.title"
              type="text"
              required
              placeholder="Ex: Gravar vídeo do produto vencedor X"
              class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Venture / Negócio</label>
            <select
              v-model="newTask.business_id"
              class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            >
              <option value="">Selecione o negócio (ou padrão do venture ativo)</option>
              <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
                {{ b.name }}
              </option>
            </select>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Atribuído a (Executor)</label>
              <select
                v-model="newTask.assignee"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="agent">🤖 Agente (Gemini 3.8)</option>
                <option value="user">👤 Humano (Você)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Prioridade</label>
              <select
                v-model="newTask.priority"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="low">Baixa</option>
                <option value="medium">Média</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Descrição / Instruções</label>
            <textarea
              v-model="newTask.description"
              rows="3"
              placeholder="Instruções específicas para execução..."
              class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            ></textarea>
          </div>

          <div class="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2.5 text-xs font-semibold text-slate-400 hover:text-white min-h-[44px]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              :disabled="isCreatingTask"
              class="px-5 py-2.5 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-xl transition shadow-md shadow-emerald-400/20 disabled:opacity-50 flex items-center space-x-1.5 min-h-[44px]"
            >
              <span v-if="isCreatingTask" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
              <span>{{ isCreatingTask ? 'Criando...' : 'Criar Tarefa' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL DETALHADO DA TAREFA (COMPONENTE COMPARTILHADO) -->
    <TaskDetailModal
      :is-open="showDetailModal"
      :task="selectedTaskForDetail"
      :is-executing="executingTaskId === selectedTaskForDetail?.id"
      @close="showDetailModal = false"
      @execute="handleExecuteTask"
      @move="(task, status) => { handleMove(task, status); showDetailModal = false; }"
      @delete="(task) => { handleDeleteTask(task); showDetailModal = false; }"
    />
  </AppLayout>
</template>

