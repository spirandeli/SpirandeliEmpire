<template>
  <div
    class="relative flex flex-col lg:flex-row h-[100dvh] w-screen overflow-hidden p-1.5 sm:p-2.5 md:p-3.5 gap-2 sm:gap-3 md:gap-4 bg-slate-950 text-slate-100 select-none"
  >
    <!-- Clean ambient lighting: subtle gradient, zero clutter -->
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(30,41,59,0.6),rgba(2,6,23,0.98))] z-0"></div>

    <!-- COMMAND CENTER LOGIN & REGISTRATION GATE -->
    <div
      v-if="!isAuthenticated"
      class="relative z-30 flex-1 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md -m-3.5 overflow-y-auto"
    >
      <div class="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-2xl my-auto">
        <div class="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 mb-4 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 shrink-0 rounded-xl bg-slate-900 border border-amber-500/50 overflow-hidden flex items-center justify-center shadow-md">
              <img src="/assets/sprites/avatar.png" alt="Comandante" class="w-full h-full object-cover" />
            </div>
            <div>
              <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30 mb-1">
                {{ authSetupRequired ? '🛡️ 1º Acesso: Criar Conta' : (authMode === 'register' ? '✨ Novo Cadastro de Perfil' : '🔒 Autenticação Soberana') }}
              </span>
              <h1 class="font-bold text-base sm:text-lg text-white tracking-tight">
                SPIRANDELIEMPIRE OS
              </h1>
              <p class="text-xs text-slate-400">
                {{ authMode === 'register' ? 'Cadastre um perfil com preferências salvas para o Jeffrey AI' : 'Acesso ao Command Center & Gestão Autônoma' }}
              </p>
            </div>
          </div>
        </div>

        <!-- Mode Tabs: Login vs Criar Cadastro -->
        <div v-if="!authSetupRequired" class="grid grid-cols-2 gap-2 mb-4">
          <button
            type="button"
            @click="authMode = 'login'; loginError = ''"
            class="py-2.5 px-3 rounded-xl text-xs font-bold uppercase transition"
            :class="authMode === 'login'
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white hover:bg-slate-750'"
          >
            🗝️ Entrar no Perfil
          </button>
          <button
            type="button"
            @click="authMode = 'register'; loginError = ''"
            class="py-2.5 px-3 rounded-xl text-xs font-bold uppercase transition"
            :class="authMode === 'register'
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white hover:bg-slate-750'"
          >
            ➕ Criar Conta / Perfil
          </button>
        </div>

        <form @submit.prevent="submitAuthForm" class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 sm:p-5 space-y-3.5 text-xs text-slate-200">
          <div
            v-if="authSetupRequired"
            class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/40 text-xs text-amber-200 leading-snug"
          >
            ⚔️ <strong>Primeiro Acesso Detectado:</strong> Cadastre seu perfil, e-mail e senha abaixo. Suas informações e preferências ficarão salvas no banco de dados.
          </div>

          <div
            v-if="loginError"
            class="p-3 rounded-xl bg-red-950/80 border border-red-700 text-xs text-red-200 leading-snug"
          >
            ⚠️ {{ loginError }}
          </div>

          <div v-if="authSetupRequired || authMode === 'register'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Nome do Perfil / Comandante *</label>
              <input
                v-model="loginForm.name"
                type="text"
                required
                placeholder="Ex: Spirandeli Principal"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Cargo / Título no Império</label>
              <input
                v-model="loginForm.title"
                type="text"
                placeholder="Ex: Gestor TikTok Shop"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div :class="(authSetupRequired || authMode === 'register') ? '' : 'sm:col-span-2'">
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">E-mail do Perfil *</label>
              <input
                v-model="loginForm.email"
                type="email"
                required
                autocomplete="username"
                placeholder="admin@spirandeliempire.tech"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition"
              />
            </div>

            <div :class="(authSetupRequired || authMode === 'register') ? '' : 'sm:col-span-2'">
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Senha Secreta *</label>
              <input
                v-model="loginForm.password"
                type="password"
                required
                autocomplete="current-password"
                placeholder="••••••••••••"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition"
              />
            </div>
          </div>

          <div v-if="authMode === 'register' || authSetupRequired" class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Negócio Principal em Foco</label>
              <select
                v-model="loginForm.focus_business_slug"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe (YouTube Dark)</option>
                <option value="kdp-factory">📚 KDP Factory (Amazon)</option>
                <option value="digital-products">📄 Digital Products (PDFs)</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Meta Diária deste Perfil</label>
              <input
                v-model="loginForm.daily_goal"
                type="text"
                placeholder="Ex: 5 vídeos virais TikTok Shop/dia"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div class="sm:col-span-2">
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Diretrizes Padrão para o Agente Jeffrey</label>
              <input
                v-model="loginForm.custom_instructions"
                type="text"
                placeholder="Ex: Priorizar produtos com comissão acima de 20% e ganchos de 3s"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div v-if="authMode === 'register' && !authSetupRequired" class="sm:col-span-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/40">
              <label class="block mb-1 uppercase font-semibold text-[10.5px] text-amber-300">
                🔑 Senha Mestra do Comandante Atual (Autorização Anti-Intruso) *
              </label>
              <input
                v-model="loginForm.commander_password"
                type="password"
                required
                placeholder="Digite a senha do Comandante atual para autorizar o novo perfil"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none"
              />
            </div>
          </div>

          <div class="pt-2">
            <button
              type="submit"
              :disabled="loggingIn"
              class="w-full py-2.5 px-4 text-xs uppercase font-bold tracking-wider rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2"
            >
              <span v-if="loggingIn">Processando registro real...</span>
              <span v-else>
                {{ authSetupRequired ? '🔐 Salvar Cadastro & Entrar →' : (authMode === 'register' ? '✨ Concluir Cadastro & Entrar →' : '🗝️ Destrancar Command Center →') }}
              </span>
            </button>
          </div>
        </form>

        <div class="mt-3 text-center text-xs text-slate-500 flex items-center justify-between px-1 font-mono">
          <span>🛡️ Persistência PostgreSQL</span>
          <span>Teto: R$ 200/mês</span>
        </div>
      </div>
    </div>

    <template v-else>
      <!-- Desktop Sidebar (>= 1024px) -->
      <Sidebar
        class="hidden lg:flex relative z-20 shrink-0"
        :user="currentUser"
        :is-collapsed="sidebarCollapsed"
        @open-profile="openProfileModal"
      />

      <!-- Mobile / Tablet Drawer (< 1024px) with Backdrop -->
      <div
        v-if="mobileMenuOpen"
        class="lg:hidden fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex transition-opacity"
        @click.self="mobileMenuOpen = false"
      >
        <Sidebar
          class="h-full z-10 shadow-2xl"
          :user="currentUser"
          :is-mobile="true"
          @close-mobile="mobileMenuOpen = false"
          @open-profile="openProfileModal(); mobileMenuOpen = false"
        />
      </div>

      <!-- Main Column: Top Server Bar + Viewport Area -->
      <div class="relative z-10 flex-1 flex flex-col min-w-0 w-full h-full overflow-hidden gap-2 sm:gap-3">
        <Header
          class="shrink-0"
          :user="currentUser"
          :is-collapsed="sidebarCollapsed"
          @open-profile="openProfileModal"
          @toggle-menu="mobileMenuOpen = !mobileMenuOpen"
          @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
          @logout="logoutCommander"
        />
        <main class="flex-1 overflow-y-auto pr-0.5 sm:pr-1 pb-20 md:pb-4 w-full">
          <router-view />
        </main>
      </div>

      <!-- Bottom Mobile Dock (< 768px) -->
      <nav
        class="md:hidden !fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 px-2 py-1.5 flex items-center justify-around shadow-2xl select-none pb-safe"
      >
        <router-link
          v-for="dockItem in mobileDock"
          :key="dockItem.path"
          :to="dockItem.path"
          class="flex flex-col items-center justify-center py-1 px-3 rounded-lg transition-all text-center relative"
          :class="isActiveRoute(dockItem.path)
            ? 'text-amber-400 font-bold bg-amber-500/10'
            : 'text-slate-400 hover:text-slate-200'"
        >
          <span class="text-xl leading-none mb-0.5 relative">
            {{ dockItem.icon }}
          </span>
          <span class="text-[10px] font-medium tracking-tight">{{ dockItem.name }}</span>
        </router-link>

        <button
          type="button"
          @click="mobileMenuOpen = true"
          class="flex flex-col items-center justify-center py-1 px-3 rounded-lg text-slate-400 hover:text-slate-200 transition-all"
        >
          <span class="text-xl leading-none mb-0.5">☰</span>
          <span class="text-[10px] font-medium tracking-tight">Mais</span>
        </button>
      </nav>
    </template>

    <!-- MODAL: MEU PERFIL & SISTEMA DE CADASTROS -->
    <div
      v-if="showProfileModal"
      class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 overflow-y-auto"
      @click.self="showProfileModal = false"
    >
      <div class="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl my-auto max-h-[94vh] overflow-y-auto">
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3 sm:p-3.5 mb-4 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <img src="/assets/sprites/avatar.png" alt="Avatar" class="w-10 h-10 sm:w-11 sm:h-11 rounded-xl border border-amber-500/40 object-cover shrink-0" />
            <div class="min-w-0">
              <h2 class="text-sm sm:text-base font-bold text-slate-100 uppercase tracking-tight truncate">
                👤 Gestão de Perfil & Cadastros
              </h2>
              <p class="text-xs text-slate-400 truncate">
                As informações deste perfil são salvas no banco
              </p>
            </div>
          </div>
          <button
            @click="showProfileModal = false"
            class="px-2.5 py-1 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition shrink-0"
          >
            ✕
          </button>
        </div>

        <!-- Sub-tabs inside modal: Editar Meu Perfil vs Perfis Cadastrados / Novo Perfil -->
        <div class="flex flex-wrap gap-2 mb-4">
          <button
            @click="profileTab = 'edit'"
            class="px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase transition"
            :class="profileTab === 'edit'
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white'"
          >
            ✏️ Meu Perfil Ativo ({{ currentUser?.name }})
          </button>
          <button
            @click="profileTab = 'list'; fetchProfilesList()"
            class="px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase transition"
            :class="profileTab === 'list'
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white'"
          >
            👥 Perfis Cadastrados ({{ profilesList.length || 1 }})
          </button>
          <button
            @click="profileTab = 'new'"
            class="px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase transition"
            :class="profileTab === 'new'
              ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
              : 'bg-slate-800 text-slate-300 border border-slate-700 hover:text-white'"
          >
            ➕ Cadastrar Novo Perfil
          </button>
        </div>

        <div v-if="profileFeedback" class="mb-4 p-3 rounded-xl bg-emerald-950/90 border border-emerald-500/70 text-emerald-200 text-xs font-semibold">
          ✅ {{ profileFeedback }}
        </div>

        <!-- TAB 1: EDIT CURRENT PROFILE -->
        <form v-if="profileTab === 'edit'" @submit.prevent="saveProfileChanges" class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 sm:p-5 space-y-3.5 text-xs text-slate-200">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Nome do Comandante *</label>
              <input
                v-model="profileForm.name"
                type="text"
                required
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">E-mail de Login *</label>
              <input
                v-model="profileForm.email"
                type="email"
                required
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Cargo / Título</label>
              <input
                v-model="profileForm.title"
                type="text"
                placeholder="Comandante Soberano"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Negócio Principal em Foco</label>
              <select
                v-model="profileForm.focus_business_slug"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe</option>
                <option value="kdp-factory">📚 KDP Factory</option>
                <option value="digital-products">📄 Digital Products</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Motor de IA Preferido</label>
              <select
                v-model="profileForm.preferred_provider"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              >
                <option value="hybrid">⚡ Híbrido (Gemini Free + Ollama)</option>
                <option value="gemini">✨ Google Gemini Flash</option>
                <option value="ollama">🦙 Ollama Local (Custo Zero)</option>
                <option value="openai">🧠 OpenAI GPT-4o-mini</option>
              </select>
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Telegram ID / @handle</label>
              <input
                v-model="profileForm.telegram_id"
                type="text"
                placeholder="Ex: @spirandeli"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div class="sm:col-span-3">
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Meta Diária Pessoal</label>
              <input
                v-model="profileForm.daily_goal"
                type="text"
                placeholder="Ex: 3 vídeos virais TikTok Shop + 1 roteiro YouTube Dark por dia"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Nível Operacional</label>
              <input
                v-model.number="profileForm.level"
                type="number"
                min="1"
                max="99"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none font-mono"
              />
            </div>
          </div>

          <div>
            <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Biografia / Notas do Perfil</label>
            <textarea
              v-model="profileForm.bio"
              rows="2"
              placeholder="Resumo das operações e prioridades deste perfil..."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
            ></textarea>
          </div>

          <div>
            <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Diretrizes Fixas para o Jeffrey AI (Salvas na Memória Operacional)</label>
            <textarea
              v-model="profileForm.custom_instructions"
              rows="2"
              placeholder="Ex: Sempre entregue ganchos de 3s, hashtags de conversão e links da vitrine TikTok Shop nas respostas."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
            ></textarea>
          </div>

          <div class="flex justify-end gap-2.5 pt-2">
            <button
              type="button"
              @click="showProfileModal = false"
              class="px-4 py-2 rounded-xl border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            >
              Fechar
            </button>
            <button
              type="submit"
              :disabled="savingProfile"
              class="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold uppercase text-xs transition shadow-md shadow-amber-500/20"
            >
              {{ savingProfile ? 'Salvando...' : '💾 Salvar Informações do Perfil' }}
            </button>
          </div>
        </form>

        <!-- TAB 2: LIST ALL PROFILES -->
        <div v-else-if="profileTab === 'list'" class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 sm:p-5 space-y-3 text-xs text-slate-200">
          <p class="font-medium text-xs text-slate-400 mb-2">
            Perfis registrados no SpirandeliEmpire OS (cada perfil guarda suas próprias metas e diretrizes):
          </p>
          <div
            v-for="prof in profilesList"
            :key="prof.id"
            class="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 flex items-center justify-between gap-3"
          >
            <div>
              <div class="font-bold text-sm text-slate-100 flex items-center gap-2">
                <span>{{ prof.name }}</span>
                <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-amber-400 border border-slate-700">
                  Lv. {{ prof.profile_data?.level || 3 }} • {{ prof.profile_data?.title || 'Comandante' }}
                </span>
                <span
                  v-if="prof.id === currentUser?.id"
                  class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-950 text-emerald-400 border border-emerald-800"
                >
                  ATIVO AGORA
                </span>
              </div>
              <div class="text-xs text-slate-400 mt-1">
                📧 {{ prof.email }} • 🎯 Foco: <strong class="text-slate-200">{{ prof.profile_data?.focus_business_slug || 'tiktok-shop-afiliados' }}</strong>
              </div>
              <div v-if="prof.profile_data?.daily_goal" class="text-xs text-slate-400 mt-0.5">
                🏆 Meta: {{ prof.profile_data.daily_goal }}
              </div>
            </div>
            <button
              v-if="prof.id !== currentUser?.id"
              @click="switchProfileLogin(prof)"
              class="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shrink-0 transition"
            >
              Trocar para este Perfil
            </button>
          </div>
        </div>

        <!-- TAB 3: CREATE NEW PROFILE -->
        <form v-else-if="profileTab === 'new'" @submit.prevent="registerNewProfileFromModal" class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 sm:p-5 space-y-3.5 text-xs text-slate-200">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Nome do Novo Perfil *</label>
              <input
                v-model="newProfileForm.name"
                type="text"
                required
                placeholder="Ex: Operação TikTok Shop #2"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Cargo / Especialidade</label>
              <input
                v-model="newProfileForm.title"
                type="text"
                placeholder="Ex: Gestor de Afiliados"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">E-mail de Acesso *</label>
              <input
                v-model="newProfileForm.email"
                type="email"
                required
                placeholder="perfil2@spirandeliempire.tech"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Senha (mín. 6 caracteres) *</label>
              <input
                v-model="newProfileForm.password"
                type="password"
                required
                minlength="6"
                placeholder="••••••••"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Negócio em Foco</label>
              <select
                v-model="newProfileForm.focus_business_slug"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe</option>
                <option value="kdp-factory">📚 KDP Factory</option>
                <option value="digital-products">📄 Digital Products</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Meta Diária</label>
              <input
                v-model="newProfileForm.daily_goal"
                type="text"
                placeholder="Ex: 5 vídeos TikTok Shop por dia"
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
              />
            </div>
          </div>
          <div>
            <label class="block mb-1.5 uppercase font-medium text-[11px] text-slate-400">Diretrizes para o Agente Jeffrey neste Perfil</label>
            <textarea
              v-model="newProfileForm.custom_instructions"
              rows="2"
              placeholder="Instruções específicas que o agente seguirá quando este perfil estiver ativo..."
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:border-amber-500 outline-none transition"
            ></textarea>
          </div>
          <div class="flex justify-end pt-2">
            <button
              type="submit"
              :disabled="savingProfile"
              class="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold uppercase text-xs transition shadow-md shadow-amber-500/20"
            >
              {{ savingProfile ? 'Cadastrando...' : '➕ Criar e Ativar Novo Perfil' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import Sidebar from './components/Sidebar.vue'
import Header from './components/Header.vue'

const route = useRoute()
const mobileMenuOpen = ref(false)
const sidebarCollapsed = ref(false)

const mobileDock = [
  { name: 'Início', path: '/', icon: '🏠' },
  { name: 'Jeffrey', path: '/jeffrey', icon: '🧙‍♂️' },
  { name: 'Negócios', path: '/businesses', icon: '💼' },
  { name: 'Factory', path: '/factory', icon: '🏭' },
]

const isActiveRoute = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const isAuthenticated = ref(false)
const authSetupRequired = ref(false)
const authMode = ref('login')
const loggingIn = ref(false)
const loginError = ref('')
const currentUser = ref(null)

const loginForm = ref({
  name: 'Comandante Spirandeli',
  title: 'Comandante Soberano',
  email: '',
  password: '',
  commander_password: '',
  focus_business_slug: 'tiktok-shop-afiliados',
  daily_goal: '3 vídeos virais para TikTok Shop + 1 roteiro YouTube Dark',
  custom_instructions: 'Priorizar produtos de alta comissão na TikTok Shop Brasil e manter proteção Anti-Ban nos vídeos.',
})

// Profile Modal State
const showProfileModal = ref(false)
const profileTab = ref('edit')
const savingProfile = ref(false)
const profileFeedback = ref('')
const profilesList = ref([])

const profileForm = ref({
  name: '',
  email: '',
  title: 'Comandante Soberano',
  bio: '',
  telegram_id: '',
  preferred_provider: 'hybrid',
  focus_business_slug: 'tiktok-shop-afiliados',
  daily_goal: '',
  custom_instructions: '',
  level: 3,
})

const newProfileForm = ref({
  name: '',
  title: 'Gestor de Operações',
  email: '',
  password: '',
  focus_business_slug: 'tiktok-shop-afiliados',
  daily_goal: '5 criativos de alta conversão para TikTok Shop',
  custom_instructions: '',
})

const syncProfileFormFromUser = (user) => {
  if (!user) return
  currentUser.value = user
  const p = user.profile_data || {}
  profileForm.value = {
    name: user.name || 'Comandante Spirandeli',
    email: user.email || '',
    title: p.title || 'Comandante Soberano',
    bio: p.bio || '',
    telegram_id: p.telegram_id || '',
    preferred_provider: p.preferred_provider || 'hybrid',
    focus_business_slug: p.focus_business_slug || 'tiktok-shop-afiliados',
    daily_goal: p.daily_goal || '',
    custom_instructions: p.custom_instructions || '',
    level: p.level || 3,
  }
}

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
    if (
      err.response &&
      err.response.status === 401 &&
      !err.config?.url?.includes('/auth/login') &&
      !err.config?.url?.includes('/auth/register')
    ) {
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
      syncProfileFormFromUser(meRes.data.user)
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

const submitAuthForm = async () => {
  loginError.value = ''
  loggingIn.value = true
  try {
    const endpoint = (!authSetupRequired.value && authMode.value === 'register')
      ? '/api/v1/auth/register'
      : '/api/v1/auth/login'

    const res = await axios.post(endpoint, {
      name: loginForm.value.name,
      title: loginForm.value.title,
      email: loginForm.value.email,
      password: loginForm.value.password,
      commander_password: loginForm.value.commander_password,
      focus_business_slug: loginForm.value.focus_business_slug,
      daily_goal: loginForm.value.daily_goal,
      custom_instructions: loginForm.value.custom_instructions,
    })
    if (res.data?.token) {
      applyAuthToken(res.data.token)
      syncProfileFormFromUser(res.data.user)
      authSetupRequired.value = false
      isAuthenticated.value = true
      loginForm.value.password = ''
    }
  } catch (err) {
    loginError.value =
      err.response?.data?.error ||
      err.response?.data?.message ||
      'Falha ao autenticar/cadastrar perfil. Verifique os dados informados.'
  } finally {
    loggingIn.value = false
  }
}

const openProfileModal = () => {
  profileFeedback.value = ''
  profileTab.value = 'edit'
  showProfileModal.value = true
  fetchProfilesList()
}

const fetchProfilesList = async () => {
  try {
    const res = await axios.get('/api/v1/auth/profiles')
    if (res.data?.profiles) {
      profilesList.value = res.data.profiles
    }
  } catch (_) {}
}

const saveProfileChanges = async () => {
  savingProfile.value = true
  profileFeedback.value = ''
  try {
    const res = await axios.put('/api/v1/auth/profile', profileForm.value)
    if (res.data?.user) {
      syncProfileFormFromUser(res.data.user)
    }
    if (res.data?.token) {
      applyAuthToken(res.data.token)
    }
    profileFeedback.value = res.data?.message || 'Perfil salvo e sincronizado com Jeffrey AI!'
  } catch (err) {
    alert(err.response?.data?.message || 'Erro ao salvar perfil.')
  } finally {
    savingProfile.value = false
  }
}

const registerNewProfileFromModal = async () => {
  savingProfile.value = true
  profileFeedback.value = ''
  try {
    const res = await axios.post('/api/v1/auth/register', newProfileForm.value)
    if (res.data?.token && res.data?.user) {
      applyAuthToken(res.data.token)
      syncProfileFormFromUser(res.data.user)
      profileFeedback.value = `Novo perfil "${res.data.user.name}" cadastrado e ativado!`
      newProfileForm.value = {
        name: '',
        title: 'Gestor de Operações',
        email: '',
        password: '',
        focus_business_slug: 'tiktok-shop-afiliados',
        daily_goal: '5 criativos de alta conversão para TikTok Shop',
        custom_instructions: '',
      }
      profileTab.value = 'edit'
      fetchProfilesList()
    }
  } catch (err) {
    alert(err.response?.data?.message || err.response?.data?.error || 'Erro ao criar novo perfil.')
  } finally {
    savingProfile.value = false
  }
}

const switchProfileLogin = async (prof) => {
  const pwd = prompt(`Digite a senha do perfil "${prof.name}" (${prof.email}):`)
  if (!pwd) return
  try {
    const res = await axios.post('/api/v1/auth/login', {
      email: prof.email,
      password: pwd,
    })
    if (res.data?.token && res.data?.user) {
      applyAuthToken(res.data.token)
      syncProfileFormFromUser(res.data.user)
      profileFeedback.value = `Alternado para o perfil "${res.data.user.name}"!`
      profileTab.value = 'edit'
    }
  } catch (err) {
    alert(err.response?.data?.error || 'Senha incorreta para este perfil.')
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
