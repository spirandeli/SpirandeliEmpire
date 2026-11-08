<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/services/api'
import { useSwal } from '@/composables/useSwal'
import AppLayout from '@/components/AppLayout.vue'
import CalendarSyncModal from '@/components/CalendarSyncModal.vue'

const swal = useSwal()

// Estado do Modal de Sincronização
const isCalendarModalOpen = ref(false)
const selectedEvent = ref(null)
const userFeedUrl = ref('')
const loading = ref(false)

// Formulário simples de novo agendamento para demonstrar o Gatilho 1
const appointmentForm = ref({
  title: 'Reunião de Alinhamento Estratégico',
  description: 'Discussão de KPIs e expansão da operação internacional.',
  location: 'Google Meet',
  starts_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
  duration_minutes: 45,
})

onMounted(async () => {
  await fetchUserCalendarFeed()
})

/**
 * Obtém a URL oficial do feed iCal RFC 5545 do usuário autenticado
 */
async function fetchUserCalendarFeed() {
  try {
    const response = await api.get('/v1/calendar/me/feed-url')
    userFeedUrl.value = response.data.feed_url
  } catch (err) {
    console.error('Erro ao recuperar feed URL:', err)
    // Fallback gracioso
    userFeedUrl.value = `${window.location.origin}/api/v1/calendar/feed/default-user.ics`
  }
}

/**
 * GATILHO 1: Contexto de Evento Único (Pós-Agendamento)
 * Disparado automaticamente no callback de sucesso após o usuário criar um agendamento.
 */
async function handleCreateAppointment() {
  if (!appointmentForm.value.title?.trim()) {
    swal.error('Campo obrigatório', 'Por favor, informe o título do agendamento.')
    return
  }

  loading.value = true
  try {
    const startDate = new Date(appointmentForm.value.starts_at)
    const endDate = new Date(startDate.getTime() + appointmentForm.value.duration_minutes * 60 * 1000)

    // Simula ou envia a criação do evento no backend
    // const response = await api.post('/appointments', payload)
    const createdEvent = {
      id: Math.floor(Math.random() * 9000) + 1000,
      title: appointmentForm.value.title,
      description: appointmentForm.value.description,
      location: appointmentForm.value.location,
      start_at: startDate.toISOString(),
      end_at: endDate.toISOString(),
      download_url: `/api/v1/calendar/events/${Math.floor(Math.random() * 9000) + 1000}/download`,
    }

    swal.toast('Agendamento salvo com sucesso!', 'success')

    // Dispara automaticamente o modal com os dados do evento recém-criado
    selectedEvent.value = createdEvent
    isCalendarModalOpen.value = true
  } catch (err) {
    swal.error('Erro ao agendar', err.message || 'Falha ao salvar agendamento.')
  } finally {
    loading.value = false
  }
}

/**
 * GATILHO 2: Contexto Geral (Painel do Usuário / Configurações)
 * Disparado manualmente pelo usuário sem nenhum evento específico associado.
 */
function handleOpenGeneralSync() {
  selectedEvent.value = null // Nulo para foco exclusivo na assinatura do feed webcal/Google
  isCalendarModalOpen.value = true
}
</script>

<template>
  <AppLayout>
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <!-- Header do Painel -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <span class="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider block mb-1">
            Zero-Auth iCalendar Integration (RFC 5545)
          </span>
          <h1 class="text-2xl font-black text-white tracking-tight">Painel de Agendamentos & Calendário</h1>
          <p class="text-xs text-slate-400 mt-1">
            Demonstração dos dois cenários de UX: pós-agendamento (evento único) e sincronização global da agenda.
          </p>
        </div>

        <!-- GATILHO 2: Botão Geral no Topo do Painel -->
        <button
          type="button"
          @click="handleOpenGeneralSync"
          class="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 text-slate-200 text-xs font-bold transition shadow-sm self-start sm:self-auto"
        >
          <span>📅</span>
          <span>Sincronizar Calendário</span>
        </button>
      </div>

      <!-- Formulário de Exemplo para Testar o Gatilho 1 (Pós-Agendamento) -->
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-5">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <span class="text-lg">⚡</span>
            <h2 class="text-sm font-bold text-white">Criar Novo Agendamento (Gatilho 1)</h2>
          </div>
          <span class="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            Abre modal pós-sucesso
          </span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1 sm:col-span-2">
            <label class="block text-xs font-mono text-slate-300 font-bold">Título da Reunião / Agendamento:</label>
            <input
              v-model="appointmentForm.title"
              type="text"
              class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-mono text-slate-300 font-bold">Data e Horário de Início:</label>
            <input
              v-model="appointmentForm.starts_at"
              type="datetime-local"
              class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-mono text-slate-300 font-bold">Duração Estimada:</label>
            <select
              v-model="appointmentForm.duration_minutes"
              class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
            >
              <option :value="15">15 minutos (Micro-meeting)</option>
              <option :value="30">30 minutos</option>
              <option :value="45">45 minutos</option>
              <option :value="60">1 hora</option>
            </select>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <label class="block text-xs font-mono text-slate-300 font-bold">Local / Link:</label>
            <input
              v-model="appointmentForm.location"
              type="text"
              class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        <div class="pt-2 flex justify-end">
          <button
            type="button"
            :disabled="loading"
            @click="handleCreateAppointment"
            class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
          >
            <span>Salvar Agendamento & Testar Modal</span>
            <span>→</span>
          </button>
        </div>
      </div>

      <!-- Explicação Arquitetural da Integração Zero-Auth -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        <div class="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <h4 class="font-bold text-slate-200 flex items-center space-x-2">
            <span>🍏</span>
            <span>Apple Calendar (iOS / macOS)</span>
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Utiliza o protocolo nativo <code class="text-indigo-400">webcal://</code>. O clique dispara a caixa de diálogo nativa do sistema operacional para assinar o feed sem nenhuma etapa de login.
          </p>
        </div>

        <div class="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <h4 class="font-bold text-slate-200 flex items-center space-x-2">
            <span>🌐</span>
            <span>Google Agenda (Web / Android)</span>
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Para evento único, cria a URL de template instantânea preenchida. Para a agenda completa, fornece a URL pública stateless assinável em <em>"Adicionar agenda &rarr; Do URL"</em>.
          </p>
        </div>
      </div>
    </div>

    <!-- O Componente Reutilizável de Sincronização de Calendário -->
    <CalendarSyncModal
      v-model="isCalendarModalOpen"
      :feed-url="userFeedUrl"
      :event="selectedEvent"
    />
  </AppLayout>
</template>

