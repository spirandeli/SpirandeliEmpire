<script setup>
import { ref, watch, onMounted } from 'vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'
import { useBusinessStore } from '@/stores/business'

const props = defineProps({
  businessId: { type: [Number, String], required: true },
  business: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['updated'])

const swal = useSwal()
const businessStore = useBusinessStore()

const loadingCredentials = ref(false)
const savingCredentials = ref(false)
const savingGeneral = ref(false)

function emptyChannel() {
  return {
    enabled: false,
    handle: '',
    channel_url: '',
    username_email: '',
    password: '',
    api_key_or_token: '',
    notes: '',
    auto_publish: false,
    has_password: false,
    has_api_key_or_token: false,
    configured: false,
  }
}

const channelsForm = ref({
  youtube: emptyChannel(),
  tiktok: emptyChannel(),
  instagram: emptyChannel(),
})

const showPassword = ref({
  youtube: false,
  tiktok: false,
  instagram: false,
})

const showToken = ref({
  youtube: false,
  tiktok: false,
  instagram: false,
})

const generalForm = ref({
  name: '',
  niche: '',
  archetype: 'canal_dark',
  north_star_metric: 'monthly_views',
  target_kpi_value: 0,
  description: '',
  tone_of_voice: '',
  target_audience: '',
})

function syncGeneralFromBusiness(biz) {
  if (!biz) return
  generalForm.value = {
    name: biz.name || '',
    niche: biz.niche || '',
    archetype: biz.archetype || biz.type || 'canal_dark',
    north_star_metric: biz.north_star_metric || 'monthly_views',
    target_kpi_value: Number(biz.target_kpi_value || 0),
    description: biz.description || '',
    tone_of_voice: biz.brand_rules?.tone_of_voice || '',
    target_audience: biz.brand_rules?.target_audience || '',
  }
}

async function loadCredentials() {
  loadingCredentials.value = true
  try {
    const res = await api.get(`/businesses/${props.businessId}/credentials`)
    const data = res.data?.data || {}
    for (const key of ['youtube', 'tiktok', 'instagram']) {
      const ch = data[key] || {}
      channelsForm.value[key] = {
        enabled: Boolean(ch.enabled),
        handle: ch.handle || '',
        channel_url: ch.channel_url || '',
        username_email: ch.username_email || '',
        password: ch.password || '',
        api_key_or_token: ch.api_key_or_token || '',
        notes: ch.notes || '',
        auto_publish: Boolean(ch.auto_publish),
        has_password: Boolean(ch.has_password),
        has_api_key_or_token: Boolean(ch.has_api_key_or_token),
        configured: Boolean(ch.configured),
      }
    }
  } catch (err) {
    console.error('Erro ao carregar credenciais:', err)
  } finally {
    loadingCredentials.value = false
  }
}

onMounted(async () => {
  syncGeneralFromBusiness(props.business)
  await loadCredentials()
})

watch(
  () => props.business,
  (val) => {
    syncGeneralFromBusiness(val)
  },
  { deep: true }
)

watch(
  () => props.businessId,
  async () => {
    await loadCredentials()
  }
)

async function handleSaveCredentials() {
  savingCredentials.value = true
  try {
    const payload = {}
    for (const key of ['youtube', 'tiktok', 'instagram']) {
      const c = channelsForm.value[key]
      const hasAnyAccountData = Boolean(
        c.handle?.trim() || c.username_email?.trim() || c.password || c.api_key_or_token
      )
      payload[key] = {
        enabled: c.enabled || hasAnyAccountData,
        handle: c.handle?.trim() || null,
        channel_url: c.channel_url?.trim() || null,
        username_email: c.username_email?.trim() || null,
        password: c.password || undefined,
        api_key_or_token: c.api_key_or_token || undefined,
        notes: c.notes?.trim() || null,
        auto_publish: Boolean(c.auto_publish),
      }
    }
    await api.put(`/businesses/${props.businessId}/credentials`, payload)
    swal.toast('Acessos e credenciais do negócio salvos no cofre AES-256!', 'success')
    await loadCredentials()
    await businessStore.fetchBusiness(props.businessId)
    emit('updated')
  } catch (err) {
    swal.error('Erro ao salvar acessos', err.response?.data?.message || err.message)
  } finally {
    savingCredentials.value = false
  }
}

async function handleClearSecret(platform, field) {
  const label = field === 'password' ? 'a senha' : 'o token/chave'
  const ok = await swal.confirm({
    title: `Remover ${label} de ${platform.toUpperCase()}?`,
    text: 'O valor criptografado será apagado do cofre deste negócio.',
    confirmText: 'Sim, remover',
    confirmButtonColor: '#ef4444',
  })
  if (!ok) return
  try {
    await api.put(`/businesses/${props.businessId}/credentials`, {
      [platform]: { [field]: '__clear__' },
    })
    channelsForm.value[platform][field] = ''
    swal.toast('Credencial removida com segurança.', 'info')
    await loadCredentials()
    await businessStore.fetchBusiness(props.businessId)
    emit('updated')
  } catch (err) {
    swal.error('Erro ao remover credencial', err.response?.data?.message || err.message)
  }
}

async function handleSaveGeneral() {
  if (!generalForm.value.name.trim()) {
    swal.error('Campo obrigatório', 'Informe o nome do negócio.')
    return
  }
  savingGeneral.value = true
  try {
    const existingBrand = props.business?.brand_rules || {}
    await businessStore.updateBusiness(Number(props.businessId), {
      name: generalForm.value.name.trim(),
      niche: generalForm.value.niche.trim(),
      archetype: generalForm.value.archetype,
      north_star_metric: generalForm.value.north_star_metric,
      target_kpi_value: Number(generalForm.value.target_kpi_value || 0),
      description: generalForm.value.description,
      brand_rules: {
        ...existingBrand,
        tone_of_voice: generalForm.value.tone_of_voice,
        target_audience: generalForm.value.target_audience,
      },
    })
    swal.toast('Dados gerais do negócio atualizados!', 'success')
    emit('updated')
  } catch (err) {
    swal.error('Erro ao atualizar dados', err.response?.data?.message || err.message)
  } finally {
    savingGeneral.value = false
  }
}

function copyText(value, label = 'Valor') {
  if (!value) {
    swal.toast(`Nenhum ${label.toLowerCase()} preenchido para copiar.`, 'warning')
    return
  }
  navigator.clipboard.writeText(value)
  swal.toast(`${label} copiado para a área de transferência!`, 'success')
}

const platformMeta = [
  {
    key: 'youtube',
    title: 'YouTube (Canal Dark / Shorts & Longos)',
    subtitle: 'Credenciais da conta Google/YouTube e chave de integração para upload e análise',
    badgeClass: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    icon: '▶️',
    handlePlaceholder: '@misteriosocultos',
    urlPlaceholder: 'https://www.youtube.com/@misteriosocultos',
    userPlaceholder: 'canal.youtube@gmail.com',
    tokenLabel: 'Chave de API / OAuth Refresh Token / Stream Key (Opcional)',
    tokenPlaceholder: 'AIzaSy... ou token OAuth do YouTube Studio',
  },
  {
    key: 'tiktok',
    title: 'TikTok (Perfil Viral / TikTok Shop)',
    subtitle: 'Usuário, senha e token da conta TikTok vinculada a este negócio',
    badgeClass: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
    icon: '🎵',
    handlePlaceholder: '@misterios.tiktok',
    urlPlaceholder: 'https://www.tiktok.com/@misterios.tiktok',
    userPlaceholder: 'login.tiktok@gmail.com ou +55...',
    tokenLabel: 'Session Token / TikTok API Key / Link Afiliado Principal (Opcional)',
    tokenPlaceholder: 'Session ID, chave de API ou link da vitrine TikTok Shop',
  },
  {
    key: 'instagram',
    title: 'Instagram Reels / Plataforma Extra (Opcional)',
    subtitle: 'Conta secundária para distribuição cruzada de vídeos 9:16',
    badgeClass: 'bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30',
    icon: '📸',
    handlePlaceholder: '@misterios.reels',
    urlPlaceholder: 'https://www.instagram.com/misterios.reels',
    userPlaceholder: 'login.insta@gmail.com',
    tokenLabel: 'Token Graph API / Chave de Integração (Opcional)',
    tokenPlaceholder: 'Token ou chave de automação',
  },
]
</script>

<template>
  <div class="space-y-6">
    <!-- SEÇÃO 1: COFRE DE ACESSOS & INTEGRAÇÕES DO NEGÓCIO (YOUTUBE / TIKTOK) -->
    <section class="p-5 sm:p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-lg">🔐</span>
            <h3 class="text-base font-bold text-white">Acessos &amp; Contas Vinculadas ao Negócio</h3>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              AES-256 Vault
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-1">
            Cadastre o usuário/e-mail, senha e tokens do <strong>YouTube</strong> e do <strong>TikTok</strong> exclusivos desta operação para que o sistema e os workers possam integrar.
          </p>
        </div>

        <button
          type="button"
          @click="handleSaveCredentials"
          :disabled="savingCredentials || loadingCredentials"
          class="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 transition shadow-lg shadow-emerald-400/20 disabled:opacity-50 flex items-center justify-center gap-2 shrink-0"
        >
          <span v-if="savingCredentials" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
          <span>{{ savingCredentials ? 'Salvando no Cofre...' : '💾 Salvar Todos os Acessos' }}</span>
        </button>
      </div>

      <div v-if="loadingCredentials" class="p-8 text-center text-xs text-slate-400">
        Descriptografando cofre de credenciais do negócio...
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div
          v-for="meta in platformMeta"
          :key="meta.key"
          class="p-5 rounded-2xl bg-slate-950 border transition space-y-4 flex flex-col justify-between"
          :class="[
            channelsForm[meta.key].configured ? 'border-emerald-500/40' : 'border-slate-800',
            meta.key === 'instagram' ? 'xl:col-span-2' : ''
          ]"
        >
          <div class="space-y-4">
            <!-- Header do Card da Plataforma -->
            <div class="flex flex-wrap items-start justify-between gap-2 border-b border-slate-900 pb-3">
              <div class="flex items-center gap-2.5">
                <span class="w-9 h-9 rounded-xl border flex items-center justify-center text-base shrink-0" :class="meta.badgeClass">
                  {{ meta.icon }}
                </span>
                <div>
                  <h4 class="text-sm font-bold text-white flex items-center gap-2">
                    <span>{{ meta.title }}</span>
                  </h4>
                  <p class="text-[11px] text-slate-400">{{ meta.subtitle }}</p>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <span
                  class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border"
                  :class="channelsForm[meta.key].configured
                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                    : 'bg-slate-900 text-slate-400 border-slate-800'"
                >
                  {{ channelsForm[meta.key].configured ? '✓ Configurado' : 'Pendente' }}
                </span>

                <label class="inline-flex items-center gap-1.5 text-[11px] text-slate-300 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    v-model="channelsForm[meta.key].enabled"
                    class="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-0"
                  />
                  <span>Ativo</span>
                </label>
              </div>
            </div>

            <!-- Campos: Handle e URL -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] font-semibold text-slate-300 mb-1">Handle / @ do Canal</label>
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="channelsForm[meta.key].handle"
                    type="text"
                    :placeholder="meta.handlePlaceholder"
                    class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    @click="copyText(channelsForm[meta.key].handle, 'Handle')"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                    title="Copiar Handle"
                  >📋</button>
                </div>
              </div>

              <div>
                <label class="block text-[11px] font-semibold text-slate-300 mb-1">URL do Canal / Perfil</label>
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="channelsForm[meta.key].channel_url"
                    type="url"
                    :placeholder="meta.urlPlaceholder"
                    class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                  <a
                    v-if="channelsForm[meta.key].channel_url"
                    :href="channelsForm[meta.key].channel_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                    title="Abrir canal em nova aba"
                  >↗</a>
                </div>
              </div>
            </div>

            <!-- Campos: Login/Usuário e Senha -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] font-semibold text-slate-300 mb-1">Usuário / E-mail de Acesso</label>
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="channelsForm[meta.key].username_email"
                    type="text"
                    autocomplete="off"
                    :placeholder="meta.userPlaceholder"
                    class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    @click="copyText(channelsForm[meta.key].username_email, 'Usuário/E-mail')"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                    title="Copiar Usuário/E-mail"
                  >📋</button>
                </div>
              </div>

              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="text-[11px] font-semibold text-slate-300">Senha da Conta</label>
                  <button
                    v-if="channelsForm[meta.key].has_password"
                    type="button"
                    @click="handleClearSecret(meta.key, 'password')"
                    class="text-[10px] text-rose-400 hover:underline"
                  >Limpar senha</button>
                </div>
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="channelsForm[meta.key].password"
                    :type="showPassword[meta.key] ? 'text' : 'password'"
                    autocomplete="new-password"
                    placeholder="••••••••••••"
                    class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    @click="showPassword[meta.key] = !showPassword[meta.key]"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                    :title="showPassword[meta.key] ? 'Ocultar senha' : 'Mostrar senha'"
                  >{{ showPassword[meta.key] ? '🙈' : '👁️' }}</button>
                  <button
                    type="button"
                    @click="copyText(channelsForm[meta.key].password, 'Senha')"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                    title="Copiar Senha"
                  >📋</button>
                </div>
              </div>
            </div>

            <!-- Token / API Key & Notas -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="text-[11px] font-semibold text-slate-300 truncate">{{ meta.tokenLabel }}</label>
                  <button
                    v-if="channelsForm[meta.key].has_api_key_or_token"
                    type="button"
                    @click="handleClearSecret(meta.key, 'api_key_or_token')"
                    class="text-[10px] text-rose-400 hover:underline shrink-0"
                  >Limpar</button>
                </div>
                <div class="flex items-center gap-1.5">
                  <input
                    v-model="channelsForm[meta.key].api_key_or_token"
                    :type="showToken[meta.key] ? 'text' : 'password'"
                    autocomplete="off"
                    :placeholder="meta.tokenPlaceholder"
                    class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    @click="showToken[meta.key] = !showToken[meta.key]"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                  >{{ showToken[meta.key] ? '🙈' : '👁️' }}</button>
                  <button
                    type="button"
                    @click="copyText(channelsForm[meta.key].api_key_or_token, 'Token')"
                    class="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs shrink-0"
                  >📋</button>
                </div>
              </div>

              <div>
                <label class="block text-[11px] font-semibold text-slate-300 mb-1">Observações / 2FA / Recuperação</label>
                <input
                  v-model="channelsForm[meta.key].notes"
                  type="text"
                  placeholder="Ex: E-mail de recuperação, horários de postagem..."
                  class="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
          </div>

          <div class="pt-3 border-t border-slate-900 flex items-center justify-between text-xs">
            <label class="inline-flex items-center gap-2 text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                v-model="channelsForm[meta.key].auto_publish"
                class="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-0"
              />
              <span>Permitir publicação/integração automática pelos IA Workers</span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <!-- SEÇÃO 2: DADOS CADASTRAIS E IDENTIDADE DO NEGÓCIO -->
    <section class="p-5 sm:p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 class="text-base font-bold text-white">📋 Dados Gerais &amp; Diretrizes do Negócio</h3>
          <p class="text-xs text-slate-400 mt-0.5">Edite o nome, nicho, metas (KPI) e tom de voz usados pelo Gemini para gerar roteiros e tarefas.</p>
        </div>
        <button
          type="button"
          @click="handleSaveGeneral"
          :disabled="savingGeneral"
          class="px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition shadow-md shadow-indigo-600/20 disabled:opacity-50 shrink-0"
        >
          {{ savingGeneral ? 'Salvando...' : 'Salvar Dados do Negócio' }}
        </button>
      </div>

      <form @submit.prevent="handleSaveGeneral" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Nome do Negócio</label>
          <input
            v-model="generalForm.name"
            type="text"
            required
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Nicho / Vertical</label>
          <input
            v-model="generalForm.niche"
            type="text"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Métrica North Star</label>
          <select
            v-model="generalForm.north_star_metric"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          >
            <option value="monthly_views">Visualizações Mensais (YouTube / TikTok)</option>
            <option value="commission_volume">Volume de Comissões (R$)</option>
            <option value="mrr">Receita Recorrente Mensal (MRR)</option>
            <option value="leads_captured">Leads Qualificados</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Meta Alvo (Target KPI)</label>
          <input
            v-model.number="generalForm.target_kpi_value"
            type="number"
            step="any"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div class="md:col-span-2">
          <label class="block text-xs font-semibold text-slate-300 mb-1">Descrição Executiva da Operação</label>
          <textarea
            v-model="generalForm.description"
            rows="2"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          ></textarea>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Tom de Voz da Marca (Brand Tone)</label>
          <input
            v-model="generalForm.tone_of_voice"
            type="text"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Público-Alvo Prioritário</label>
          <input
            v-model="generalForm.target_audience"
            type="text"
            class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </form>

      <!-- Token de Webhook do Negócio -->
      <div v-if="business.webhook_secret_token" class="pt-4 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div>
          <span class="font-bold text-slate-300">Token de Webhook do Negócio:</span>
          <span class="ml-2 font-mono text-slate-400">{{ business.webhook_secret_token.slice(0, 16) }}••••••••</span>
        </div>
        <button
          type="button"
          @click="copyText(business.webhook_secret_token, 'Token de Webhook')"
          class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold self-start sm:self-auto"
        >
          📋 Copiar Token Webhook
        </button>
      </div>
    </section>
  </div>
</template>

