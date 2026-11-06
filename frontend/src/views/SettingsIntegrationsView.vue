<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useSwal } from '@/composables/useSwal'
import { api } from '@/services/api'

const route = useRoute()
const swal = useSwal()

const integrations = ref([])
const loading = ref(false)

// Formulário Gemini
const geminiApiKey = ref('')
const geminiModel = ref('gemini-2.5-pro')
const savingGemini = ref(false)

// Formulário Apple CalDAV
const appleId = ref('')
const appleAppPassword = ref('')
const appleServerUrl = ref('https://caldav.icloud.com')
const savingApple = ref(false)
const syncingApple = ref(false)

// Apple Shortcuts Webhook
const shortcutsTokenGenerated = ref('')
const shortcutsWebhookUrl = ref('')
const generatingShortcutsToken = ref(false)

// Google OAuth
const syncingGoogle = ref(false)

onMounted(async () => {
  if (route.query.success === 'google_connected') {
    swal.toast('Google Workspace conectado com sucesso!', 'success')
  } else if (route.query.error) {
    swal.error('Erro ao conectar Google', route.query.error)
  }

  await fetchIntegrations()
})

async function fetchIntegrations() {
  loading.value = true
  try {
    const res = await api.get('/integrations')
    integrations.value = res.data.data || []

    const geminiInt = integrations.value.find((i) => i.provider === 'gemini')
    if (geminiInt?.metadata?.model) {
      geminiModel.value = geminiInt.metadata.model
    }

    const appleInt = integrations.value.find((i) => i.provider === 'apple_caldav')
    if (appleInt?.metadata?.apple_id) {
      appleId.value = appleInt.metadata.apple_id
    }
  } catch (err) {
    swal.error('Erro ao buscar integrações', err.response?.data?.message || err.message)
  } finally {
    loading.value = false
  }
}

const geminiIntegration = computed(() => integrations.value.find((i) => i.provider === 'gemini'))
const googleIntegration = computed(() => integrations.value.find((i) => i.provider === 'google'))
const appleIntegration = computed(() => integrations.value.find((i) => i.provider === 'apple_caldav'))
const shortcutsIntegration = computed(() => integrations.value.find((i) => i.provider === 'apple_shortcuts'))

async function saveGemini() {
  if (!geminiApiKey.value.trim() && !geminiIntegration.value) {
    swal.error('Atenção', 'Informe a API Key do Gemini.')
    return
  }

  savingGemini.value = true
  try {
    await api.put('/integrations/gemini', {
      api_key: geminiApiKey.value.trim() || undefined,
      model: geminiModel.value,
    })
    swal.toast('Credenciais do Gemini 3.8 salvas com sucesso no cofre!', 'success')
    geminiApiKey.value = ''
    await fetchIntegrations()
  } catch (err) {
    swal.error('Falha ao salvar Gemini', err.response?.data?.message || err.message)
  } finally {
    savingGemini.value = false
  }
}

async function connectGoogle() {
  try {
    const res = await api.get('/integrations/google/redirect')
    if (res.data?.auth_url) {
      window.location.href = res.data.auth_url
    }
  } catch (err) {
    swal.error('Erro ao iniciar OAuth', err.response?.data?.message || err.message)
  }
}

async function syncGoogle() {
  syncingGoogle.value = true
  try {
    await api.post('/integrations/google/sync')
    swal.toast('Job de sincronização do Google Calendar enfileirado!', 'success')
  } catch (err) {
    swal.error('Erro ao sincronizar Google', err.response?.data?.message || err.message)
  } finally {
    syncingGoogle.value = false
  }
}

async function saveAppleCaldav() {
  if (!appleId.value.trim() || !appleAppPassword.value.trim()) {
    swal.error('Campos obrigatórios', 'Informe o Apple ID e a Senha Específica de App.')
    return
  }

  savingApple.value = true
  try {
    await api.put('/integrations/apple-caldav', {
      apple_id: appleId.value.trim(),
      app_password: appleAppPassword.value.trim(),
      server_url: appleServerUrl.value.trim(),
    })
    swal.toast('Conexão CalDAV do iCloud salva! Sincronização inicial disparada.', 'success')
    appleAppPassword.value = ''
    await fetchIntegrations()
  } catch (err) {
    swal.error('Falha na integração Apple', err.response?.data?.message || err.message)
  } finally {
    savingApple.value = false
  }
}

async function syncApple() {
  syncingApple.value = true
  try {
    await api.post('/integrations/apple-caldav/sync')
    swal.toast('Sincronização do Apple iCloud disparada com sucesso!', 'success')
  } catch (err) {
    swal.error('Falha ao sincronizar Apple', err.response?.data?.message || err.message)
  } finally {
    syncingApple.value = false
  }
}

