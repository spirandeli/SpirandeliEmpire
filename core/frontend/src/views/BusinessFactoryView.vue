<template>
  <div class="space-y-6 max-w-4xl mx-auto">
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 shadow-xl">
      <div class="flex items-center space-x-3 mb-2">
        <span class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center font-bold text-sm">
          ★
        </span>
        <h2 class="text-xl font-bold text-slate-100">Business Factory (Forja de Negócios & Agentes)</h2>
      </div>
      <p class="text-xs text-slate-400">
        Crie um novo negócio digital já com suas <strong class="text-amber-300">Contas Vinculadas</strong> e <strong class="text-cyan-300">Parâmetros de Automação</strong> para o Jeffrey AI gerir em segundo plano.
      </p>
    </div>

    <!-- Stepper Indicator -->
    <div class="flex items-center justify-between px-4 py-3 bg-slate-950/70 rounded-xl border border-slate-800 font-mono text-xs">
      <span :class="step >= 1 ? 'text-amber-400 font-bold' : 'text-slate-600'">1. Negócio, Contas & Parâmetros</span>
      <span class="text-slate-700">→</span>
      <span :class="step >= 2 ? 'text-amber-400 font-bold' : 'text-slate-600'">2. Parecer Técnico de Jeffrey</span>
      <span class="text-slate-700">→</span>
      <span :class="step >= 3 ? 'text-emerald-400 font-bold' : 'text-slate-600'">3. Provisionamento Real</span>
    </div>

    <!-- Step 1: Questionnaire Form -->
    <div v-if="step === 1" class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 space-y-5 shadow-xl">
      <h3 class="text-sm font-bold text-slate-200 uppercase font-mono">1. Identidade do Negócio Digital</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Nome do Negócio *</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="Ex: TikTok Shop Casa & Tech"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none font-mono"
          />
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Categoria *</label>
          <select
            v-model="form.category"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none font-mono"
          >
            <option value="TikTok Shop Afiliados">🔥 TikTok Shop Afiliados</option>
            <option value="YouTube Dark">🎬 YouTube Dark / Shorts</option>
            <option value="Amazon KDP">📚 Amazon KDP (eBooks / Devocionais)</option>
            <option value="Produtos Digitais">📄 Produtos Digitais (PDF / Planners)</option>
            <option value="Printables & Artes">🖨️ Printables / Artes Imprimíveis</option>
            <option value="SaaS & Automação">⚙️ SaaS & Automação</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs text-slate-400 mb-1 font-mono">Descrição & Proposta de Valor</label>
        <textarea
          v-model="form.description"
          rows="2"
          placeholder="Descreva o público-alvo, nicho, formato das publicações e estrategia de monetização..."
          class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
        ></textarea>
      </div>

      <!-- Initial Linked Account -->
      <div class="p-4 bg-slate-950/90 rounded-xl border border-slate-800 space-y-3">
        <h4 class="text-xs font-mono font-bold text-amber-400 uppercase">
          🔐 Conta Principal do Negócio (Para Gestão do Agente)
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Plataforma</label>
            <input
              v-model="form.account_platform"
              type="text"
              placeholder="TikTok Shop"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">@Handle / Perfil</label>
            <input
              v-model="form.account_handle"
              type="text"
              placeholder="@achadinhos.spirandeli"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">ID Afiliado / Seller ID</label>
            <input
              v-model="form.account_id"
              type="text"
              placeholder="BR-TTS-01"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Link da Vitrine / Canal</label>
            <input
              v-model="form.account_url"
              type="text"
              placeholder="https://www.tiktok.com/@..."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
        </div>
      </div>

      <!-- Initial Automation Parameters -->
      <div class="p-4 bg-slate-950/90 rounded-xl border border-slate-800 space-y-3">
        <h4 class="text-xs font-mono font-bold text-cyan-400 uppercase">
          ⚙️ Parâmetros de Automação do Agente
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Nicho / Produtos Alvo</label>
            <input
              v-model="form.niche"
              type="text"
              placeholder="Ex: Beleza, Casa, Cozinha e Gadgets"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Meta Diária de Entregáveis</label>
            <input
              v-model.number="form.daily_deliverables_goal"
              type="number"
              min="1"
              max="30"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Teto Orçamento Mensal (R$)</label>
            <input
              v-model.number="form.budget_limit_brl"
              type="number"
              min="5"
              max="200"
              step="5"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">CTA Padrão (Chamada para Ação)</label>
            <input
              v-model="form.cta_template"
              type="text"
              placeholder="Clique no carrinho laranja na tela para garantir com desconto!"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Regras para o Agente</label>
            <input
              v-model="form.custom_prompt_rules"
              type="text"
              placeholder="Focar em produtos com comissão >= 15% e vídeo Anti-Ban"
              class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-slate-100"
            />
          </div>
        </div>
      </div>

      <div class="flex justify-end pt-2">
        <button
          @click="submitToJeffrey"
          class="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition font-mono uppercase shadow-md"
        >
          Analisar Viabilidade com Jeffrey →
        </button>
      </div>
    </div>

    <!-- Step 2: Jeffrey Feasibility Analysis -->
    <div v-if="step === 2" class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 class="text-sm font-bold text-cyan-400 font-mono">2. Parecer Técnico e Orçamentário de Jeffrey</h3>
        <span class="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
          Viabilidade Técnica: Aprovada
        </span>
      </div>

      <div class="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono space-y-2.5">
        <p class="text-slate-300">
          <strong>Negócio Proposto:</strong> {{ form.name }} ({{ form.category }})
        </p>
        <p class="text-slate-300">
          <strong>Conta Vinculada:</strong> {{ form.account_platform }} — {{ form.account_handle || '@conta' }} {{ form.account_id ? `[ID: ${form.account_id}]` : '' }}
        </p>
        <p class="text-slate-300">
          <strong>Parâmetros do Agente:</strong> Nicho "{{ form.niche || form.category }}" • Meta de {{ form.daily_deliverables_goal }} entregáveis/dia
        </p>
        <p class="text-slate-300">
          <strong>Governança de Custos:</strong> Teto alocado de R$ {{ Number(form.budget_limit_brl).toFixed(2) }}/mês dentro do teto global da VPS de R$ 200,00/mês.
        </p>
        <p class="text-slate-300">
          <strong>Volume em Disco:</strong> Será alocado o diretório isolado <code>storage/businesses/{{ slugify(form.name) }}</code> com subpastas <code>assets/</code>, <code>scripts/</code>, <code>output/</code> e <code>logs/</code>.
        </p>
      </div>

      <div v-if="provisioningError" class="p-3 bg-red-950/60 border border-red-800 text-red-300 text-xs font-mono rounded-lg">
        {{ provisioningError }}
      </div>

      <div class="flex justify-between pt-2">
        <button
          @click="step = 1"
          :disabled="provisioning"
          class="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
        >
          ← Ajustar Parâmetros
        </button>
        <button
          @click="provisionBusinessReal"
          :disabled="provisioning"
          class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs rounded-lg transition font-mono uppercase shadow-md flex items-center gap-2"
        >
          <span v-if="provisioning" class="animate-spin">↻</span>
          <span>Aprovar e Criar com Contas & Automação</span>
        </button>
      </div>
    </div>

    <!-- Step 3: Success Completed -->
    <div v-if="step === 3" class="bg-slate-900/90 p-8 rounded-2xl border border-emerald-500/40 text-center space-y-4 shadow-xl">
      <div class="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto text-xl font-bold">
        ✓
      </div>
      <h3 class="text-lg font-bold text-slate-100">Negócio Digital & Automação Criados com Sucesso!</h3>
      <p class="text-xs text-slate-400 max-w-md mx-auto">
        O negócio <strong>{{ createdBusiness?.name }}</strong> foi persistido no banco de dados com suas contas e parâmetros operacionais sincronizados na memória do Jeffrey AI:
      </p>
      <div class="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono text-cyan-400 max-w-md mx-auto truncate">
        {{ createdBusiness?.storage_path }}
      </div>
      <div class="pt-4 flex justify-center gap-3">
        <router-link
          to="/businesses"
          class="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition font-mono"
        >
          Gerenciar Contas & Rodar Agente →
        </router-link>
        <router-link
          to="/jeffrey"
          class="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 font-bold text-xs rounded-lg transition font-mono"
        >
          Conversar com Jeffrey
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const step = ref(1)
const provisioning = ref(false)
const provisioningError = ref(null)
const createdBusiness = ref(null)

