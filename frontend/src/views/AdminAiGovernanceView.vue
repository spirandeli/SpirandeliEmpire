<script setup>
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'
import Swal from 'sweetalert2'

const authStore = useAuthStore()
const swal = useSwal()

const loading = ref(true)
const stats = ref({
  metrics: {
    monthly_tokens: 0,
    monthly_cost_usd: 0,
    monthly_cost_brl: 0,
    total_users: 0,
    active_ai_users: 0,
    blocked_users: 0,
  },
  users: [],
  by_model: [],
  by_context: [],
  recent_logs: [],
})

onMounted(async () => {
  await loadStats()
})

async function loadStats() {
  loading.value = true
  try {
    const res = await api.get('/admin/ai-governance/stats')
    stats.value = res.data
  } catch (err) {
    swal.error('Erro ao carregar dados de governança', err.response?.data?.message || err.message)
  } finally {
    loading.value = false
  }
}

async function handleToggleKillSwitch(user) {
  try {
    const res = await api.post(`/admin/ai-governance/users/${user.id}/kill-switch`)
    user.is_ai_active = res.data.is_ai_active
    swal.toast(res.data.message, user.is_ai_active ? 'success' : 'warning')
  } catch (err) {
    swal.error('Erro ao alterar Kill-Switch', err.response?.data?.message || err.message)
  }
}

async function handleEditLimit(user) {
  const { value: newLimit } = await Swal.fire({
    title: `Editar Cota Mensal: ${user.name}`,
    text: 'Defina o limite máximo de tokens que este usuário pode consumir no mês.',
    input: 'number',
    inputValue: user.monthly_token_limit,
    inputAttributes: {
      min: '10000',
      step: '50000',
    },
    showCancelButton: true,
    confirmButtonText: 'Atualizar Cota',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#334155',
    background: '#090d16',
    color: '#f8fafc',
    customClass: {
      popup: 'border border-slate-800 rounded-2xl shadow-2xl',
      input: 'bg-slate-950 border-slate-800 text-slate-100 rounded-xl text-sm focus:border-emerald-500',
    },
  })

  if (!newLimit) return

  try {
    await api.patch(`/admin/ai-governance/users/${user.id}/limits`, {
      monthly_token_limit: Number(newLimit),
    })
    user.monthly_token_limit = Number(newLimit)
    user.usage_percentage = Math.min(100, Math.round((user.tokens_used_this_month / user.monthly_token_limit) * 100))
    swal.toast('Limite atualizado com sucesso!', 'success')
  } catch (err) {
    swal.error('Erro ao atualizar limite', err.response?.data?.message || err.message)
  }
}

async function handleResetUsage(user) {
  const confirmed = await swal.confirm({
    title: `Resetar Ciclo de Tokens: ${user.name}?`,
    text: 'A contagem de consumo mensal voltará a zero.',
    confirmText: 'Sim, resetar consumo',
    confirmButtonColor: '#3b82f6',
  })

  if (!confirmed) return

  try {
    await api.post(`/admin/ai-governance/users/${user.id}/reset-usage`)
    user.tokens_used_this_month = 0
    user.usage_percentage = 0
    swal.toast('Ciclo de consumo resetado!', 'success')
  } catch (err) {
    swal.error('Erro ao resetar consumo', err.response?.data?.message || err.message)
  }
}

