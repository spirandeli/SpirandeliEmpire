<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useBusinessStore } from '@/stores/business'
import { useSwal } from '@/composables/useSwal'
import AgentChatDrawer from '@/components/AgentChatDrawer.vue'

const router = useRouter()
const businessStore = useBusinessStore()
const swal = useSwal()

const showCreateModal = ref(false)
const isChatDrawerOpen = ref(false)
const newBiz = ref({
  name: '',
  niche: '',
  archetype: 'affiliate_tiktok',
  business_model: 'tiktok_shop_affiliate',
  north_star_metric: 'commission_volume',
  target_kpi_value: 5000,
  description: '',
  target_audience: '',
  tone_of_voice: 'Persuasivo, dinâmico e focado em benefícios imediatos',
})

onMounted(async () => {
  await businessStore.fetchBusinesses()
})

async function handleCreate() {
  if (!newBiz.value.name.trim()) return

  try {
    const created = await businessStore.createBusiness({
      name: newBiz.value.name,
      niche: newBiz.value.niche,
      archetype: newBiz.value.archetype,
      type: newBiz.value.archetype === 'affiliate_tiktok' ? 'tiktok_shop_affiliate' : 'custom',
      north_star_metric: newBiz.value.north_star_metric,
      target_kpi_value: newBiz.value.target_kpi_value,
      description: newBiz.value.description,
      brand_guidelines: {
        target_audience: newBiz.value.target_audience,
        tone_of_voice: newBiz.value.tone_of_voice,
      },
      canvas: {
        value_propositions: ['Produtos e ofertas validadas com alto retorno sobre investimento'],
        revenue_streams: ['Receitas diretas parametrizadas via webhooks'],
      },
    })
    swal.toast('Novo venture criado com sucesso!', 'success')
    showCreateModal.value = false
    newBiz.value = {
      name: '',
      niche: '',
      archetype: 'affiliate_tiktok',
      business_model: 'tiktok_shop_affiliate',
      north_star_metric: 'commission_volume',
      target_kpi_value: 5000,
      description: '',
      target_audience: '',
      tone_of_voice: 'Persuasivo, dinâmico e focado em benefícios imediatos',
    }
    router.push(`/businesses/${created.id}`)
  } catch (err) {
    swal.error('Erro ao criar negócio', err.response?.data?.message || err.message)
  }
}

async function handleToggleStatus(biz) {
  try {
    if (biz.status === 'active') {
      await businessStore.pauseBusiness(biz.id)
      swal.toast(`Venture "${biz.name}" pausado. Workers em stand-by.`, 'info')
    } else {
      await businessStore.activateBusiness(biz.id)
      swal.toast(`Venture "${biz.name}" ativado com sucesso!`, 'success')
    }
  } catch (err) {
    swal.error('Erro ao alterar status', err.response?.data?.message || err.message)
  }
}

async function handleDelete(biz) {
  const confirmed = await swal.confirm({
    title: `Excluir "${biz.name}"?`,
    text: 'Todas as tarefas, produtos minerados e automações deste negócio serão apagadas permanentemente.',
    confirmText: 'Sim, excluir negócio',
    confirmButtonColor: '#ef4444',
  })

  if (!confirmed) return

  try {
    await businessStore.deleteBusiness(biz.id)
    swal.toast('Negócio excluído com sucesso.', 'info')
  } catch (err) {
    swal.error('Erro ao excluir', err.response?.data?.message || err.message)
  }
}
</script>

