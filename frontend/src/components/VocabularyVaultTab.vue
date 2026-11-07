<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'

const languageStore = useLanguageStore()
const swal = useSwal()

const searchTerm = ref('')
const selectedLevel = ref('all')

onMounted(async () => {
  await languageStore.fetchVault()
})

const vaultItems = computed(() => languageStore.vaultItems)
const stats = computed(() => languageStore.vaultStats)

const filteredItems = computed(() => {
  return vaultItems.value.filter((item) => {
    const matchesSearch =
      item.term_or_phrase.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
      item.translation.toLowerCase().includes(searchTerm.value.toLowerCase())

    const matchesLevel =
      selectedLevel.value === 'all' ||
      (selectedLevel.value === 'mastered' && item.mastery_level === 5) ||
      (selectedLevel.value === 'learning' && item.mastery_level < 5)

    return matchesSearch && matchesLevel
  })
})

async function openAddWordModal() {
  const { value: formValues } = await swal.instance.fire({
    title: 'Adicionar Termo ao Cofre SRS',
    html: `
      <div class="text-left text-xs text-slate-300 space-y-3 font-sans">
        <div>
          <label class="block font-bold text-slate-200 mb-1">Palavra ou Expressão no Idioma:</label>
          <input id="swal-word-term" class="swal2-input !bg-slate-900 !text-white !border-slate-700 !rounded-xl !text-sm !w-full !m-0" placeholder="Ex: Touch base">
        </div>
        <div>
          <label class="block font-bold text-slate-200 mb-1">Tradução / Significado Prático:</label>
          <input id="swal-word-trans" class="swal2-input !bg-slate-900 !text-white !border-slate-700 !rounded-xl !text-sm !w-full !m-0" placeholder="Ex: Entrar em contato brevemente para alinhar">
        </div>
        <div>
          <label class="block font-bold text-slate-200 mb-1">Frase de Contexto (Opcional):</label>
          <textarea id="swal-word-example" rows="2" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-white text-xs placeholder-slate-500 focus:outline-none" placeholder="Ex: Let's touch base next Monday before the board meeting."></textarea>
        </div>
      </div>
    `,
    focusConfirm: false,
    showCancelButton: true,
    confirmButtonText: 'Adicionar ao Cofre',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#10b981',
    cancelButtonColor: '#334155',
    background: '#0f172a',
    color: '#f8fafc',
    preConfirm: () => {
      const term = document.getElementById('swal-word-term').value
      const translation = document.getElementById('swal-word-trans').value
      const example = document.getElementById('swal-word-example').value
      if (!term || !translation) {
        swal.instance.showValidationMessage('Informe a palavra e a tradução.')
        return false
      }
      return { term_or_phrase: term, translation, context_example: example }
    },
  })

  if (formValues) {
    try {
      await languageStore.addVaultWord(formValues)
      swal.toast('Termo adicionado à fila de repetição espaçada!', 'success')
    } catch (err) {
      swal.error('Erro ao adicionar', err.response?.data?.message || 'Falha ao salvar termo.')
    }
  }
}

async function handleDeleteWord(item) {
  const confirmed = await swal.confirm({
    title: `Remover "${item.term_or_phrase}"?`,
    text: 'Este termo sairá do seu banco de repetição espaçada.',
    confirmText: 'Sim, remover',
    confirmButtonColor: '#e11d48',
  })

  if (confirmed) {
    await languageStore.deleteVaultWord(item.id)
    swal.toast('Palavra removida do cofre.', 'success')
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Métricas do Cofre SRS -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
        <span class="text-[10px] uppercase font-mono font-bold text-slate-400 block">Total no Cofre</span>
        <span class="text-2xl font-black font-mono text-white">{{ stats.total }}</span>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
        <span class="text-[10px] uppercase font-mono font-bold text-emerald-400 block">Dominadas (Nível 5)</span>
        <span class="text-2xl font-black font-mono text-emerald-400">{{ stats.mastered }}</span>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
        <span class="text-[10px] uppercase font-mono font-bold text-amber-400 block">Em Aprendizado</span>
        <span class="text-2xl font-black font-mono text-amber-400">{{ stats.learning }}</span>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
        <span class="text-[10px] uppercase font-mono font-bold text-indigo-400 block">A Revisar Hoje</span>
        <span class="text-2xl font-black font-mono text-indigo-400">{{ stats.due_today }}</span>
      </div>
    </div>

    <!-- Barra de Filtros e Busca -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex items-center space-x-3 flex-1">
        <div class="relative flex-1 max-w-md">
          <input
            v-model="searchTerm"
            type="text"
            placeholder="Buscar por termo ou tradução..."
            class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <select
          v-model="selectedLevel"
          class="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none"
        >
          <option value="all">Todos os Níveis</option>
          <option value="learning">Em Aprendizado (&lt; 5)</option>
          <option value="mastered">Dominadas (Nível 5)</option>
        </select>
      </div>

      <button
        type="button"
        @click="openAddWordModal"
        class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20 transition flex items-center justify-center space-x-2 shrink-0"
      >
        <span>+ Adicionar Termo</span>
      </button>
    </div>

    <!-- Lista de Termos -->
    <div v-if="filteredItems.length === 0" class="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-2xl space-y-2">
      <span class="text-3xl block">📦</span>
      <h4 class="font-bold text-sm text-slate-300">Nenhum termo encontrado no cofre</h4>
      <p class="text-xs text-slate-500 max-w-sm mx-auto">
        As palavras e expressões que você errar ou aprender nas sessões de 15 minutos com o Gemini 3.8 Flash entrarão aqui automaticamente.
      </p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 shadow-sm space-y-3 transition group flex flex-col justify-between"
      >
        <div class="space-y-1.5">
          <div class="flex items-start justify-between">
            <h4 class="font-bold text-sm text-white">{{ item.term_or_phrase }}</h4>
            <button
              type="button"
              @click="handleDeleteWord(item)"
              class="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 transition text-xs p-1"
              title="Remover do cofre"
            >
              ✕
            </button>
          </div>

          <p class="text-xs text-emerald-400 font-medium">{{ item.translation }}</p>

          <p v-if="item.context_example" class="text-[11px] text-slate-400 italic pt-1 font-serif line-clamp-2">
            "{{ item.context_example }}"
          </p>
        </div>

        <div class="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono">
          <!-- Maestria SRS (1 a 5) -->
          <div class="flex items-center space-x-1" :title="`Nível de Maestria: ${item.mastery_level}/5`">
            <span
              v-for="star in 5"
              :key="star"
              class="w-2 h-2 rounded-full"
              :class="star <= item.mastery_level ? 'bg-amber-400' : 'bg-slate-800'"
            ></span>
          </div>

          <span class="text-slate-500">
            Revisão: {{ item.next_review_date }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
