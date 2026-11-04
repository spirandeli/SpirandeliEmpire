<template>
  <div class="space-y-5 max-w-7xl mx-auto">
    <!-- Top Header Bar -->
    <div class="flex items-center justify-between flex-wrap gap-4 bg-slate-900/95 p-5 rounded-2xl border border-slate-800 shadow-xl">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2.5">
          <span>🛡️ Business & Agent Manager</span>
          <span class="text-xs font-mono px-2.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
            {{ businesses.length }} Negócios Ativos
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Configure as <strong class="text-amber-300">Contas Vinculadas</strong> e os <strong class="text-cyan-300">Parâmetros Operacionais</strong> de cada negócio para que o Jeffrey AI gerencie tudo de forma automatizada.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="fetchBusinesses"
          :disabled="loading"
          class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{ 'animate-spin': loading }">↻</span> Atualizar
        </button>
        <router-link
          to="/factory"
          class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition shadow-md flex items-center gap-1.5 font-mono"
        >
          <span>+</span> Novo Negócio Digital
        </router-link>
      </div>
    </div>

    <!-- Feedback Toast Banner -->
    <div
      v-if="feedbackBanner"
      class="p-3.5 rounded-xl bg-emerald-950/90 border border-emerald-500/60 text-emerald-200 text-xs font-mono flex items-center justify-between gap-3 shadow-lg"
    >
      <div>
        ✅ {{ feedbackBanner }}
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <router-link
          to="/jeffrey"
          class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
        >
          Acompanhar no Monitor do Jeffrey →
        </router-link>
        <button @click="feedbackBanner = ''" class="text-emerald-400 hover:text-white px-1">✕</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && businesses.length === 0" class="text-center py-12 text-slate-400 text-xs font-mono">
      Carregando negócios, contas e parâmetros de automação...
    </div>

    <!-- Businesses Cards Grid -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div
        v-for="biz in businesses"
        :key="biz.id"
        class="bg-slate-900/95 rounded-2xl border p-6 flex flex-col justify-between shadow-xl transition"
        :class="biz.slug === 'tiktok-shop-afiliados'
          ? 'border-amber-500/80 ring-1 ring-amber-500/30'
          : 'border-slate-800'"
      >
        <div>
          <!-- Top Badges Row -->
          <div class="flex items-center justify-between flex-wrap gap-2 mb-3">
            <div class="flex items-center gap-2">
              <span
                v-if="biz.slug === 'tiktok-shop-afiliados'"
                class="text-[11px] font-mono px-2.5 py-0.5 rounded bg-gradient-to-r from-pink-600 to-amber-500 text-white font-extrabold uppercase shadow"
              >
                🔥 PRINCIPAL • TIKTOK SHOP
              </span>
              <span class="text-xs font-mono px-2.5 py-0.5 rounded bg-slate-800 text-amber-400 font-semibold border border-slate-700">
                {{ biz.category }}
              </span>
            </div>

            <div class="flex items-center gap-2">
              <span
                class="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase border"
                :class="getAutomation(biz).auto_enabled
                  ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                  : 'bg-slate-800 text-slate-400 border-slate-700'"
              >
                {{ getAutomation(biz).auto_enabled ? `🤖 AUTO (${formatFrequency(getAutomation(biz).frequency)})` : '⏸️ AUTO MANUAL' }}
              </span>
              <span
                class="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase border"
                :class="biz.status === 'active'
                  ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                  : 'bg-amber-950 text-amber-400 border-amber-800'"
              >
                {{ biz.status === 'active' ? 'ATIVO' : 'PAUSADO' }}
              </span>
            </div>
          </div>

          <!-- Title & Description -->
          <h3 class="text-lg font-bold text-slate-100 flex items-center justify-between">
            <span>{{ biz.name }}</span>
            <span class="text-xs font-mono text-slate-500 font-normal">#{{ biz.slug }}</span>
          </h3>
          <p class="text-xs text-slate-400 mt-1.5 leading-relaxed">{{ biz.description }}</p>

          <!-- SECTION 1: CONTAS VINCULADAS DO NEGÓCIO -->
          <div class="mt-4 p-3.5 bg-slate-950/80 rounded-xl border border-slate-800/90">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-mono font-bold text-amber-400 uppercase flex items-center gap-1.5">
                🔐 Contas do Negócio ({{ getAccounts(biz).length }})
              </span>
              <button
                @click="openAccountsModal(biz)"
                class="text-[11px] font-mono text-amber-300 hover:text-amber-200 underline"
              >
                + Adicionar / Editar Contas
              </button>
            </div>

            <div v-if="getAccounts(biz).length === 0" class="text-xs text-slate-500 italic py-1">
              Nenhuma conta cadastrada ainda. Clique em "+ Adicionar / Editar Contas" para informar @handle, ID de afiliado e link da vitrine.
            </div>
            <div v-else class="space-y-1.5">
              <div
                v-for="(acc, idx) in getAccounts(biz)"
                :key="acc.id || idx"
                class="flex items-center justify-between gap-2 text-xs font-mono bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800"
              >
                <div class="min-w-0">
                  <span class="text-amber-300 font-bold">{{ acc.platform || 'Conta' }}:</span>
                  <span class="text-slate-100 ml-1.5 font-semibold">{{ acc.handle }}</span>
                  <span v-if="acc.account_id" class="text-slate-400 ml-1.5 text-[11px]">[ID: {{ acc.account_id }}]</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <a
                    v-if="acc.affiliate_showcase_url"
                    :href="acc.affiliate_showcase_url"
                    target="_blank"
                    rel="noopener"
                    class="text-[10px] text-cyan-400 hover:underline"
                  >
                    Vitrine ↗
                  </a>
                  <span class="w-2 h-2 rounded-full bg-emerald-400" title="Conta ativa para o Agente"></span>
                </div>
              </div>
            </div>
          </div>

          <!-- SECTION 2: PARÂMETROS DE GESTÃO AUTOMATIZADA DO AGENTE -->
          <div class="mt-3 p-3.5 bg-slate-950/80 rounded-xl border border-slate-800/90 text-xs font-mono">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-bold text-cyan-400 uppercase flex items-center gap-1.5">
                ⚙️ Parâmetros do Agente ({{ getAutomation(biz).assigned_agent || 'Jeffrey' }})
              </span>
              <button
                @click="openAutomationModal(biz)"
                class="text-[11px] text-cyan-300 hover:text-cyan-200 underline"
              >
                Configurar Parâmetros
              </button>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-[11px]">
              <div>
                <span class="text-slate-500 block text-[10px]">Nicho / Foco:</span>
                <span class="text-slate-200 font-semibold truncate block" :title="getAutomation(biz).niche">
                  {{ getAutomation(biz).niche || biz.category }}
                </span>
              </div>
              <div>
                <span class="text-slate-500 block text-[10px]">Meta Diária:</span>
                <span class="text-emerald-400 font-bold">
                  {{ getAutomation(biz).daily_deliverables_goal || 3 }} entregáveis/dia
                </span>
              </div>
              <div>
                <span class="text-slate-500 block text-[10px]">Comissão / Preço:</span>
                <span class="text-amber-300">
                  ≥{{ getAutomation(biz).min_commission_percent ?? 15 }}% (R$ {{ getAutomation(biz).price_range_brl || '29-197' }})
                </span>
              </div>
              <div class="col-span-2">
                <span class="text-slate-500 block text-[10px]">CTA Padrão do Agente:</span>
                <span class="text-slate-300 truncate block" :title="getAutomation(biz).cta_template">
                  "{{ getAutomation(biz).cta_template || 'Clique no carrinho laranja abaixo!' }}"
                </span>
              </div>
              <div>
                <span class="text-slate-500 block text-[10px]">Teto Mensal:</span>
                <span class="text-amber-400 font-bold">R$ {{ biz.budget_limit_brl }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions Bar -->
        <div class="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center flex-wrap gap-2">
            <button
              @click="openRunAgentModal(biz)"
              :disabled="runningAgentId === biz.id"
              class="px-3.5 py-2 text-xs font-mono font-bold rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 shadow transition flex items-center gap-1.5"
            >
              <span>🚀</span>
              <span>{{ runningAgentId === biz.id ? 'Disparando...' : 'Rodar Agente Agora' }}</span>
            </button>

            <button
              @click="openAccountsModal(biz)"
              class="px-3 py-2 text-xs font-mono rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700 transition"
            >
              🔐 Contas ({{ getAccounts(biz).length }})
            </button>

            <button
              @click="openAutomationModal(biz)"
              class="px-3 py-2 text-xs font-mono rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition"
            >
              ⚙️ Parâmetros
            </button>
          </div>

          <div class="flex items-center gap-2">
            <button
              @click="toggleStatus(biz)"
              :disabled="updatingId === biz.id"
              class="px-2.5 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              {{ biz.status === 'active' ? 'Pausar' : 'Ativar' }}
            </button>
            <button
              v-if="biz.slug !== 'tiktok-shop-afiliados'"
              @click="deleteBusiness(biz)"
              class="px-2.5 py-1.5 text-xs font-mono rounded text-red-400 hover:bg-red-950/50 transition border border-red-900/40"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- MODAL 1: CONTAS VINCULADAS DO NEGÓCIO (ACCOUNTS MANAGER)              -->
    <!-- ===================================================================== -->
    <div
      v-if="activeModal === 'accounts' && selectedBiz"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
      @click.self="closeModal"
    >
      <div class="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl my-auto space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
              🔐 Contas Vinculadas — <span class="text-amber-400">{{ selectedBiz.name }}</span>
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              Cadastre os perfis, IDs de afiliado, links de vitrine e observações para o Jeffrey AI gerir este negócio.
            </p>
          </div>
          <button @click="closeModal" class="text-slate-400 hover:text-white text-sm px-2 py-1">✕</button>
        </div>

        <div class="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
          <div
            v-for="(acc, index) in accountsForm"
            :key="index"
            class="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 relative"
          >
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono font-bold text-amber-400">
                Conta #{{ index + 1 }} — {{ acc.handle || 'Nova Conta' }}
              </span>
              <button
                type="button"
                @click="removeAccountRow(index)"
                class="text-xs font-mono text-red-400 hover:text-red-300"
              >
                Remover Conta
              </button>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div>
                <label class="block text-[10px] text-slate-400 mb-1">Plataforma *</label>
                <select
                  v-model="acc.platform"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
                >
                  <option value="TikTok Shop">TikTok Shop</option>
                  <option value="TikTok Creator">TikTok Creator / Perfil</option>
                  <option value="YouTube Shorts">YouTube Shorts / Dark</option>
                  <option value="Instagram Reels">Instagram Reels</option>
                  <option value="Amazon KDP">Amazon KDP</option>
                  <option value="Kiwify / Hotmart">Kiwify / Hotmart</option>
                  <option value="Etsy / Gumroad">Etsy / Gumroad / Loja</option>
                </select>
              </div>
              <div>
                <label class="block text-[10px] text-slate-400 mb-1">@Handle / Nome da Conta *</label>
                <input
                  v-model="acc.handle"
                  type="text"
                  placeholder="@achadinhos.spirandeli"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-slate-400 mb-1">ID Afiliado / Seller ID</label>
                <input
                  v-model="acc.account_id"
                  type="text"
                  placeholder="BR-TTS-AFILIADO-01"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label class="block text-[10px] text-slate-400 mb-1">Link da Vitrine / Canal / Loja</label>
                <input
                  v-model="acc.affiliate_showcase_url"
                  type="text"
                  placeholder="https://www.tiktok.com/@achadinhos.spirandeli"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
                />
              </div>
              <div>
                <label class="block text-[10px] text-slate-400 mb-1">E-mail / Login de Referência</label>
                <input
                  v-model="acc.email_or_login"
                  type="text"
                  placeholder="tiktokshop@spirandeliempire.tech"
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
                />
              </div>
            </div>

            <div class="text-xs font-mono">
              <label class="block text-[10px] text-slate-400 mb-1">Instruções / Notas desta Conta para o Agente</label>
              <input
                v-model="acc.notes"
                type="text"
                placeholder="Ex: Conta principal focada em achadinhos de casa e cozinha com carrinho laranja."
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100"
              />
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-slate-800">
          <button
            type="button"
            @click="addAccountRow"
            class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-mono border border-slate-700"
          >
            + Adicionar Outra Conta
          </button>

          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono"
            >
              Cancelar
            </button>
            <button
              type="button"
              @click="saveAccounts"
              :disabled="savingModal"
              class="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs font-mono"
            >
              {{ savingModal ? 'Salvando...' : '💾 Salvar Contas do Negócio' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- MODAL 2: PARÂMETROS DE AUTOMAÇÃO DO AGENTE                            -->
    <!-- ===================================================================== -->
    <div
      v-if="activeModal === 'automation' && selectedBiz"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
      @click.self="closeModal"
    >
      <div class="w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl my-auto space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
              ⚙️ Parâmetros do Agente — <span class="text-cyan-400">{{ selectedBiz.name }}</span>
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              Estes parâmetros guiam o Jeffrey AI e os agentes em 2º plano ao gerenciar este negócio automaticamente.
            </p>
          </div>
          <button @click="closeModal" class="text-slate-400 hover:text-white text-sm px-2 py-1">✕</button>
        </div>

        <form @submit.prevent="saveAutomation" class="space-y-3 text-xs font-mono">
          <div class="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <div class="font-bold text-slate-100">🤖 Execução Periódica Automatizada em 2º Plano</div>
              <div class="text-[11px] text-slate-400">
                Quando ativo, o worker do Jeffrey executa ciclos automáticos para este negócio na frequência escolhida.
              </div>
            </div>
            <input
              v-model="automationForm.auto_enabled"
              type="checkbox"
              class="w-5 h-5 accent-amber-500 cursor-pointer"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Frequência do Ciclo</label>
              <select
                v-model="automationForm.frequency"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              >
                <option value="every_6h">A cada 6 horas</option>
                <option value="every_12h">A cada 12 horas</option>
                <option value="daily">Diário (1x por dia)</option>
                <option value="weekly">Semanal</option>
                <option value="manual">Apenas sob comando</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Agente Responsável</label>
              <select
                v-model="automationForm.assigned_agent"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              >
                <option value="TikTok Shop Strategist">TikTok Shop Strategist</option>
                <option value="Research Agent">Research Agent</option>
                <option value="Jeffrey">Jeffrey (Executivo)</option>
                <option value="Scriptwriter Agent">Scriptwriter Agent</option>
                <option value="Publisher Agent">Publisher Agent</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Teto Mensal do Negócio (R$)</label>
              <input
                v-model.number="automationForm.budget_limit_brl"
                type="number"
                min="0"
                max="200"
                step="5"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Nicho / Produtos Foco *</label>
              <input
                v-model="automationForm.niche"
                type="text"
                required
                placeholder="Ex: Achadinhos Virais, Beleza, Casa & Cozinha, Tech"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Público-Alvo</label>
              <input
                v-model="automationForm.target_audience"
                type="text"
                placeholder="Ex: Compradores por impulso no TikTok Brasil (18-45 anos)"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Meta Diária de Entregáveis</label>
              <input
                v-model.number="automationForm.daily_deliverables_goal"
                type="number"
                min="1"
                max="30"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Comissão Mínima (%)</label>
              <input
                v-model.number="automationForm.min_commission_percent"
                type="number"
                min="0"
                max="100"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Faixa de Preço Alvo (R$)</label>
              <input
                v-model="automationForm.price_range_brl"
                type="text"
                placeholder="29-149"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">Tom de Voz</label>
              <input
                v-model="automationForm.tone_of_voice"
                type="text"
                placeholder="Dinâmico, prova social forte, urgência real"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-slate-400 mb-1">CTA Padrão (Chamada para Ação)</label>
              <input
                v-model="automationForm.cta_template"
                type="text"
                placeholder="Clique no carrinho laranja na tela antes que o estoque acabe!"
                class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
              />
            </div>
          </div>

          <div>
            <label class="block text-[10px] text-slate-400 mb-1">Regras Operacionais Específicas para o Agente</label>
            <textarea
              v-model="automationForm.custom_prompt_rules"
              rows="3"
              placeholder="Ex: Priorizar produtos com alta avaliação (>4.7), comissão mínima de 15%, gerar 3 variações de Hook de 3 segundos por produto e aplicar pipeline Anti-Ban."
              class="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-slate-100"
            ></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 rounded-lg bg-slate-800 text-slate-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              :disabled="savingModal"
              class="px-5 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold"
            >
              {{ savingModal ? 'Salvando...' : '💾 Salvar Parâmetros & Automação' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ===================================================================== -->
    <!-- MODAL 3: DISPARAR AGENTE AGORA (COM PARÂMETROS E CONTAS DO NEGÓCIO)   -->
    <!-- ===================================================================== -->
    <div
      v-if="activeModal === 'run' && selectedBiz"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
      @click.self="closeModal"
    >
      <div class="w-full max-w-lg bg-slate-900 border border-amber-500/60 rounded-2xl p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
            🚀 Executar Gestão Automatizada — <span class="text-amber-400">{{ selectedBiz.name }}</span>
          </h3>
          <button @click="closeModal" class="text-slate-400 hover:text-white text-sm px-2 py-1">✕</button>
        </div>

        <div class="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono space-y-1.5 text-slate-300">
          <div>
            <strong class="text-amber-400">Agente:</strong> {{ getAutomation(selectedBiz).assigned_agent || 'Jeffrey' }}
          </div>
          <div>
            <strong class="text-amber-400">Contas Alvo:</strong>
            {{ getAccounts(selectedBiz).map(a => `${a.platform}: ${a.handle}`).join(' | ') || 'Nenhuma conta cadastrada' }}
          </div>
          <div>
            <strong class="text-amber-400">Parâmetros:</strong>
            Nicho "{{ getAutomation(selectedBiz).niche }}" • Meta: {{ getAutomation(selectedBiz).daily_deliverables_goal }} entregáveis
          </div>
        </div>

        <div class="text-xs font-mono">
          <label class="block text-slate-400 mb-1">
            Objetivo específico para este ciclo (opcional — deixe em branco para rodar o ciclo completo padrão):
          </label>
          <textarea
            v-model="customRunObjective"
            rows="3"
            placeholder="Ex: Levantar 10 produtos virais de cozinha na TikTok Shop hoje com roteiro de 30s e CTA para o carrinho laranja..."
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100"
          ></textarea>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            @click="closeModal"
            class="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-mono"
          >
            Cancelar
          </button>
          <button
            type="button"
            @click="confirmRunAgent"
            :disabled="savingModal"
            class="px-5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold text-xs font-mono"
          >
            {{ savingModal ? 'Enfileirando no Worker...' : '🚀 Disparar Agente em 2º Plano' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const businesses = ref([])
const loading = ref(false)
const updatingId = ref(null)
const runningAgentId = ref(null)
const feedbackBanner = ref('')

// Modal state
const activeModal = ref(null) // 'accounts' | 'automation' | 'run' | null
const selectedBiz = ref(null)
const savingModal = ref(false)
const accountsForm = ref([])
const automationForm = ref({})
const customRunObjective = ref('')

const getAccounts = (biz) => {
  return biz.accounts_list || biz.accounts || biz.settings?.accounts || []
}

const getAutomation = (biz) => {
  return biz.automation_config || biz.automation_params || biz.settings?.automation_params || {
    auto_enabled: true,
    frequency: 'daily',
    assigned_agent: 'Jeffrey',
    niche: biz.category,
    daily_deliverables_goal: 3,
    min_commission_percent: 15,
    price_range_brl: '29-149',
    cta_template: 'Clique no carrinho laranja!',
  }
}

const formatFrequency = (freq) => {
  const map = {
    every_6h: '6h',
    every_12h: '12h',
    daily: 'Diário',
    weekly: 'Semanal',
    manual: 'Manual',
  }
  return map[freq] || freq || 'Diário'
}

const fetchBusinesses = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/businesses')
    if (res.data?.businesses) {
      businesses.value = res.data.businesses
    }
  } catch (err) {
    console.error('Falha ao carregar negócios:', err)
  } finally {
    loading.value = false
  }
}

const openAccountsModal = (biz) => {
  selectedBiz.value = biz
  const existing = getAccounts(biz)
  accountsForm.value = existing.length > 0
    ? JSON.parse(JSON.stringify(existing))
    : [{
        platform: biz.slug === 'tiktok-shop-afiliados' ? 'TikTok Shop' : 'YouTube Shorts',
        handle: '@minha.conta',
        account_id: '',
        affiliate_showcase_url: '',
        email_or_login: '',
        status: 'active',
        notes: '',
      }]
  activeModal.value = 'accounts'
}

const addAccountRow = () => {
  accountsForm.value.push({
    platform: 'TikTok Shop',
    handle: '',
    account_id: '',
    affiliate_showcase_url: '',
    email_or_login: '',
    status: 'active',
    notes: '',
  })
}

const removeAccountRow = (index) => {
  accountsForm.value.splice(index, 1)
}

const saveAccounts = async () => {
  if (!selectedBiz.value) return
  savingModal.value = true
  try {
    const res = await axios.post(`/api/v1/businesses/${selectedBiz.value.id}/accounts`, {
      accounts: accountsForm.value,
    })
    if (res.data?.business) {
      const idx = businesses.value.findIndex(b => b.id === selectedBiz.value.id)
      if (idx !== -1) businesses.value[idx] = res.data.business
    }
    feedbackBanner.value = res.data?.message || 'Contas do negócio salvas e sincronizadas com o Jeffrey AI!'
    closeModal()
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao salvar contas do negócio.')
  } finally {
    savingModal.value = false
  }
}

const openAutomationModal = (biz) => {
  selectedBiz.value = biz
  const current = getAutomation(biz)
  automationForm.value = {
    auto_enabled: current.auto_enabled !== false,
    frequency: current.frequency || 'daily',
    assigned_agent: current.assigned_agent || 'Jeffrey',
    niche: current.niche || biz.category,
    target_audience: current.target_audience || '',
    daily_deliverables_goal: current.daily_deliverables_goal || 3,
    min_commission_percent: current.min_commission_percent ?? 15,
    price_range_brl: current.price_range_brl || '29-149',
    tone_of_voice: current.tone_of_voice || 'Persuasivo e direto',
    cta_template: current.cta_template || 'Clique no link ou carrinho laranja abaixo!',
    pipeline_mode: current.pipeline_mode || 'anti_ban_full',
    custom_prompt_rules: current.custom_prompt_rules || '',
    budget_limit_brl: biz.budget_limit_brl || 50,
  }
  activeModal.value = 'automation'
}

const saveAutomation = async () => {
  if (!selectedBiz.value) return
  savingModal.value = true
  try {
    const res = await axios.put(`/api/v1/businesses/${selectedBiz.value.id}`, {
      budget_limit_brl: automationForm.value.budget_limit_brl,
      automation_params: automationForm.value,
    })
    if (res.data?.business) {
      const idx = businesses.value.findIndex(b => b.id === selectedBiz.value.id)
      if (idx !== -1) businesses.value[idx] = res.data.business
    }
    feedbackBanner.value = res.data?.message || 'Parâmetros de automação atualizados com sucesso!'
    closeModal()
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao salvar parâmetros de automação.')
  } finally {
    savingModal.value = false
  }
}

const openRunAgentModal = (biz) => {
  selectedBiz.value = biz
  customRunObjective.value = ''
  activeModal.value = 'run'
}

const confirmRunAgent = async () => {
  if (!selectedBiz.value) return
  savingModal.value = true
  runningAgentId.value = selectedBiz.value.id
  try {
    const res = await axios.post(`/api/v1/businesses/${selectedBiz.value.id}/run-agent`, {
      custom_objective: customRunObjective.value || null,
    })
    feedbackBanner.value = res.data?.message || `Ciclo automatizado iniciado para ${selectedBiz.value.name}!`
    closeModal()
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao disparar agente para este negócio.')
  } finally {
    savingModal.value = false
    runningAgentId.value = null
  }
}

const closeModal = () => {
  activeModal.value = null
  selectedBiz.value = null
}

const toggleStatus = async (biz) => {
  updatingId.value = biz.id
  const nextStatus = biz.status === 'active' ? 'paused' : 'active'
  try {
    const res = await axios.patch(`/api/v1/businesses/${biz.id}/status`, {
      status: nextStatus,
    })
    if (res.data?.business) {
      biz.status = res.data.business.status
    }
  } catch (err) {
    alert('Erro ao atualizar status do negócio: ' + (err.response?.data?.message || err.message))
  } finally {
    updatingId.value = null
  }
}

const deleteBusiness = async (biz) => {
  if (!confirm(`Tem certeza que deseja remover o negócio "${biz.name}"?`)) return
  try {
    await axios.delete(`/api/v1/businesses/${biz.id}`)
    businesses.value = businesses.value.filter(b => b.id !== biz.id)
  } catch (err) {
    alert('Erro ao excluir negócio: ' + (err.response?.data?.message || err.message))
  }
}

onMounted(() => {
  fetchBusinesses()
})
</script>