<template>
  <AppLayout>
    <template #header>
      <div class="flex items-center justify-between w-full">
        <div>
          <h1 class="text-xl font-bold text-white tracking-tight">Hub de Negócios & Ventures</h1>
          <p class="text-xs text-slate-400 mt-0.5">Gestão de Empresas Digitais Autônomas</p>
        </div>
        <div class="flex items-center space-x-3">
          <button
            @click="isChatDrawerOpen = true"
            class="px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 shadow-lg shadow-indigo-600/20 transition flex items-center space-x-2"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Co-Criar com COO IA</span>
          </button>
          <button
            @click="showCreateModal = true"
            class="px-4 py-2 rounded-xl text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-lg shadow-emerald-400/20 transition flex items-center space-x-1.5"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Novo Venture</span>
          </button>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Loading -->
      <div v-if="businessStore.loading && businessStore.businesses.length === 0" class="p-12 text-center text-slate-400 text-sm">
        Carregando negócios operacionais...
      </div>

      <!-- Grid de Negócios -->
      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          v-for="biz in businessStore.businesses"
          :key="biz.id"
          class="rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between overflow-hidden group shadow-lg shadow-black/20"
        >
          <div class="p-6">
            <!-- Top Tags -->
            <div class="flex items-center justify-between">
              <span class="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                {{ biz.business_model || 'TikTok Shop Affiliate' }}
              </span>
              <span
                class="px-2 py-0.5 text-[10px] font-bold rounded-full border flex items-center space-x-1"
                :class="biz.status === 'active'
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="biz.status === 'active' ? 'bg-emerald-400' : 'bg-slate-500'"></span>
                <span>{{ biz.status === 'active' ? 'Ativo' : 'Pausado' }}</span>
              </span>
            </div>

            <!-- Title & Description -->
            <h3 class="text-lg font-bold text-white mt-4 group-hover:text-emerald-400 transition">
              {{ biz.name }}
            </h3>
            <p class="text-xs text-slate-400 mt-1.5 line-clamp-3 leading-relaxed">
              {{ biz.description || 'Nenhuma descrição detalhada. O modelo foi gerado com regras autônomas.' }}
            </p>

            <!-- Nicho & Público -->
            <div class="mt-4 pt-4 border-t border-slate-800/80 space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-500 font-medium">Nicho / Vertical:</span>
                <span class="text-slate-200 font-semibold">{{ biz.niche || 'Geral' }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-500 font-medium">Automações Ativas:</span>
                <span class="text-indigo-400 font-semibold">{{ biz.automations_count || biz.automations?.length || 2 }} regras ativas</span>
              </div>
            </div>
          </div>

          <!-- Bottom Footer Actions -->
          <div class="px-6 py-4 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <button
                @click="handleToggleStatus(biz)"
                class="p-2 text-xs rounded-xl border transition"
                :class="biz.status === 'active'
                  ? 'bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20'
                  : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20'"
                :title="biz.status === 'active' ? 'Pausar Venture' : 'Ativar Venture'"
              >
                <svg v-if="biz.status === 'active'" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>

              <button
                @click="handleDelete(biz)"
                class="p-2 text-xs rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition"
                title="Excluir"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>

            <router-link
              :to="`/businesses/${biz.id}`"
              class="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1"
            >
              <span>Acessar Hub</span>
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Criação Rápida de Negócio -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div class="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-white">Lançar Novo Venture Digital</h3>
          <button @click="showCreateModal = false" class="text-slate-400 hover:text-white">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="handleCreate" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Nome do Negócio</label>
            <input
              v-model="newBiz.name"
              type="text"
              required
              placeholder="Ex: Gadgets Virais Brasil"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Nicho / Categoria</label>
              <input
                v-model="newBiz.niche"
                type="text"
                required
                placeholder="Ex: Utilidades & Tech"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Arquétipo do Negócio</label>
              <select
                v-model="newBiz.archetype"
                class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="affiliate_tiktok">Afiliados & TikTok Shop Viral</option>
                <option value="infoproduct">Infoprodutos & Lançamentos</option>
                <option value="saas">SaaS & Assinaturas Recorrentes</option>
                <option value="ecommerce">E-commerce & Dropshipping Direto</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Descrição & Proposta</label>
            <textarea
              v-model="newBiz.description"
              rows="2"
              placeholder="Descreva o propósito da operação..."
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            ></textarea>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Tom de Voz da Marca (Brand Tone)</label>
            <input
              v-model="newBiz.tone_of_voice"
              type="text"
              placeholder="Ex: Persuasivo, enérgico e focado em dores reais"
              class="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div class="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-xl transition shadow-md shadow-emerald-400/20"
            >
              Criar e Configurar
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Drawer de Chat com COO IA -->
    <AgentChatDrawer
      :is-open="isChatDrawerOpen"
      @close="isChatDrawerOpen = false"
    />
  </AppLayout>
</template>

