<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Administração & Monitoramento da VPS
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
            Ubuntu 24.04 LTS
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Telemetria do servidor em tempo real, governança de containers Docker e inspeção de logs
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="fetchVpsData"
          :disabled="loading"
          class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{'animate-spin': loading}">↻</span> Atualizar
        </button>
        <a
          href="/kuma"
          target="_blank"
          class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 rounded-xl text-xs font-mono transition flex items-center space-x-2"
        >
          <span>Abrir Uptime Kuma ↗</span>
        </a>
      </div>
    </div>

    <!-- Live Telemetry -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- CPU -->
      <div class="bg-slate-900/90 p-5 rounded-xl border border-slate-800 shadow-xl">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Processador (CPU)</span>
          <span class="text-xs font-mono text-emerald-400 font-bold">{{ telemetry.cpu_percent || 0 }}%</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div
            class="bg-emerald-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: Math.min(100, telemetry.cpu_percent || 0) + '%' }"
          ></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">
          SO: {{ telemetry.os || 'Linux' }} • PHP: {{ telemetry.php_version || '8.3' }}
        </span>
      </div>

      <!-- RAM -->
      <div class="bg-slate-900/90 p-5 rounded-xl border border-slate-800 shadow-xl">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Memória RAM</span>
          <span class="text-xs font-mono text-cyan-400 font-bold">
            {{ telemetry.memory?.used_gb || 0 }} GB / {{ telemetry.memory?.total_gb || 0 }} GB ({{ telemetry.memory?.percentage || 0 }}%)
          </span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div
            class="bg-cyan-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: Math.min(100, telemetry.memory?.percentage || 0) + '%' }"
          ></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">
          Livre: {{ telemetry.memory?.free_gb || 0 }} GB disponível
        </span>
      </div>

      <!-- SSD -->
      <div class="bg-slate-900/90 p-5 rounded-xl border border-slate-800 shadow-xl">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Armazenamento (SSD)</span>
          <span class="text-xs font-mono text-amber-400 font-bold">
            {{ telemetry.disk?.used_gb || 0 }} GB / {{ telemetry.disk?.total_gb || 0 }} GB ({{ telemetry.disk?.percentage || 0 }}%)
          </span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div
            class="bg-amber-500 h-2 rounded-full transition-all duration-500"
            :style="{ width: Math.min(100, telemetry.disk?.percentage || 0) + '%' }"
          ></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">
          Espaço Livre: {{ telemetry.disk?.free_gb || 0 }} GB
        </span>
      </div>
    </div>

    <!-- Container Grid (Real from Docker API) -->
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-bold text-slate-200 uppercase font-mono">
          Containers Docker em Execução ({{ containers.length }})
        </h3>
        <span class="text-xs font-mono text-emerald-400">
          ● Todos os serviços monitorados
        </span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
        <div
          v-for="c in containers"
          :key="c.id || c.name"
          class="p-3.5 bg-slate-950/70 rounded-xl border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition"
        >
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-bold text-slate-200 truncate">{{ c.name }}</span>
              <span
                class="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase border"
                :class="c.is_running ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-red-950 text-red-400 border-red-800'"
              >
                {{ c.is_running ? 'Ativo' : 'Parado' }}
              </span>
            </div>
            <div class="text-[10px] text-slate-500 truncate">{{ c.image }}</div>
            <div class="text-[9px] text-slate-400 mt-1 truncate">{{ c.status }}</div>
          </div>

          <div class="mt-3 pt-2 border-t border-slate-800/80 flex justify-between items-center text-[10px]">
            <span class="text-slate-500">{{ c.uptime || 'Online' }}</span>
            <button
              @click="openLogs(c.name)"
              class="text-cyan-400 hover:text-cyan-300 underline"
            >
              Ver Logs ↗
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Container Logs Modal -->
    <div v-if="activeLogContainer" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-3xl w-full flex flex-col max-h-[80vh] shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 class="text-xs font-bold text-cyan-400 font-mono">
            Logs Recentes: {{ activeLogContainer }}
          </h3>
          <button
            @click="activeLogContainer = null"
            class="text-slate-500 hover:text-white p-1 text-sm font-bold"
          >
            ✕
          </button>
        </div>

        <div class="flex-1 overflow-y-auto my-4 p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap">
          {{ containerLogsContent || 'Carregando saída do terminal...' }}
        </div>

        <div class="flex justify-end">
          <button
            @click="activeLogContainer = null"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const telemetry = ref({})
const containers = ref([])
const activeLogContainer = ref(null)
const containerLogsContent = ref('')

const fetchVpsData = async () => {
  loading.value = true
  try {
    const [metricsRes, containersRes] = await Promise.all([
      axios.get('/api/v1/vps/metrics'),
      axios.get('/api/v1/vps/containers'),
    ])

    if (metricsRes.data?.telemetry) telemetry.value = metricsRes.data.telemetry
    if (containersRes.data?.containers) containers.value = containersRes.data.containers
  } catch (err) {
    console.error('Falha ao obter telemetria da VPS:', err)
  } finally {
    loading.value = false
  }
}

const openLogs = async (containerName) => {
  activeLogContainer.value = containerName
  containerLogsContent.value = 'Consultando logs do container via Docker API...'
  try {
    const res = await axios.get(`/api/v1/vps/containers/${containerName}/logs`)
    containerLogsContent.value = res.data?.logs || 'Sem logs registrados.'
  } catch (err) {
    containerLogsContent.value = 'Falha ao obter logs: ' + (err.response?.data?.message || err.message)
  }
}

let timer = null
onMounted(() => {
  fetchVpsData()
  timer = setInterval(fetchVpsData, 20000) // 20s auto-refresh
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