const form = ref({
  name: '',
  category: 'TikTok Shop Afiliados',
  description: '',
  budget_limit_brl: 50.00,
  account_platform: 'TikTok Shop',
  account_handle: '@achadinhos.spirandeli',
  account_id: 'BR-TTS-01',
  account_url: '',
  niche: 'Achadinhos Virais, Casa, Cozinha e Beleza',
  daily_deliverables_goal: 5,
  cta_template: 'Clique no carrinho laranja na tela antes que acabe o estoque promocional!',
  custom_prompt_rules: 'Priorizar produtos com comissão >= 15%, gancho forte nos primeiros 3s e pipeline Anti-Ban.',
})

const slugify = (text) => {
  return text.toString().toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-]+/g, '')
    .replace(/\-\-+/g, '-')
    .replace(/^-+/, '')
    .replace(/-+$/, '')
}

const submitToJeffrey = () => {
  if (!form.value.name.trim()) {
    return alert('Por favor, informe o nome do negócio digital.')
  }
  step.value = 2
}

const provisionBusinessReal = async () => {
  provisioning.value = true
  provisioningError.value = null

  try {
    const accounts = form.value.account_handle
      ? [{
          id: 'acc_main',
          platform: form.value.account_platform || 'TikTok Shop',
          handle: form.value.account_handle,
          account_id: form.value.account_id || '',
          affiliate_showcase_url: form.value.account_url || '',
          status: 'active',
          notes: 'Conta principal cadastrada na Business Factory',
        }]
      : []

    const automation_params = {
      auto_enabled: true,
      frequency: 'daily',
      assigned_agent: form.value.category.includes('TikTok') ? 'TikTok Shop Strategist' : 'Jeffrey',
      niche: form.value.niche || form.value.category,
      target_audience: 'Público brasileiro de alta conversão',
      daily_deliverables_goal: form.value.daily_deliverables_goal || 3,
      min_commission_percent: 15,
      price_range_brl: '29-149',
      tone_of_voice: 'Dinâmico, persuasivo e direto',
      cta_template: form.value.cta_template,
      pipeline_mode: 'anti_ban_full',
      custom_prompt_rules: form.value.custom_prompt_rules,
    }

    const res = await axios.post('/api/v1/businesses', {
      name: form.value.name,
      category: form.value.category,
      description: form.value.description,
      budget_limit_brl: form.value.budget_limit_brl,
      template_used: form.value.category.toLowerCase().replace(/\s+/g, '-'),
      accounts,
      automation_params,
    })

    if (res.data?.business) {
      createdBusiness.value = res.data.business
      step.value = 3
    }
  } catch (err) {
    provisioningError.value = err.response?.data?.message || err.message || 'Erro ao criar negócio no servidor.'
  } finally {
    provisioning.value = false
  }
}
</script>
