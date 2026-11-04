<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Empire Financial & Analytics
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
            Teto: R$ 200,00/mês
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Governança financeira estrita e livro razão auditável de receitas e despesas
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="fetchFinancialData"
          :disabled="loading"
          class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{'animate-spin': loading}">↻</span> Atualizar
        </button>
        <button
          @click="showExpenseModal = true"
          class="px-3 py-2 bg-red-950 hover:bg-red-900 text-red-300 border border-red-800 font-bold text-xs rounded-lg transition font-mono"
        >
          - Lançar Despesa
        </button>
        <button
          @click="showRevenueModal = true"
          class="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition font-mono shadow-md"
        >
          + Lançar Receita
        </button>
      </div>
    </div>

    <!-- Financial Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl">
        <div class="text-xs font-mono text-slate-400 uppercase">Receita Bruta do Mês</div>
        <div class="text-2xl font-bold text-emerald-400 mt-2 font-mono">
          R$ {{ summary.month_revenue_brl || '0.00' }}
        </div>
        <div class="text-xs text-slate-500 mt-1 font-mono">
          Total Histórico: R$ {{ summary.total_revenue_brl || '0.00' }}
        </div>
      </div>

      <div class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl">
        <div class="text-xs font-mono text-slate-400 uppercase">Despesas Totais do Mês</div>
        <div class="text-2xl font-bold text-red-400 mt-2 font-mono">
          R$ {{ summary.month_expenses_brl || '0.00' }}
        </div>
        <div class="text-xs text-slate-500 mt-1 font-mono">
          Teto Máximo Permitido: R$ {{ budget.monthly_limit_brl || '200.00' }}
        </div>
      </div>

      <div class="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 shadow-xl">
        <div class="flex justify-between items-center">
          <div class="text-xs font-mono text-slate-400 uppercase">Saldo Restante do Teto</div>
          <span
            class="text-[9px] font-mono px-1.5 py-0.5 rounded border"
            :class="budget.warning_triggered ? 'bg-red-950 text-red-400 border-red-800' : 'bg-emerald-950 text-emerald-400 border-emerald-800'"
          >
            {{ budget.percentage_used || 0 }}% Usado
          </span>
        </div>
        <div class="text-2xl font-bold text-amber-400 mt-2 font-mono">
          R$ {{ budget.remaining_brl || '200.00' }}
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800 mt-2">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="budget.warning_triggered ? 'bg-red-500' : 'bg-amber-500'"
            :style="{ width: Math.min(100, budget.percentage_used || 0) + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Ledger Table (Real from PostgreSQL) -->
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-bold text-slate-200 uppercase font-mono">
          Livro Razão de Lançamentos Financeiros (PostgreSQL)
        </h3>
        <span class="text-xs font-mono text-slate-500">
          {{ records.length }} lançamentos registrados
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead class="bg-slate-950/80 text-slate-400 border-b border-slate-800">
            <tr>
              <th class="p-3">Data</th>
              <th class="p-3">Negócio</th>
              <th class="p-3">Categoria</th>
              <th class="p-3">Descrição</th>
              <th class="p-3 text-right">Valor (BRL)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 text-slate-300">
            <tr v-for="rec in records" :key="rec.id" class="hover:bg-slate-800/40 transition">
              <td class="p-3 text-slate-400">{{ new Date(rec.recorded_at).toLocaleDateString() }}</td>
              <td class="p-3 text-cyan-400">{{ rec.business?.name || 'Empire Core' }}</td>
              <td class="p-3 text-slate-400 capitalize">{{ rec.category }}</td>
              <td class="p-3">{{ rec.description }}</td>
              <td
                class="p-3 text-right font-bold"
                :class="rec.type === 'revenue' ? 'text-emerald-400' : 'text-red-400'"
              >
                {{ rec.type === 'revenue' ? '+ ' : '- ' }} R$ {{ rec.amount_brl }}
              </td>
            </tr>
            <tr v-if="records.length === 0">
              <td colspan="5" class="p-8 text-center text-slate-500">
                Nenhum lançamento financeiro registrado até o momento.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Lançar Despesa -->
    <div v-if="showExpenseModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
        <h3 class="text-sm font-bold text-red-400 font-mono uppercase">Novo Lançamento de Despesa</h3>
        <p class="text-xs text-slate-400">
          Despesas são submetidas à verificação imediata do teto mensal de R$ 200,00.
        </p>

        <div class="space-y-3 text-xs font-mono">
          <div>
            <label class="block text-slate-400 mb-1">Descrição *</label>
            <input
              v-model="expenseForm.description"
              type="text"
              placeholder="Ex: Renovação domínio ou VPS mensal"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Valor (R$) *</label>
            <input
              v-model.number="expenseForm.amount_brl"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="60.00"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Categoria *</label>
            <select
              v-model="expenseForm.category"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            >
              <option value="infraestrutura">Infraestrutura VPS</option>
              <option value="dominio_ssl">Domínio & SSL</option>
              <option value="ai_api">API de IA (quando aplicável)</option>
              <option value="armazenamento">Armazenamento / Backup</option>
              <option value="outros">Outros</option>
            </select>
          </div>
        </div>

        <div v-if="modalError" class="p-2.5 bg-red-950/80 border border-red-800 text-red-300 text-xs font-mono rounded-lg">
          {{ modalError }}
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            @click="showExpenseModal = false; modalError = null"
            class="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
          >
            Cancelar
          </button>
          <button
            @click="submitExpense"
            :disabled="saving"
            class="px-5 py-2 bg-red-700 hover:bg-red-600 text-white font-bold text-xs rounded-lg font-mono transition"
          >
            <span v-if="saving">Gravando...</span>
            <span v-else>Confirmar Despesa</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Lançar Receita -->
    <div v-if="showRevenueModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
        <h3 class="text-sm font-bold text-emerald-400 font-mono uppercase">Novo Lançamento de Receita</h3>
        <p class="text-xs text-slate-400">
          Registros de monetização confirmada de negócios digitais do império.
        </p>

        <div class="space-y-3 text-xs font-mono">
          <div>
            <label class="block text-slate-400 mb-1">Descrição *</label>
            <input
              v-model="revenueForm.description"
              type="text"
              placeholder="Ex: Pagamento AdSense YouTube ou KDP Royalties"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Valor Recebido (R$) *</label>
            <input
              v-model.number="revenueForm.amount_brl"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="150.00"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Canal de Receita *</label>
            <select
              v-model="revenueForm.category"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            >
              <option value="youtube_adsense">YouTube AdSense</option>
              <option value="amazon_kdp">Amazon KDP Royalties</option>
              <option value="produtos_digitais">Venda de Produtos Digitais (Hotmart/Kiwify)</option>
              <option value="afiliados">Comissões TikTok Shop / Afiliados</option>
              <option value="outros">Outros</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            @click="showRevenueModal = false"
            class="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
          >
            Cancelar
          </button>
          <button
            @click="submitRevenue"
            :disabled="saving"
            class="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg font-mono transition"
          >
            <span v-if="saving">Gravando...</span>
            <span v-else>Confirmar Receita</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(false)
