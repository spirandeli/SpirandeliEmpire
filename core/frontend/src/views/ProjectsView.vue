<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="bg-slate-900/90 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Workspaces & Projetos
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
            {{ projects.length }} Registrados
          </span>
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Projetos autorizados para análise de código, execução de testes e controle Git por Jeffrey
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="fetchProjects"
          :disabled="loading"
          class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg border border-slate-700 transition flex items-center gap-1.5"
        >
          <span :class="{'animate-spin': loading}">↻</span> Atualizar
        </button>
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg transition font-mono shadow-md"
        >
          + Novo Projeto
        </button>
      </div>
    </div>

    <!-- Projects Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="proj in projects"
        :key="proj.id"
        class="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 flex flex-col justify-between shadow-xl"
      >
        <div>
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-cyan-400 font-semibold border border-slate-700 uppercase">
              {{ proj.stack || 'General' }}
            </span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-bold">
              {{ proj.status }}
            </span>
          </div>

          <h3 class="text-lg font-bold text-slate-100">{{ proj.name }}</h3>
          <p class="text-xs text-slate-400 mt-2 leading-relaxed">{{ proj.description }}</p>

          <div class="mt-4 p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 text-xs font-mono space-y-1.5">
            <div class="flex justify-between">
              <span class="text-slate-500">Caminho Workspace:</span>
              <span class="text-slate-300 truncate max-w-[200px]" :title="proj.path">{{ proj.path }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Branch Git:</span>
              <span class="text-amber-400 font-semibold">{{ proj.git_branch || 'main' }}</span>
            </div>
          </div>
        </div>

        <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2">
          <button
            @click="inspectProject(proj)"
            class="px-3 py-1.5 text-xs font-mono rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            Inspecionar Pastas & Git ↗
          </button>
          <router-link
            to="/jeffrey"
            class="px-3 py-1.5 text-xs font-mono rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 transition"
          >
            Pedir Análise a Jeffrey
          </router-link>
        </div>
      </div>
    </div>

    <!-- Project Inspection Modal -->
    <div v-if="inspectedProject" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full flex flex-col max-h-[85vh] shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 class="text-sm font-bold text-cyan-400 font-mono">
              Workspace: {{ inspectedProject.name }}
            </h3>
            <div class="text-[10px] text-slate-500 font-mono mt-0.5">
              Branch: {{ inspectedGit?.branch }} • Status: {{ inspectedGit?.status }}
            </div>
          </div>
          <button @click="inspectedProject = null" class="text-slate-500 hover:text-white p-1 text-sm font-bold">
            ✕
          </button>
        </div>

        <div class="flex-1 overflow-y-auto my-4 space-y-4 font-mono text-xs">
          <!-- Files List -->
          <div>
            <div class="text-slate-400 font-bold mb-2 uppercase text-[11px]">Pastas & Arquivos no Workspace</div>
            <div v-if="loadingFiles" class="text-slate-500 text-center py-4">Inspecionando diretório...</div>
            <div v-else class="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
              <div v-for="dir in projectFiles.directories" :key="dir" class="text-amber-400 flex items-center gap-1.5">
                <span>📁</span> <span>{{ dir }}/</span>
              </div>
              <div v-for="file in projectFiles.files" :key="file.name" class="text-slate-300 flex items-center justify-between text-[11px]">
                <span class="flex items-center gap-1.5">
                  <span>📄</span> <span>{{ file.name }}</span>
                </span>
                <span class="text-slate-500">{{ (file.size / 1024).toFixed(1) }} KB</span>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-2 border-t border-slate-800">
          <button
            @click="inspectedProject = null"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>

    <!-- Create Project Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
        <h3 class="text-sm font-bold text-amber-400 font-mono uppercase">Cadastrar Novo Projeto</h3>
        <div class="space-y-3 text-xs font-mono">
          <div>
            <label class="block text-slate-400 mb-1">Nome do Projeto *</label>
            <input
              v-model="createForm.name"
              type="text"
              placeholder="Ex: Landing Page Nova"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Caminho no Servidor (Path) *</label>
            <input
              v-model="createForm.path"
              type="text"
              placeholder="/var/spirandeli/businesses/novo"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Stack Tecnológica</label>
            <input
              v-model="createForm.stack"
              type="text"
              placeholder="Ex: laravel+vue, python, nodejs"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            />
          </div>
          <div>
            <label class="block text-slate-400 mb-1">Descrição</label>
            <textarea
              v-model="createForm.description"
              rows="2"
              class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 outline-none"
            ></textarea>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="showCreateModal = false" class="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white">
            Cancelar
          </button>
          <button @click="submitCreateProject" class="px-5 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg font-mono">
            Cadastrar Projeto
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const projects = ref([])
const loading = ref(false)
const showCreateModal = ref(false)
const inspectedProject = ref(null)
const inspectedGit = ref(null)
const projectFiles = ref({ directories: [], files: [] })
const loadingFiles = ref(false)

const createForm = ref({
  name: '',
  path: '',
  stack: 'general',
  description: '',
})

const fetchProjects = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/v1/projects')
    if (res.data?.projects) {
      projects.value = res.data.projects
    }
  } catch (err) {
    console.error('Falha ao listar projetos:', err)
  } finally {
    loading.value = false
  }
}

const inspectProject = async (proj) => {
  inspectedProject.value = proj
  loadingFiles.value = true
  projectFiles.value = { directories: [], files: [] }

  try {
    const [detailRes, filesRes] = await Promise.all([
      axios.get(`/api/v1/projects/${proj.id}`),
      axios.get(`/api/v1/projects/${proj.id}/files`),
    ])

    inspectedGit.value = detailRes.data?.git || {}
    projectFiles.value = {
      directories: filesRes.data?.directories || [],
      files: filesRes.data?.files || [],
    }
  } catch (err) {
    console.error('Falha ao inspecionar projeto:', err)
  } finally {
    loadingFiles.value = false
  }
}

const submitCreateProject = async () => {
  if (!createForm.value.name || !createForm.value.path) {
    return alert('Preencha o nome e o caminho do projeto.')
  }
  try {
    const res = await axios.post('/api/v1/projects', createForm.value)
    if (res.data?.success) {
      showCreateModal.value = false
      createForm.value = { name: '', path: '', stack: 'general', description: '' }
      await fetchProjects()
    }
  } catch (err) {
    alert('Erro ao cadastrar projeto: ' + (err.response?.data?.message || err.message))
  }
}

onMounted(() => {
  fetchProjects()
})
</script>
