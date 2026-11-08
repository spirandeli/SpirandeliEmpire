<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useTaskStore } from '@/stores/tasks'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'

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
const selectedTaskResult = ref(null)
const showTaskResultModal = ref(false)

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
  } catch (err) {
    swal.error('Erro ao executar tarefa', err.response?.data?.detail || err.message)
  } finally {
    executingTaskId.value = null
  }
}

function viewTaskResult(task) {
  selectedTaskResult.value = task
  showTaskResultModal.value = true
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
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full gap-3">
        <div class="hidden sm:block">
          <h1 class="text-lg sm:text-xl font-bold text-white tracking-tight">Quadro Operacional & Tarefas (Kanban)</h1>
          <p class="text-xs text-slate-400 mt-0.5">Distribuição Híbrida: Tarefas do Agente Autônomo vs. Ações Humanas</p>
        </div>
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

        <!-- Toggle do Drawer de Logs -->
        <div class="pt-1 flex sm:justify-end">
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

            <!-- Card de Tarefa Individual -->
            <div
              v-for="task in col.tasks"
              :key="task.id"
              class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition space-y-2.5 shadow-sm group"
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

              <!-- Ações da IA Worker -->
              <div v-if="task.result || (task.assignee === 'agent' && task.status !== 'done')" class="flex flex-wrap items-center gap-1.5 pt-1">
                <button
                  v-if="task.result"
                  @click="viewTaskResult(task)"
                  class="px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold flex items-center space-x-1 transition"
                  title="Visualizar entregável produzido"
                >
                  <span>📄</span>
                  <span>Ver Entregável</span>
                </button>

                <button
                  v-if="task.assignee === 'agent' && task.status !== 'done'"
                  @click="handleExecuteTask(task)"
                  :disabled="executingTaskId === task.id"
                  class="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-semibold flex items-center space-x-1 transition shadow-sm disabled:opacity-50"
                  :title="task.result ? 'Reexecutar tarefa com IA' : 'Executar tarefa com IA Worker'"
                >
                  <span v-if="executingTaskId === task.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  <span>{{ executingTaskId === task.id ? 'Gerando...' : (task.result ? 'Reexecutar' : 'Executar IA') }}</span>
                </button>
              </div>

              <!-- Controles Rápidos de Movimentação -->
              <div class="pt-2 border-t border-slate-900 flex items-center justify-between text-[11px]">
                <div class="flex items-center space-x-1">
                  <!-- Mover para Trás -->
                  <button
                    v-if="col.status !== 'backlog'"
                    @click="handleMove(task, (col.status === 'done' || col.status === 'completed') ? 'awaiting_supervision' : col.status === 'todo_user' ? 'in_progress_agent' : col.status === 'awaiting_supervision' ? 'in_progress_agent' : 'backlog')"
                    title="Mover para coluna anterior"
                    class="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                  >
                    &larr;
                  </button>
                  <!-- Mover para Frente -->
                  <button
                    v-if="col.status !== 'done' && col.status !== 'completed'"
                    @click="handleMove(task, col.status === 'backlog' ? (task.assignee === 'agent' ? 'in_progress_agent' : 'todo_user') : col.status === 'in_progress_agent' ? 'awaiting_supervision' : 'done')"
                    title="Avançar etapa"
                    class="p-1 rounded bg-slate-900 hover:bg-slate-800 text-emerald-400 font-bold"
                  >
                    &rarr;
                  </button>
                </div>

                <button
                  @click="handleDeleteTask(task)"
                  class="text-slate-600 hover:text-rose-400 text-[10px] transition"
                  title="Excluir"
                >
                  Excluir
                </button>
              </div>
            </div>
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

    <!-- MODAL: Visualizar Entregável da Tarefa -->
    <div
      v-if="showTaskResultModal && selectedTaskResult"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
    >
      <div class="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-4 my-8 max-h-[85vh] flex flex-col">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3 shrink-0">
          <div>
            <span class="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">Entregável do IA Worker (Gemini 3.8)</span>
            <h3 class="text-base font-bold text-white mt-1">{{ selectedTaskResult.title }}</h3>
          </div>
          <button @click="showTaskResultModal = false" class="text-slate-400 hover:text-white p-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto space-y-4 pr-1 text-slate-300 text-xs leading-relaxed">
          <!-- SEÇÃO VÍDEO & MÍDIA RENDERIZADA PELO ABVOS -->
          <div
            v-if="selectedTaskResult.result?.video_url || selectedTaskResult.result?.media?.video?.url"
            class="p-4 rounded-2xl bg-gradient-to-b from-indigo-950/40 to-slate-950 border border-indigo-500/30 space-y-3.5 shadow-xl"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="text-base">🎬</span>
                <span class="text-sm font-bold text-white">Vídeo Vertical 9:16 Renderizado</span>
              </div>
              <div class="flex items-center space-x-1.5 text-[10px] font-mono">
                <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">1080x1920</span>
                <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  {{ selectedTaskResult.result?.media?.video?.duration_seconds || '60' }}s
                </span>
                <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {{ selectedTaskResult.result?.media?.video?.size_mb || '0' }} MB
                </span>
              </div>
            </div>

            <!-- Player de Vídeo 9:16 -->
            <div class="flex justify-center bg-black/60 rounded-xl p-2 border border-slate-800/80">
              <video
                :src="selectedTaskResult.result.video_url || selectedTaskResult.result.media?.video?.url"
                controls
                playsinline
                class="max-h-80 w-auto rounded-lg shadow-2xl border border-slate-700/60"
              ></video>
            </div>

            <!-- Botões de Ação e Download -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <a
                :href="selectedTaskResult.result.video_url || selectedTaskResult.result.media?.video?.url"
                download
                target="_blank"
                class="px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] text-center flex items-center justify-center space-x-1.5 transition shadow-md shadow-emerald-500/20"
              >
                <span>📥</span>
                <span>Baixar Vídeo (.mp4)</span>
              </a>

              <a
                v-if="selectedTaskResult.result.audio_url || selectedTaskResult.result.media?.audio?.url"
                :href="selectedTaskResult.result.audio_url || selectedTaskResult.result.media?.audio?.url"
                download
                target="_blank"
                class="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] text-center flex items-center justify-center space-x-1.5 transition shadow-sm"
              >
                <span>🎙️</span>
                <span>Baixar Áudio (.mp3)</span>
              </a>

              <a
                v-if="selectedTaskResult.result.srt_url || selectedTaskResult.result.media?.subtitles?.srt_url"
                :href="selectedTaskResult.result.srt_url || selectedTaskResult.result.media?.subtitles?.srt_url"
                download
                target="_blank"
                class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-[11px] text-center flex items-center justify-center space-x-1.5 transition border border-slate-700"
              >
                <span>📝</span>
                <span>Legendas (.srt)</span>
              </a>
            </div>

            <!-- Galeria de Imagens de Cenas (se houver) -->
            <div v-if="selectedTaskResult.result?.media?.images_generated?.length" class="pt-2 border-t border-slate-800/80">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">Cenas Visuais Geradas (9:16):</span>
              <div class="flex space-x-2 overflow-x-auto pb-1">
                <a
                  v-for="(imgUrl, iIdx) in selectedTaskResult.result.media.images_generated"
                  :key="iIdx"
                  :href="imgUrl"
                  target="_blank"
                  class="shrink-0 w-16 h-28 rounded-lg overflow-hidden border border-slate-800 hover:border-indigo-500 transition shadow"
                  :title="`Cena ${iIdx + 1}`"
                >
                  <img :src="imgUrl" :alt="`Cena ${iIdx + 1}`" class="w-full h-full object-cover" />
                </a>
              </div>
            </div>
          </div>

          <div v-if="selectedTaskResult.result?.summary" class="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <h4 class="text-slate-400 font-semibold mb-1">Resumo Executivo:</h4>
            <p class="text-slate-200">{{ selectedTaskResult.result.summary }}</p>
          </div>

          <div v-if="selectedTaskResult.result?.markdown_content" class="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono whitespace-pre-wrap">
            {{ selectedTaskResult.result.markdown_content }}
          </div>

          <div v-if="selectedTaskResult.result?.items?.length" class="space-y-3">
            <h4 class="text-sm font-bold text-white">Itens & Cenas Detalhadas:</h4>
            <div
              v-for="(it, idx) in selectedTaskResult.result.items"
              :key="idx"
              class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-2"
            >
              <div class="flex items-center justify-between">
                <strong class="text-white text-xs">{{ idx + 1 }}. {{ it.title }}</strong>
                <span v-if="it.description" class="text-slate-500 text-[10px]">{{ it.description }}</span>
              </div>
              <p v-if="it.script" class="text-slate-200 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 text-[11px]">
                <span class="text-emerald-400 font-semibold block mb-0.5">Narração / TTS:</span>
                {{ it.script }}
              </p>
              <div v-if="it.visual_prompt" class="bg-indigo-950/30 p-2 rounded-lg border border-indigo-500/20 text-[11px] text-indigo-300">
                <div class="flex items-center justify-between mb-1">
                  <span class="font-bold text-[10px] uppercase text-indigo-400">Prompt Visual (Midjourney/Leonardo):</span>
                  <button @click="copyText(it.visual_prompt)" class="text-[10px] text-indigo-300 hover:text-white underline">Copiar Prompt</button>
                </div>
                <code class="font-mono text-[10px] select-all">{{ it.visual_prompt }}</code>
              </div>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-800 flex items-center justify-between shrink-0">
          <button
            @click="copyText(selectedTaskResult.result?.markdown_content || selectedTaskResult.result?.summary)"
            class="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
          >
            📋 Copiar Todo o Conteúdo
          </button>
          <div class="flex items-center space-x-2">
            <button
              v-if="selectedTaskResult.status === 'awaiting_supervision'"
              @click="handleMove(selectedTaskResult, 'done'); showTaskResultModal = false"
              class="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition"
            >
              ✓ Aprovar Entregável
            </button>
            <button
              @click="showTaskResultModal = false"
              class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

