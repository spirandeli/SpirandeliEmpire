<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useTaskStore } from '@/stores/tasks'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'

const taskStore = useTaskStore()
const businessStore = useBusinessStore()
const swal = useSwal()

const selectedBusinessId = ref('')
const selectedAssignee = ref('')
const showCreateModal = ref(false)
const showLogsDrawer = ref(true)

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
  if (!newTask.value.title.trim()) return

  try {
    await taskStore.createTask({
      business_id: newTask.value.business_id || null,
      title: newTask.value.title,
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
      <div class="flex items-center justify-between w-full">
        <div>
          <h1 class="text-xl font-bold text-white tracking-tight">Quadro Operacional & Tarefas (Kanban)</h1>
          <p class="text-xs text-slate-400 mt-0.5">Distribuição Híbrida: Tarefas do Agente Autônomo vs. Ações Humanas</p>
        </div>
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-lg shadow-emerald-400/20 transition flex items-center space-x-1.5"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          <span>Nova Tarefa</span>
        </button>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Filtros -->
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div class="flex flex-wrap items-center gap-3">
          <!-- Filtro por Negócio -->
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400 font-semibold uppercase">Venture:</span>
            <select
              v-model="selectedBusinessId"
              @change="handleFilterChange"
              class="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Todos os Negócios</option>
              <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
                {{ b.name }}
              </option>
            </select>
          </div>

          <!-- Filtro por Atribuído a -->
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400 font-semibold uppercase">Executor:</span>
            <select
              v-model="selectedAssignee"
              @change="handleFilterChange"
              class="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="">Todos (IA + Humano)</option>
              <option value="agent">Agente (Gemini 3.8)</option>
              <option value="user">Humano (Você)</option>
            </select>
          </div>
        </div>

        <!-- Toggle do Drawer de Logs -->
        <button
          @click="showLogsDrawer = !showLogsDrawer"
          class="px-3 py-1.5 text-xs font-semibold rounded-xl border transition flex items-center space-x-2"
          :class="showLogsDrawer
            ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300'
            : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'"
        >
          <span class="w-2 h-2 rounded-full" :class="taskStore.isPollingLogs ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'"></span>
          <span>{{ showLogsDrawer ? 'Ocultar Terminal de Logs da IA' : 'Ver Terminal de Logs da IA' }}</span>
        </button>
      </div>

      <!-- Kanban Board (5 Colunas) -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 items-start">
        <div
          v-for="col in taskStore.boardColumns"
          :key="col.status"
          class="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col min-h-[550px]"
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

              <!-- Controles Rápidos de Movimentação -->
              <div class="pt-2 border-t border-slate-900 flex items-center justify-between text-[11px]">
                <div class="flex items-center space-x-1">
                  <!-- Mover para Trás -->
                  <button
                    v-if="col.status !== 'backlog'"
                    @click="handleMove(task, col.status === 'completed' ? 'awaiting_supervision' : col.status === 'todo_user' ? 'in_progress_agent' : col.status === 'awaiting_supervision' ? 'in_progress_agent' : 'backlog')"
                    title="Mover para coluna anterior"
                    class="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white"
                  >
                    &larr;
                  </button>
                  <!-- Mover para Frente -->
                  <button
                    v-if="col.status !== 'completed'"
                    @click="handleMove(task, col.status === 'backlog' ? (task.assignee === 'agent' ? 'in_progress_agent' : 'todo_user') : col.status === 'in_progress_agent' ? 'awaiting_supervision' : 'completed')"
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

    <!-- Modal Nova Tarefa -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-white">Criar Nova Tarefa Operacional</h3>
          <button @click="showCreateModal = false" class="text-slate-400 hover:text-white">
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
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Venture / Negócio</label>
            <select
              v-model="newTask.business_id"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            >
              <option value="">Sem negócio vinculado (Geral)</option>
              <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
                {{ b.name }}
              </option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Atribuído a (Executor)</label>
              <select
                v-model="newTask.assignee"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="agent">🤖 Agente (Gemini 3.8)</option>
                <option value="user">👤 Humano (Você)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Prioridade</label>
              <select
                v-model="newTask.priority"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
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
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            ></textarea>
          </div>

          <div class="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-xl transition shadow-md shadow-emerald-400/20"
            >
              Criar Tarefa
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

