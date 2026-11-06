<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSwal } from '@/composables/useSwal'

const router = useRouter()
const authStore = useAuthStore()
const swal = useSwal()

const name = ref('')
const email = ref('')
const password = ref('')
const passwordConfirmation = ref('')
const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Sao_Paulo')
const errorMessage = ref('')
const errors = ref({})

async function handleSubmit() {
  errorMessage.value = ''
  errors.value = {}

  if (password.value !== passwordConfirmation.value) {
    errorMessage.value = 'As senhas não coincidem.'
    return
  }

  try {
    await authStore.register({
      name: name.value,
      email: email.value,
      password: password.value,
      password_confirmation: passwordConfirmation.value,
      timezone: timezone.value,
    })
    swal.toast('Conta criada com sucesso! Bem-vindo ao SpirandeliEmpire.', 'success')
    router.push('/')
  } catch (err) {
    if (err.response?.status === 422 && err.response?.data?.errors) {
      errors.value = err.response.data.errors
      errorMessage.value = 'Por favor, corrija os erros abaixo.'
    } else {
      errorMessage.value = err.response?.data?.message || 'Falha ao registrar conta.'
    }
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
        <h1 class="text-xl font-bold text-white tracking-tight">Criar Conta Executiva</h1>
        <p class="text-xs text-slate-400 mt-1">SpirandeliEmpire · Operação Privada</p>
      </div>

      <!-- Erro Geral -->
      <div v-if="errorMessage" class="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
        {{ errorMessage }}
      </div>

      <!-- Formulário -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Nome Completo
          </label>
          <input
            v-model="name"
            type="text"
            required
            placeholder="Ex: Alexander Spirandeli"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
          />
          <p v-if="errors.name" class="mt-1 text-xs text-rose-400">{{ errors.name[0] }}</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            E-mail Executivo
          </label>
          <input
            v-model="email"
            type="email"
            required
            placeholder="seu@dominio.com"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
          />
          <p v-if="errors.email" class="mt-1 text-xs text-rose-400">{{ errors.email[0] }}</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Senha (Mín. 10 chars, maiúsculas & números)
          </label>
          <input
            v-model="password"
            type="password"
            required
            placeholder="••••••••••"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
          />
          <p v-if="errors.password" class="mt-1 text-xs text-rose-400">{{ errors.password[0] }}</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            Confirmar Senha
          </label>
          <input
            v-model="passwordConfirmation"
            type="password"
            required
            placeholder="••••••••••"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition"
          />
        </div>

        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full mt-2 py-3 px-4 rounded-xl font-semibold text-sm text-slate-950 bg-gradient-to-r from-emerald-400 to-emerald-500 hover:from-emerald-300 hover:to-emerald-400 disabled:opacity-50 transition shadow-lg shadow-emerald-500/20 flex items-center justify-center space-x-2"
        >
          <span v-if="authStore.loading" class="animate-spin h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full"></span>
          <span>{{ authStore.loading ? 'Criando conta...' : 'Cadastrar e Acessar' }}</span>
        </button>
      </form>

      <!-- Footer -->
      <div class="mt-6 text-center text-xs text-slate-400">
        Já possui acesso?
        <router-link to="/login" class="text-emerald-400 hover:underline font-semibold ml-1">
          Fazer Login
        </router-link>
      </div>
    </div>
  </div>
</template>

