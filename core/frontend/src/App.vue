<template>
  <div
    class="relative flex h-screen w-screen overflow-hidden select-none p-2.5 sm:p-3.5 gap-3 sm:gap-4 bg-[#1a2e12] bg-cover bg-center"
    style="background-image: url('/assets/rpg-village-bg.jpg');"
  >
    <!-- Subtle warm vignette so UI panels pop clearly over the village -->
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/25 z-0"></div>

    <!-- RPG FORTRESS LOGIN GATE -->
    <div
      v-if="!isAuthenticated"
      class="relative z-30 flex-1 flex items-center justify-center p-4 bg-black/45 backdrop-blur-[2px] -m-3.5"
    >
      <div class="w-full max-w-md pixel-wood rpg-rivets p-4 shadow-2xl">
        <div class="pixel-wood-inset p-3.5 mb-3 flex items-center gap-3">
          <div class="w-14 h-14 shrink-0 rounded bg-[#3b200e] border-2 border-[#f59e0b] overflow-hidden flex items-center justify-center shadow-md">
            <img src="/assets/sprites/avatar.png" alt="Comandante" class="w-full h-full object-cover" />
          </div>
          <div>
            <span class="rpg-ribbon mb-1">
              {{ authSetupRequired ? '🛡️ 1º ACESSO: CRIAR SENHA' : '🔒 PORTÃO SOBERANO' }}
            </span>
            <h1 class="font-extrabold text-sm sm:text-base text-[#fff7e6] uppercase rpg-text-outline-sm">
              SPIRANDELIEMPIRE OS
            </h1>
            <p class="text-[11px] text-[#d9bc8c]">
              {{ authSetupRequired ? 'Defina seu e-mail e senha para trancar o império' : 'Acesso restrito ao Comandante Soberano' }}
            </p>
          </div>
        </div>

        <form @submit.prevent="submitLogin" class="rpg-parchment-inner p-4 space-y-3 text-xs font-bold text-[#2b1507]">
          <div
            v-if="authSetupRequired"
            class="p-2.5 rounded bg-[#fef3c7] border-2 border-[#d97706] text-[11px] text-[#78350f] leading-snug"
          >
            ⚔️ <strong>Primeiro Acesso Detectado:</strong> Cadastre seu e-mail e senha abaixo. A partir deste momento o site ficará 100% blindado com esta senha.
          </div>

          <div
            v-if="loginError"
            class="p-2.5 rounded bg-red-100 border-2 border-red-600 text-[11px] text-red-900 leading-snug"
          >
            ⚠️ {{ loginError }}
          </div>

          <div v-if="authSetupRequired">
            <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Título / Nome do Comandante</label>
            <input
              v-model="loginForm.name"
              type="text"
              placeholder="Comandante Spirandeli"
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
            />
          </div>

          <div>
            <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">E-mail de Comando *</label>
            <input
              v-model="loginForm.email"
              type="email"
              required
              autocomplete="username"
              placeholder="admin@spirandeliempire.tech"
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
            />
          </div>

          <div>
            <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Senha Secreta *</label>
            <input
              v-model="loginForm.password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="••••••••••••"
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
            />
          </div>

          <div class="pt-2">
            <button
              type="submit"
              :disabled="loggingIn"
              class="pixel-btn-gold w-full py-2.5 px-4 text-xs uppercase flex items-center justify-center gap-2"
            >
              <span v-if="loggingIn">Verificando selo real...</span>
              <span v-else>{{ authSetupRequired ? '🔐 Salvar Senha & Entrar no Império →' : '🗝️ Destrancar Command Center →' }}</span>
            </button>
          </div>
        </form>

        <div class="mt-2.5 text-center text-[10px] text-[#d9bc8c] flex items-center justify-between px-1">
          <span>🛡️ Criptografia HMAC-SHA256 Ativa</span>
          <span>Teto: R$ 200/mês</span>
        </div>
      </div>
    </div>

    <template v-else>
      <!-- Left Column: Profile + RPG Sidebar + Bottom Jeffrey Status -->
      <Sidebar class="relative z-20 shrink-0" />

      <!-- Right Column: Top Server Bar + Main Content Area -->
      <div class="relative z-10 flex-1 flex flex-col min-w-0 h-full overflow-hidden gap-3">
        <Header class="shrink-0" @logout="logoutCommander" />
        <main class="flex-1 overflow-y-auto pr-1 pb-6">
          <router-view />
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import Sidebar from './components/Sidebar.vue'
import Header from './components/Header.vue'

const isAuthenticated = ref(false)
const authSetupRequired = ref(false)
const loggingIn = ref(false)
const loginError = ref('')
const loginForm = ref({
  name: 'Comandante Spirandeli',
  email: '',
  password: '',
})

const applyAuthToken = (token) => {
  if (token) {
    localStorage.setItem('empire_auth_token', token)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    localStorage.removeItem('empire_auth_token')
    delete axios.defaults.headers.common['Authorization']
  }
}

axios.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401 && !err.config?.url?.includes('/auth/login')) {
      applyAuthToken(null)
      isAuthenticated.value = false
    }
    return Promise.reject(err)
  }
)

const checkAuthSession = async () => {
  try {
    const stRes = await axios.get('/api/v1/auth/status')
    if (stRes.data) {
      authSetupRequired.value = !!stRes.data.setup_required
      if (!loginForm.value.email && stRes.data.default_email) {
        loginForm.value.email = stRes.data.default_email
      }
    }
  } catch (_) {}

  const savedToken = localStorage.getItem('empire_auth_token')
  if (!savedToken) {
    isAuthenticated.value = false
    return
  }

  applyAuthToken(savedToken)
  try {
    const meRes = await axios.get('/api/v1/auth/me')
    if (meRes.data?.user) {
      isAuthenticated.value = true
    } else {
      applyAuthToken(null)
      isAuthenticated.value = false
    }
  } catch (_) {
    applyAuthToken(null)
    isAuthenticated.value = false
  }
}

const submitLogin = async () => {
  loginError.value = ''
  loggingIn.value = true
  try {
    const res = await axios.post('/api/v1/auth/login', {
      name: loginForm.value.name,
      email: loginForm.value.email,
      password: loginForm.value.password,
    })
    if (res.data?.token) {
      applyAuthToken(res.data.token)
      authSetupRequired.value = false
      isAuthenticated.value = true
      loginForm.value.password = ''
    }
  } catch (err) {
    loginError.value =
      err.response?.data?.error ||
      err.response?.data?.message ||
      'Credenciais inválidas. Verifique seu e-mail e senha.'
  } finally {
    loggingIn.value = false
  }
}

const logoutCommander = async () => {
  try {
    await axios.post('/api/v1/auth/logout')
  } catch (_) {}
  applyAuthToken(null)
  isAuthenticated.value = false
}

onMounted(() => {
  checkAuthSession()
})
</script>