function formatTokens(num) {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}k`
  return num
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full gap-3">
        <div class="hidden sm:block">
          <h1 class="text-lg sm:text-xl font-bold text-white tracking-tight flex flex-wrap items-center gap-2">
            <span>Governança de IA & FinOps</span>
            <span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-bold">
              Root Admin
            </span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">Auditoria de Custos em Tempo Real, Cotas de Tokens e Kill-Switch</p>
        </div>
        <button
          @click="loadStats"
          :disabled="loading"
          class="w-full sm:w-auto px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 transition flex items-center justify-center space-x-1.5 min-h-[44px]"
        >
          <span v-if="loading" class="animate-spin h-3.5 w-3.5 border-2 border-slate-400 border-t-transparent rounded-full"></span>
          <span>{{ loading ? 'Atualizando...' : 'Recarregar Auditoria' }}</span>
        </button>
      </div>
    </template>

    <div class="space-y-8">
      <!-- 1. KPIs Globais de Consumo e Custos FinOps -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <!-- Tokens Consumidos no Mês -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Tokens Totais (Mês)</span>
            <span class="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse"></span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-white">{{ formatTokens(stats.metrics.monthly_tokens) }}</span>
            <span class="text-xs text-slate-400">tokens</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">Soma de Chat + Jobs Autônomos</p>
        </div>

        <!-- Custo Estimado USD -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Custo Estimado (USD)</span>
            <span class="text-xs font-bold text-emerald-400">$ USD</span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-emerald-400">${{ stats.metrics.monthly_cost_usd.toFixed(2) }}</span>
            <span class="text-xs text-slate-500">faturado Google AI</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">Tabela oficial Gemini v1beta</p>
        </div>

        <!-- Custo Estimado BRL -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Custo Estimado (BRL)</span>
            <span class="text-xs font-bold text-emerald-400">R$ BRL</span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-white">R$ {{ stats.metrics.monthly_cost_brl.toFixed(2) }}</span>
            <span class="text-xs text-slate-500">cotação média</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">Impacto direto no caixa</p>
        </div>

        <!-- Governança de Usuários -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Usuários Ativos / Bloqueados</span>
            <span class="w-2.5 h-2.5 rounded-full" :class="stats.metrics.blocked_users > 0 ? 'bg-amber-400' : 'bg-emerald-400'"></span>
          </div>
          <div class="mt-3 flex items-baseline space-x-2">
            <span class="text-3xl font-black text-white">{{ stats.metrics.active_ai_users }}</span>
            <span class="text-xs text-slate-400">ativos ({{ stats.metrics.blocked_users }} bloqueados)</span>
          </div>
          <p class="mt-2 text-xs text-slate-400">{{ stats.metrics.total_users }} contas cadastradas</p>
        </div>
      </section>

      <!-- 2. Tabela de Governança por Usuário (Ranking de Consumo & Kill-Switch) -->
      <section class="space-y-4">
        <div>
          <h2 class="text-lg font-bold text-white flex items-center space-x-2">
            <span>Ranking de Consumo & Controles de Cota por Usuário</span>
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">
            Supervisione o uso de cada conta. O Kill-Switch suspende imediatamente chamadas e filas Redis daquele usuário.
          </p>
        </div>

        <div class="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900 shadow-xl">
          <!-- Tabela Desktop -->
          <div class="hidden md:block overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-950 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800 font-bold">
                <tr>
                  <th class="p-4">Usuário</th>
                  <th class="p-4">Ventures / Tarefas</th>
                  <th class="p-4">Consumo Mensal / Limite</th>
                  <th class="p-4">Uso de Cota</th>
                  <th class="p-4">Custo Gerado</th>
                  <th class="p-4">Status IA</th>
                  <th class="p-4 text-right">Ações de Governança</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800/60 text-slate-300">
                <tr v-for="u in stats.users" :key="u.id" class="hover:bg-slate-950/40 transition">
                  <td class="p-4">
                    <div class="font-bold text-white flex items-center space-x-1.5">
                      <span>{{ u.name }}</span>
                      <span v-if="u.is_admin" class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">ADMIN</span>
                    </div>
                    <div class="text-[11px] text-slate-500 font-mono">{{ u.email }}</div>
                  </td>

                  <td class="p-4">
                    <span class="text-slate-300 font-semibold">{{ u.businesses_count }} ventures</span>
                    <div class="text-[11px] text-slate-500">{{ u.tasks_count }} tarefas</div>
                  </td>

                  <td class="p-4">
                    <div class="font-mono font-semibold text-slate-200">
                      {{ formatTokens(u.tokens_used_this_month) }} / {{ formatTokens(u.monthly_token_limit) }}
                    </div>
                    <div class="text-[10px] text-slate-500">tokens contabilizados</div>
                  </td>

                  <td class="p-4 min-w-[140px]">
                    <div class="flex items-center space-x-2">
                      <div class="flex-1 h-2 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
                        <div
                          class="h-full rounded-full transition-all duration-300"
                          :class="{
                            'bg-emerald-400': u.usage_percentage < 70,
                            'bg-amber-400': u.usage_percentage >= 70 && u.usage_percentage < 90,
                            'bg-rose-500': u.usage_percentage >= 90
                          }"
                          :style="{ width: `${u.usage_percentage}%` }"
                        ></div>
                      </div>
                      <span class="text-[11px] font-mono font-bold" :class="u.usage_percentage >= 90 ? 'text-rose-400' : 'text-slate-400'">
                        {{ u.usage_percentage }}%
                      </span>
                    </div>
                    <div v-if="u.is_exceeded" class="text-[10px] text-rose-400 font-semibold mt-0.5">
                      ● Cota estourada (bloqueado)
                    </div>
                  </td>

                  <td class="p-4 font-mono font-bold text-emerald-400">
                    ${{ u.cost_usd.toFixed(3) }}
                    <div class="text-[10px] text-slate-500 font-normal">R$ {{ u.cost_brl.toFixed(2) }}</div>
                  </td>

                  <td class="p-4">
                    <span
                      class="px-2 py-0.5 rounded-full text-[10px] font-bold border"
                      :class="u.is_ai_active
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-300'"
                    >
                      {{ u.is_ai_active ? '● IA Ativa' : '○ Bloqueada' }}
                    </span>
                  </td>

                  <td class="p-4 text-right">
                    <div class="flex items-center justify-end space-x-2">
                      <!-- Kill Switch -->
                      <button
                        @click="handleToggleKillSwitch(u)"
                        class="px-2.5 py-1 rounded-lg text-xs font-semibold border transition"
                        :class="u.is_ai_active
                          ? 'bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20'
                          : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20'"
                        :title="u.is_ai_active ? 'Bloquear IA do Usuário' : 'Ativar IA'"
                      >
                        {{ u.is_ai_active ? 'Pausar IA' : 'Ativar IA' }}
                      </button>

                      <!-- Editar Limite -->
                      <button
                        @click="handleEditLimit(u)"
                        class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                      >
                        Editar Cota
                      </button>

                      <!-- Resetar Consumo -->
                      <button
                        @click="handleResetUsage(u)"
                        class="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 transition"
                        title="Zerar ciclo de consumo deste mês"
                      >
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Cards Mobile para Usuários e Cotas -->
          <div class="md:hidden divide-y divide-slate-800">
            <div v-for="u in stats.users" :key="u.id" class="p-4 space-y-3 bg-slate-900">
              <!-- Top: Nome e Status -->
              <div class="flex items-start justify-between">
                <div>
                  <div class="font-bold text-white text-sm flex items-center space-x-2">
                    <span>{{ u.name }}</span>
                    <span v-if="u.is_admin" class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[9px] font-mono font-bold">ADMIN</span>
                  </div>
                  <div class="text-xs text-slate-400 font-mono mt-0.5">{{ u.email }}</div>
                </div>
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0"
                  :class="u.is_ai_active
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-300'"
                >
                  {{ u.is_ai_active ? '● Ativa' : '○ Bloqueada' }}
                </span>
              </div>

              <!-- Barra de Progresso de Cota -->
              <div class="space-y-1.5 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-slate-400">Consumo de Cota</span>
                  <span class="font-mono font-bold" :class="u.usage_percentage >= 90 ? 'text-rose-400' : 'text-slate-200'">
                    {{ u.usage_percentage }}%
                  </span>
                </div>
                <div class="h-2 rounded-full bg-slate-900 overflow-hidden border border-slate-800">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="{
                      'bg-emerald-400': u.usage_percentage < 70,
                      'bg-amber-400': u.usage_percentage >= 70 && u.usage_percentage < 90,
                      'bg-rose-500': u.usage_percentage >= 90
                    }"
                    :style="{ width: `${u.usage_percentage}%` }"
                  ></div>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1">
                  <span>{{ formatTokens(u.tokens_used_this_month) }}</span>
                  <span>Lim: {{ formatTokens(u.monthly_token_limit) }}</span>
                </div>
              </div>

              <!-- Métricas Secundárias -->
              <div class="grid grid-cols-2 gap-2 text-xs">
                <div class="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60">
                  <span class="text-slate-500 block text-[10px]">Custo IA</span>
                  <span class="font-mono font-bold text-emerald-400 text-sm">${{ u.cost_usd.toFixed(3) }}</span>
                  <span class="text-[10px] text-slate-500 block">R$ {{ u.cost_brl.toFixed(2) }}</span>
                </div>
                <div class="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800/60">
                  <span class="text-slate-500 block text-[10px]">Atividade</span>
                  <span class="font-semibold text-slate-200">{{ u.businesses_count }} ventures</span>
                  <span class="text-[10px] text-slate-400 block">{{ u.tasks_count }} tarefas</span>
                </div>
              </div>

              <!-- Ações Touch-Friendly -->
              <div class="pt-1 flex items-center space-x-2">
                <button
                  @click="handleToggleKillSwitch(u)"
                  class="flex-1 py-2.5 rounded-xl text-xs font-semibold border transition text-center min-h-[44px] flex items-center justify-center"
                  :class="u.is_ai_active
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                    : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'"
                >
                  {{ u.is_ai_active ? 'Pausar IA' : 'Ativar IA' }}
                </button>
                <button
                  @click="handleEditLimit(u)"
                  class="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 min-h-[44px] flex items-center justify-center"
                >
                  Editar Cota
                </button>
                <button
                  @click="handleResetUsage(u)"
                  class="p-2.5 rounded-xl bg-slate-800 text-slate-400 hover:text-white border border-slate-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  title="Zerar ciclo de consumo"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Distribuição de Custos por Modelo & Contexto -->
      <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Por Modelo -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
          <h3 class="text-sm font-bold text-white uppercase tracking-wider">Consumo por Modelo de IA</h3>
          <div class="space-y-2 text-xs">
            <div
              v-for="m in stats.by_model"
              :key="m.model"
              class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between"
            >
              <div>
                <span class="font-bold text-white">{{ m.model }}</span>
                <span class="text-slate-500 ml-2">({{ m.calls_count }} chamadas)</span>
              </div>
              <div class="text-right">
                <span class="font-mono font-bold text-emerald-400">${{ Number(m.total_cost).toFixed(3) }}</span>
                <span class="text-slate-400 block text-[10px] font-mono">{{ formatTokens(m.total_tokens) }} tokens</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Por Contexto -->
        <div class="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
          <h3 class="text-sm font-bold text-white uppercase tracking-wider">Consumo por Contexto / Origem</h3>
          <div class="space-y-2 text-xs">
            <div
              v-for="c in stats.by_context"
              :key="c.context"
              class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between"
            >
              <div>
                <span class="font-bold text-white">{{ c.context }}</span>
                <span class="text-slate-500 ml-2">({{ c.calls_count }} execuções)</span>
              </div>
              <div class="text-right">
                <span class="font-mono font-bold text-indigo-400">${{ Number(c.total_cost).toFixed(3) }}</span>
                <span class="text-slate-400 block text-[10px] font-mono">{{ formatTokens(c.total_tokens) }} tokens</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 4. Audit Trail Recente de Chamadas (ai_usage_logs) -->
      <section class="space-y-3">
        <h3 class="text-sm font-bold text-white uppercase tracking-wider">Audit Trail em Tempo Real (Últimas Chamadas)</h3>
        <div class="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900 font-mono text-[11px]">
          <!-- Tabela Desktop -->
          <div class="hidden md:block overflow-x-auto">
            <table class="w-full text-left">
              <thead class="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800 font-bold">
                <tr>
                  <th class="p-3">Data/Hora</th>
                  <th class="p-3">Usuário</th>
                  <th class="p-3">Venture</th>
                  <th class="p-3">Modelo</th>
                  <th class="p-3">Contexto</th>
                  <th class="p-3">Prompt + Output</th>
                  <th class="p-3">Custo USD</th>
                  <th class="p-3 text-right">Latência</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800/60 text-slate-300">
                <tr v-for="log in stats.recent_logs" :key="log.id" class="hover:bg-slate-950/40">
                  <td class="p-3 text-slate-500">{{ new Date(log.created_at).toLocaleTimeString() }}</td>
                  <td class="p-3 text-white font-semibold">{{ log.user_name }}</td>
                  <td class="p-3 text-slate-400">{{ log.business_name || '-' }}</td>
                  <td class="p-3 text-indigo-400">{{ log.model }}</td>
                  <td class="p-3 text-slate-300">{{ log.context }}</td>
                  <td class="p-3 text-slate-400">{{ log.prompt_tokens }} + {{ log.completion_tokens }} ({{ log.total_tokens }})</td>
                  <td class="p-3 text-emerald-400 font-bold">${{ log.estimated_cost_usd.toFixed(5) }}</td>
                  <td class="p-3 text-right text-slate-400">{{ log.latency_ms ? `${log.latency_ms}ms` : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Cards Mobile para Audit Trail -->
          <div class="md:hidden divide-y divide-slate-800">
            <div v-for="log in stats.recent_logs" :key="log.id" class="p-3 space-y-1.5 bg-slate-900">
              <div class="flex items-center justify-between">
                <span class="text-white font-bold text-xs">{{ log.user_name }}</span>
                <span class="text-emerald-400 font-bold">${{ log.estimated_cost_usd.toFixed(4) }}</span>
              </div>
              <div class="flex items-center justify-between text-[10px] text-slate-400">
                <span class="px-1.5 py-0.5 rounded bg-slate-950 text-indigo-300 font-semibold border border-slate-800">{{ log.model }}</span>
                <span class="text-slate-500">{{ new Date(log.created_at).toLocaleTimeString() }} ({{ log.latency_ms ? `${log.latency_ms}ms` : 'ok' }})</span>
              </div>
              <div class="text-[10px] text-slate-300 truncate">
                <span class="text-slate-500">Contexto:</span> {{ log.context }} · <span class="text-slate-500">Negócio:</span> {{ log.business_name || 'Geral' }}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

