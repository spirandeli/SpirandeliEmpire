<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSwal } from '@/composables/useSwal'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const swal = useSwal()

const email = ref('')
const password = ref('')
const remember = ref(true)
const errorMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''
  try {
    await authStore.login(email.value, password.value, remember.value)
    swal.toast('Login realizado com sucesso!')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    const data = err.response?.data || {}
    errorMessage.value = data.errors?.email?.[0]
      || data.detail?.errors?.email?.[0]
      || data.message
      || (typeof data.detail === 'string' ? data.detail : null)
      || data.detail?.message
      || 'Credenciais inválidas. Verifique seu e-mail e senha.'
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8">
      <!-- Header -->
      <div class="text-center mb-8">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-black text-white text-xl mx-auto shadow-lg shadow-emerald-500/20 mb-3">
          S
        </div>
        <h1 class="text-2xl font-black text-white tracking-tight">SpirandeliEmpire</h1>
        <p class="text-xs text-slate-400 mt-1">Acesso Executivo · Gemini 3.8 Co-Pilot</p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
        {{ errorMessage }}
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1.5">E-mail corporativo</label>
          <input
            v-model="email"
            type="email"
            required
            placeholder="seu@email.com"
            class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
          />
        </div>

        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="block text-xs font-semibold text-slate-300">Senha de acesso</label>
          </div>
          <input
            v-model="password"
            type="password"
            required
            placeholder="••••••••••••"
            class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
          />
        </div>

        <div class="flex items-center justify-between text-xs text-slate-400 pt-1">
          <label class="flex items-center space-x-2 cursor-pointer">
            <input v-model="remember" type="checkbox" class="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0" />
            <span>Lembrar sessão</span>
          </label>
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-semibold text-sm text-white shadow-lg shadow-emerald-600/20 transition transform active:scale-98 disabled:opacity-50 mt-2"
        >
          {{ authStore.loading ? 'Autenticando...' : 'Entrar no Sistema' }}
        </button>
      </form>

      <div class="mt-6 text-center text-xs text-slate-400">
        Não tem conta?
        <RouterLink to="/register" class="text-emerald-400 hover:text-emerald-300 font-semibold transition ml-1">
          Criar conta
        </RouterLink>
      </div>
    </div>
  </div>
</template>

