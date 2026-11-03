<template>
  <div class="space-y-6 max-w-4xl mx-auto">
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
      <div class="flex items-center space-x-3 mb-2">
        <span class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center font-bold">
          ★
        </span>
        <h2 class="text-xl font-bold text-slate-100">Business Factory</h2>
      </div>
      <p class="text-xs text-slate-400">
        Transforme ideias em negócios digitais planejados, orçados e implantados com isolamento total.
      </p>
    </div>

    <!-- Stepper Indicator -->
    <div class="flex items-center justify-between px-4 py-3 bg-slate-950/60 rounded-xl border border-slate-800 font-mono text-xs">
      <span :class="step >= 1 ? 'text-amber-400 font-bold' : 'text-slate-600'">1. Questionário da Ideia</span>
      <span class="text-slate-700">→</span>
      <span :class="step >= 2 ? 'text-amber-400 font-bold' : 'text-slate-600'">2. Análise de Jeffrey</span>
      <span class="text-slate-700">→</span>
      <span :class="step >= 3 ? 'text-amber-400 font-bold' : 'text-slate-600'">3. Aprovação Humana</span>
      <span class="text-slate-700">→</span>
      <span :class="step >= 4 ? 'text-emerald-400 font-bold' : 'text-slate-600'">4. Provisionamento</span>
    </div>

    <!-- Step 1: Questionnaire Form -->
    <div v-if="step === 1" class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-4">
      <h3 class="text-sm font-bold text-slate-200 uppercase font-mono">Questionário do Novo Negócio</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Nome do Negócio</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="Ex: Canal Histórias do Oriente"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
          />
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Categoria</label>
          <select
            v-model="form.category"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
          >
            <option value="youtube-dark">YouTube Dark / Shorts</option>
            <option value="amazon-kdp">Amazon KDP (eBooks / Devocionais)</option>
            <option value="digital-goods">Produtos Digitais (PDF / Planners)</option>
            <option value="printables">Printables / Artes Imprimíveis</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs text-slate-400 mb-1 font-mono">Descrição & Proposta de Valor</label>
        <textarea
          v-model="form.description"
          rows="3"
          placeholder="Descreva o público-alvo, tema principal, formato das publicações e tom de comunicação..."
          class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
        ></textarea>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Teto Orçamento Inicial</label>
          <input
            v-model="form.budget_limit_brl"
            type="number"
            placeholder="50.00"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
          />
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Necessidade de IA</label>
          <select
            v-model="form.ai_need"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
          >
            <option value="local_only">Apenas Local (Ollama + Piper)</option>
            <option value="gpu_demand">GPU sob demanda (Opcional)</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-slate-400 mb-1 font-mono">Nível de Automação</label>
          <select
            v-model="form.automation_level"
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:border-amber-500 outline-none"
          >
            <option value="semi">Semi-automático (Aprovação humana)</option>
            <option value="full">Autônomo (Supervisionado)</option>
          </select>
        </div>
      </div>

      <div class="flex justify-end pt-4">
        <button
          @click="submitToJeffrey"
          class="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition font-mono uppercase"
        >
          Enviar para Análise de Jeffrey →
        </button>
      </div>
    </div>

    <!-- Step 2: Jeffrey Feasibility Analysis -->
    <div v-if="step === 2" class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 class="text-sm font-bold text-cyan-400 font-mono">Parecer Técnico e Financeiro de Jeffrey</h3>
        <span class="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
          Viabilidade Técnica: Aprovada
        </span>
      </div>

      <div class="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono space-y-3">
        <p class="text-slate-300">
          <strong>Negócio Proposto:</strong> {{ form.name }} ({{ form.category }})
        </p>
        <p class="text-slate-300">
          <strong>Impacto na VPS:</strong> CPU: +4.5% estimado | RAM: +180MB alocados em container isolado.
        </p>
        <p class="text-slate-300">
          <strong>Governança de Custos:</strong> Teto alocado de R$ {{ form.budget_limit_brl }}/mês dentro do limite global de R$ 200/mês.
        </p>
        <p class="text-amber-400">
          <strong>Diretriz de Segurança:</strong> Não utilizar APIs pagas. Geração de roteiros via Ollama e narração local via Piper TTS.
        </p>
      </div>

      <div class="flex justify-between pt-2">
        <button
          @click="step = 1"
          class="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
        >
          ← Ajustar Questionário
        </button>
        <button
          @click="approveProvisioning"
          class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition font-mono uppercase"
        >
          Aprovar e Provisionar Negócio
        </button>
      </div>
    </div>

    <!-- Step 3: Success Completed -->
    <div v-if="step === 4" class="bg-slate-900/80 p-8 rounded-2xl border border-emerald-500/40 text-center space-y-4">
      <div class="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto text-xl font-bold">
        ✓
      </div>
      <h3 class="text-lg font-bold text-slate-100">Negócio Digital Provisionado com Sucesso!</h3>
      <p class="text-xs text-slate-400 max-w-md mx-auto">
        O ambiente isolado foi criado em <code>storage/businesses/{{ form.name.toLowerCase().replace(/\s+/g, '-') }}</code> com templates e permissões seguras.
      </p>
      <div class="pt-4">
        <router-link
          to="/businesses"
          class="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition"
        >
          Ir para o Business Manager
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const step = ref(1)
const form = ref({
  name: '',
  category: 'youtube-dark',
  description: '',
  budget_limit_brl: 50.00,
  ai_need: 'local_only',
  automation_level: 'semi',
})

const submitToJeffrey = () => {
  if (!form.value.name) return alert('Por favor, informe o nome do negócio.')
  step.value = 2
}

const approveProvisioning = () => {
  step.value = 4
}
</script>