async function generateShortcutsToken() {
  generatingShortcutsToken.value = true
  try {
    const res = await api.post('/integrations/shortcuts/token', {
      name: 'iPhone / Mac Shortcuts',
    })
    shortcutsTokenGenerated.value = res.data.token
    shortcutsWebhookUrl.value = res.data.webhook_url
    swal.toast('Novo token do Webhook gerado! Copie agora.', 'success')
    await fetchIntegrations()
  } catch (err) {
    swal.error('Erro ao gerar token', err.response?.data?.message || err.message)
  } finally {
    generatingShortcutsToken.value = false
  }
}

async function disconnect(integration) {
  const confirmed = await swal.confirm({
    title: `Desconectar ${integration.name || integration.provider}?`,
    text: 'As credenciais criptografadas serão removidas do cofre de segurança.',
    confirmText: 'Sim, desconectar',
    confirmButtonColor: '#ef4444',
  })

  if (!confirmed) return

  try {
    await api.delete(`/integrations/${integration.id}`)
    swal.toast('Integração removida do cofre.', 'info')
    await fetchIntegrations()
  } catch (err) {
    swal.error('Erro ao desconectar', err.response?.data?.message || err.message)
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
  swal.toast('Copiado para a área de transferência!', 'success')
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div>
        <h1 class="text-xl font-bold text-white tracking-tight">Cofre de Integrações & IA</h1>
        <p class="text-xs text-slate-400 mt-0.5">Gestão Criptografada de Chaves de API, Tokens OAuth e Protocolos de Calendário</p>
      </div>
    </template>

    <div class="space-y-8 max-w-5xl">
      <!-- 1. Motor Gemini 3.8 Intelligence -->
      <section class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-black text-white text-lg shadow-md shadow-emerald-500/20">
              G
            </div>
            <div>
              <h2 class="text-base font-bold text-white flex items-center space-x-2">
                <span>Gemini 3.8 Intelligence Engine (Google AI)</span>
                <span
                  class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
                  :class="geminiIntegration?.is_active
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border-slate-700'"
                >
                  {{ geminiIntegration?.is_active ? 'Conectado & Operante' : 'Usando Chave do Sistema / Pendente' }}
                </span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Cérebro do COO Virtual com suporte a Function Calling, Structured Outputs e autonomia total.
              </p>
            </div>
          </div>
          <button
            v-if="geminiIntegration"
            @click="disconnect(geminiIntegration)"
            class="text-xs text-rose-400 hover:text-rose-300 font-semibold"
          >
            Remover Chave
          </button>
        </div>

        <form @submit.prevent="saveGemini" class="space-y-4 pt-2 border-t border-slate-800/80">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Gemini API Key Privada
              </label>
              <input
                v-model="geminiApiKey"
                type="password"
                placeholder="AIzaSy... (Chave armazenada sob criptografia AES-256)"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              />
              <p class="text-[11px] text-slate-500 mt-1">Por segurança, a chave existente nunca é reenviada à tela.</p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Modelo Padrão
              </label>
              <select
                v-model="geminiModel"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="gemini-2.5-pro">Gemini 2.5 Pro (Recomendado)</option>
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (Ultra Rápido)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
            </div>
          </div>

          <div class="flex items-center justify-end">
            <button
              type="submit"
              :disabled="savingGemini"
              class="px-5 py-2.5 rounded-xl font-bold text-xs text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 transition shadow-md shadow-emerald-400/20 flex items-center space-x-1.5"
            >
              <span v-if="savingGemini" class="animate-spin h-3.5 w-3.5 border-2 border-slate-950 border-t-transparent rounded-full"></span>
              <span>{{ savingGemini ? 'Salvando...' : 'Salvar no Cofre' }}</span>
            </button>
          </div>
        </form>
      </section>

      <!-- 2. Google Workspace (Calendar & Tasks) -->
      <section class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 font-black text-lg">
              📅
            </div>
            <div>
              <h2 class="text-base font-bold text-white flex items-center space-x-2">
                <span>Google Workspace (Calendar & Tasks)</span>
                <span
                  class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
                  :class="googleIntegration?.is_active
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border-slate-700'"
                >
                  {{ googleIntegration?.is_active ? 'Conectado (OAuth2)' : 'Desconectado' }}
                </span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Permite ao Gemini consultar horários livres antes de agendar tarefas ou compromissos.
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <button
              v-if="googleIntegration?.is_active"
              @click="syncGoogle"
              :disabled="syncingGoogle"
              class="px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              {{ syncingGoogle ? 'Sincronizando...' : 'Sync Agora' }}
            </button>
            <button
              v-if="googleIntegration"
              @click="disconnect(googleIntegration)"
              class="text-xs text-rose-400 hover:text-rose-300 font-semibold"
            >
              Desconectar
            </button>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between">
          <div class="text-xs text-slate-400">
            <p v-if="googleIntegration?.metadata?.email">
              Conta vinculada: <strong class="text-slate-200">{{ googleIntegration.metadata.email }}</strong>
            </p>
            <p v-else>Nenhuma conta Google conectada no momento.</p>
          </div>
          <button
            @click="connectGoogle"
            class="px-4 py-2 text-xs font-bold rounded-xl text-white bg-blue-600 hover:bg-blue-500 transition shadow-md shadow-blue-600/20"
          >
            {{ googleIntegration?.is_active ? 'Reconectar Google Account' : 'Conectar Google Calendar' }}
          </button>
        </div>
      </section>

      <!-- 3. Apple iCloud (CalDAV & Reminders) -->
      <section class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200 font-black text-lg">
              🍎
            </div>
            <div>
              <h2 class="text-base font-bold text-white flex items-center space-x-2">
                <span>Apple iCloud (CalDAV & Lembretes)</span>
                <span
                  class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
                  :class="appleIntegration?.is_active
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border-slate-700'"
                >
                  {{ appleIntegration?.is_active ? 'Conectado (CalDAV)' : 'Desconectado' }}
                </span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Sincroniza eventos no Apple Calendário e tarefas no app Lembretes do iPhone/Mac.
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <button
              v-if="appleIntegration?.is_active"
              @click="syncApple"
              :disabled="syncingApple"
              class="px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              {{ syncingApple ? 'Sincronizando...' : 'Sync Agora' }}
            </button>
            <button
              v-if="appleIntegration"
              @click="disconnect(appleIntegration)"
              class="text-xs text-rose-400 hover:text-rose-300 font-semibold"
            >
              Desconectar
            </button>
          </div>
        </div>

        <form @submit.prevent="saveAppleCaldav" class="space-y-4 pt-2 border-t border-slate-800/80">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Apple ID (E-mail do iCloud)
              </label>
              <input
                v-model="appleId"
                type="email"
                placeholder="seu.id@icloud.com"
                required
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Senha Específica de App
              </label>
              <input
                v-model="appleAppPassword"
                type="password"
                placeholder="xxxx-xxxx-xxxx-xxxx"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              />
              <p class="text-[10px] text-slate-500 mt-1">Gerada em appleid.apple.com</p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Servidor CalDAV
              </label>
              <input
                v-model="appleServerUrl"
                type="text"
                class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div class="flex items-center justify-end">
            <button
              type="submit"
              :disabled="savingApple"
              class="px-5 py-2.5 rounded-xl font-bold text-xs text-slate-950 bg-emerald-400 hover:bg-emerald-300 disabled:opacity-50 transition shadow-md shadow-emerald-400/20"
            >
              {{ savingApple ? 'Salvando & Validando...' : 'Salvar CalDAV no Cofre' }}
            </button>
          </div>
        </form>
      </section>

      <!-- 4. Apple Shortcuts Webhook (Atalhos do iOS) -->
      <section class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-pink-400 font-black text-lg">
              ⚡
            </div>
            <div>
              <h2 class="text-base font-bold text-white flex items-center space-x-2">
                <span>Apple Shortcuts Webhook (Atalhos iPhone & Siri)</span>
                <span
                  class="px-2 py-0.5 text-[10px] font-bold rounded-full border"
                  :class="shortcutsIntegration?.is_active
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-400 border-slate-700'"
                >
                  {{ shortcutsIntegration?.is_active ? 'Webhook Ativo' : 'Sem Token Gerado' }}
                </span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Permite enviar tarefas por voz pela Siri ou pelo app Atalhos do iPhone para o Kanban do ABVOS.
              </p>
            </div>
          </div>

          <button
            @click="generateShortcutsToken"
            :disabled="generatingShortcutsToken"
            class="px-4 py-2 text-xs font-bold rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 transition shadow-md shadow-indigo-600/20"
          >
            {{ generatingShortcutsToken ? 'Gerando...' : 'Gerar / Rotacionar Token' }}
          </button>
        </div>

        <div v-if="shortcutsTokenGenerated" class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Novo Token de Webhook (Copie Agora):</span>
            <button
              @click="copyToClipboard(shortcutsTokenGenerated)"
              class="text-xs font-bold text-emerald-300 hover:underline"
            >
              Copiar Token
            </button>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-950 font-mono text-xs text-slate-200 break-all border border-slate-800">
            {{ shortcutsTokenGenerated }}
          </div>
          <div class="text-[11px] text-slate-400">
            URL do Webhook: <strong class="text-slate-200">{{ shortcutsWebhookUrl }}</strong>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-800/80 text-xs text-slate-400 space-y-2">
          <p class="font-semibold text-slate-300">Como usar no app Atalhos do iPhone:</p>
          <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300">
            POST https://sua-vps.com/api/webhooks/shortcuts<br />
            Header: X-Shortcut-Token: seu_token_aqui<br />
            Body JSON: {"action": "capture_task", "title": "Ideia gravada via voz"}
          </div>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