const saving = ref(false)
const showExpenseModal = ref(false)
const showRevenueModal = ref(false)
const modalError = ref(null)

const summary = ref({})
const budget = ref({})
const records = ref([])

const expenseForm = ref({
  description: '',
  amount_brl: null,
  category: 'infraestrutura',
})

const revenueForm = ref({
  description: '',
  amount_brl: null,
  category: 'youtube_adsense',
})

const fetchFinancialData = async () => {
  loading.value = true
  try {
    const [summaryRes, recordsRes] = await Promise.all([
      axios.get('/api/v1/finance/summary'),
      axios.get('/api/v1/finance/records'),
    ])

    if (summaryRes.data) {
      summary.value = summaryRes.data.summary || {}
      budget.value = summaryRes.data.budget || {}
    }
    if (recordsRes.data?.records?.data) {
      records.value = recordsRes.data.records.data
    } else if (Array.isArray(recordsRes.data?.records)) {
      records.value = recordsRes.data.records
    }
  } catch (err) {
    console.error('Falha ao carregar dados financeiros:', err)
  } finally {
    loading.value = false
  }
}

const submitExpense = async () => {
  if (!expenseForm.value.description || !expenseForm.value.amount_brl) {
    return alert('Preencha a descrição e o valor da despesa.')
  }
  saving.value = true
  modalError.value = null

  try {
    const res = await axios.post('/api/v1/finance/expenses', expenseForm.value)
    if (res.data?.success) {
      showExpenseModal.value = false
      expenseForm.value = { description: '', amount_brl: null, category: 'infraestrutura' }
      await fetchFinancialData()
    }
  } catch (err) {
    modalError.value = err.response?.data?.error || err.message || 'Erro ao registrar despesa.'
  } finally {
    saving.value = false
  }
}

const submitRevenue = async () => {
  if (!revenueForm.value.description || !revenueForm.value.amount_brl) {
    return alert('Preencha a descrição e o valor da receita.')
  }
  saving.value = true
  try {
    const res = await axios.post('/api/v1/finance/revenues', revenueForm.value)
    if (res.data?.success) {
      showRevenueModal.value = false
      revenueForm.value = { description: '', amount_brl: null, category: 'youtube_adsense' }
      await fetchFinancialData()
    }
  } catch (err) {
    alert('Erro ao registrar receita: ' + (err.response?.data?.message || err.message))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchFinancialData()
})
</script>
