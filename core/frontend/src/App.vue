<template>
  <div
    class="relative flex h-[100dvh] w-screen overflow-hidden p-1.5 sm:p-2.5 md:p-3.5 gap-2 sm:gap-3 md:gap-4 bg-[#1a2e12] bg-cover bg-center select-none"
    style="background-image: url('/assets/rpg-village-bg.jpg');"
  >
    <!-- Subtle warm vignette so UI panels pop clearly over the village -->
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/25 z-0"></div>

    <!-- RPG FORTRESS LOGIN & REGISTRATION GATE -->
    <div
      v-if="!isAuthenticated"
      class="relative z-30 flex-1 flex items-center justify-center p-4 bg-black/45 backdrop-blur-[2px] -m-3.5 overflow-y-auto"
    >
      <div class="w-full max-w-lg pixel-wood rpg-rivets p-4 shadow-2xl my-auto">
        <div class="pixel-wood-inset p-3.5 mb-3 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-14 h-14 shrink-0 rounded bg-[#3b200e] border-2 border-[#f59e0b] overflow-hidden flex items-center justify-center shadow-md">
              <img src="/assets/sprites/avatar.png" alt="Comandante" class="w-full h-full object-cover" />
            </div>
            <div>
              <span class="rpg-ribbon mb-1">
                {{ authSetupRequired ? '🛡️ 1º ACESSO: CRIAR CONTA' : (authMode === 'register' ? '✨ NOVO CADASTRO DE PERFIL' : '🔒 PORTÃO SOBERANO') }}
              </span>
              <h1 class="font-extrabold text-sm sm:text-base text-[#fff7e6] uppercase rpg-text-outline-sm">
                SPIRANDELIEMPIRE OS
              </h1>
              <p class="text-[11px] text-[#d9bc8c]">
                {{ authMode === 'register' ? 'Cadastre um perfil com preferências salvas para o Jeffrey AI' : 'Acesso ao Command Center & Gestão Autônoma' }}
              </p>
            </div>
          </div>
        </div>

        <!-- Mode Tabs: Login vs Criar Cadastro -->
        <div v-if="!authSetupRequired" class="grid grid-cols-2 gap-2 mb-3">
          <button
            type="button"
            @click="authMode = 'login'; loginError = ''"
            class="py-2 px-3 rounded text-xs font-extrabold uppercase border-2 transition"
            :class="authMode === 'login'
              ? 'bg-[#f59e0b] text-[#1e0d04] border-[#fef08a] shadow'
              : 'bg-[#2b1507] text-[#d9bc8c] border-[#5c3419] hover:text-white'"
          >
            🗝️ Entrar no Perfil
          </button>
          <button
            type="button"
            @click="authMode = 'register'; loginError = ''"
            class="py-2 px-3 rounded text-xs font-extrabold uppercase border-2 transition"
            :class="authMode === 'register'
              ? 'bg-[#f59e0b] text-[#1e0d04] border-[#fef08a] shadow'
              : 'bg-[#2b1507] text-[#d9bc8c] border-[#5c3419] hover:text-white'"
          >
            ➕ Criar Conta / Perfil
          </button>
        </div>

        <form @submit.prevent="submitAuthForm" class="rpg-parchment-inner p-4 space-y-3 text-xs font-bold text-[#2b1507]">
          <div
            v-if="authSetupRequired"
            class="p-2.5 rounded bg-[#fef3c7] border-2 border-[#d97706] text-[11px] text-[#78350f] leading-snug"
          >
            ⚔️ <strong>Primeiro Acesso Detectado:</strong> Cadastre seu perfil, e-mail e senha abaixo. Suas informações e preferências ficarão salvas no banco de dados.
          </div>

          <div
            v-if="loginError"
            class="p-2.5 rounded bg-red-100 border-2 border-red-600 text-[11px] text-red-900 leading-snug"
          >
            ⚠️ {{ loginError }}
          </div>

          <div v-if="authSetupRequired || authMode === 'register'" class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Nome do Perfil / Comandante *</label>
              <input
                v-model="loginForm.name"
                type="text"
                required
                placeholder="Ex: Spirandeli Principal"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Cargo / Título no Império</label>
              <input
                v-model="loginForm.title"
                type="text"
                placeholder="Ex: Gestor TikTok Shop"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div :class="(authSetupRequired || authMode === 'register') ? '' : 'sm:col-span-2'">
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">E-mail do Perfil *</label>
              <input
                v-model="loginForm.email"
                type="email"
                required
                autocomplete="username"
                placeholder="admin@spirandeliempire.tech"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>

            <div :class="(authSetupRequired || authMode === 'register') ? '' : 'sm:col-span-2'">
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
          </div>

          <div v-if="authMode === 'register' || authSetupRequired" class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1 border-t border-[#c89d5c]">
            <div>
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Negócio Principal em Foco</label>
              <select
                v-model="loginForm.focus_business_slug"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe (YouTube Dark)</option>
                <option value="kdp-factory">📚 KDP Factory (Amazon)</option>
                <option value="digital-products">📄 Digital Products (PDFs)</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Meta Diária deste Perfil</label>
              <input
                v-model="loginForm.daily_goal"
                type="text"
                placeholder="Ex: 5 vídeos virais TikTok Shop/dia"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>
            <div class="sm:col-span-2">
              <label class="block mb-1 uppercase text-[10.5px] text-[#4a2810]">Diretrizes Padrão para o Agente Jeffrey</label>
              <input
                v-model="loginForm.custom_instructions"
                type="text"
                placeholder="Ex: Priorizar produtos com comissão acima de 20% e ganchos de 3s"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-2 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>
            <div v-if="authMode === 'register' && !authSetupRequired" class="sm:col-span-2 p-2.5 rounded bg-[#fef3c7] border border-[#d97706]">
              <label class="block mb-1 uppercase text-[10px] text-[#78350f]">
                🔑 Senha Mestra do Comandante Atual (Autorização Anti-Intruso) *
              </label>
              <input
                v-model="loginForm.commander_password"
                type="password"
                required
                placeholder="Digite a senha do Comandante atual para autorizar o novo perfil"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-3 py-1.5 text-[#1e0d04] focus:border-[#d97706] outline-none"
              />
            </div>
          </div>

          <div class="pt-2">
            <button
              type="submit"
              :disabled="loggingIn"
              class="pixel-btn-gold w-full py-2.5 px-4 text-xs uppercase flex items-center justify-center gap-2"
            >
              <span v-if="loggingIn">Processando registro real...</span>
              <span v-else>
                {{ authSetupRequired ? '🔐 Salvar Cadastro & Entrar →' : (authMode === 'register' ? '✨ Concluir Cadastro & Entrar →' : '🗝️ Destrancar Command Center →') }}
              </span>
            </button>
          </div>
        </form>

        <div class="mt-2.5 text-center text-[10px] text-[#d9bc8c] flex items-center justify-between px-1">
          <span>🛡️ Perfis & Preferências Persistidos no PostgreSQL</span>
          <span>Teto Global: R$ 200/mês</span>
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

      <!-- Main Column: Top Server Bar + Viewport Area + Bottom Mobile Dock -->
      <div class="relative z-10 flex-1 flex flex-col min-w-0 h-full overflow-hidden gap-2 sm:gap-3">
        <Header
          class="shrink-0"
          :user="currentUser"
          :is-collapsed="sidebarCollapsed"
          @open-profile="openProfileModal"
          @toggle-menu="mobileMenuOpen = !mobileMenuOpen"
          @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
          @logout="logoutCommander"
        />
        <main class="flex-1 overflow-y-auto pr-0.5 sm:pr-1 pb-16 md:pb-4">
          <router-view />
        </main>
      </div>

      <!-- Bottom Mobile Dock (< 768px) -->
      <nav
        class="md:hidden fixed bottom-0 left-0 right-0 z-40 pixel-wood rpg-rivets px-2 py-1.5 flex items-center justify-around border-t-2 border-[#1e0d04] shadow-[0_-4px_10px_rgba(0,0,0,0.6)] select-none pb-safe"
      >
        <router-link
          v-for="dockItem in mobileDock"
          :key="dockItem.path"
          :to="dockItem.path"
          class="flex flex-col items-center justify-center py-1 px-2.5 rounded transition-all text-center relative"
          :class="isActiveRoute(dockItem.path)
            ? 'text-[#fbbf24] font-black'
            : 'text-[#d9bc8c] hover:text-[#fff6df]'"
        >
          <span class="text-lg leading-none mb-0.5 relative">
            {{ dockItem.icon }}
          </span>
          <span class="text-[9.5px] truncate rpg-text-outline-sm">{{ dockItem.name }}</span>
        </router-link>

        <button
          type="button"
          @click="mobileMenuOpen = true"
          class="flex flex-col items-center justify-center py-1 px-2.5 rounded text-[#d9bc8c] hover:text-[#fff6df]"
        >
          <span class="text-lg leading-none mb-0.5">☰</span>
          <span class="text-[9.5px] truncate rpg-text-outline-sm">Mais</span>
        </button>
      </nav>
    </template>

    <!-- MODAL: MEU PERFIL & SISTEMA DE CADASTROS -->
    <div
      v-if="showProfileModal"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-y-auto"
      @click.self="showProfileModal = false"
    >
      <div class="w-full max-w-2xl pixel-wood rpg-rivets p-3 sm:p-4 shadow-2xl my-auto max-h-[94vh] overflow-y-auto">
        <div class="pixel-wood-inset p-2.5 sm:p-3 mb-3 flex items-center justify-between gap-2">
          <div class="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <img src="/assets/sprites/avatar.png" alt="Avatar" class="w-10 h-10 sm:w-11 sm:h-11 rounded border-2 border-[#f59e0b] object-cover shrink-0" />
            <div class="min-w-0">
              <h2 class="text-xs sm:text-base font-extrabold text-[#fff7e6] uppercase rpg-text-outline-sm truncate">
                👤 Gestão de Perfil & Cadastros
              </h2>
              <p class="text-[10px] sm:text-[11px] text-[#d9bc8c] truncate">
                As informações deste perfil são salvas no banco
              </p>
            </div>
          </div>
          <button
            @click="showProfileModal = false"
            class="pixel-btn-red px-2.5 py-1 text-xs font-black shrink-0"
          >
            ✕
          </button>
        </div>

        <!-- Sub-tabs inside modal: Editar Meu Perfil vs Perfis Cadastrados / Novo Perfil -->
        <div class="flex flex-wrap gap-2 mb-3">
          <button
            @click="profileTab = 'edit'"
            class="px-3 py-1.5 rounded text-xs font-extrabold uppercase border-2 transition"
            :class="profileTab === 'edit'
              ? 'bg-[#f59e0b] text-[#1e0d04] border-[#fef08a]'
              : 'bg-[#2b1507] text-[#d9bc8c] border-[#5c3419]'"
          >
            ✏️ Meu Perfil Ativo ({{ currentUser?.name }})
          </button>
          <button
            @click="profileTab = 'list'; fetchProfilesList()"
            class="px-3 py-1.5 rounded text-xs font-extrabold uppercase border-2 transition"
            :class="profileTab === 'list'
              ? 'bg-[#f59e0b] text-[#1e0d04] border-[#fef08a]'
              : 'bg-[#2b1507] text-[#d9bc8c] border-[#5c3419]'"
          >
            👥 Perfis Cadastrados ({{ profilesList.length || 1 }})
          </button>
          <button
            @click="profileTab = 'new'"
            class="px-3 py-1.5 rounded text-xs font-extrabold uppercase border-2 transition"
            :class="profileTab === 'new'
              ? 'bg-[#f59e0b] text-[#1e0d04] border-[#fef08a]'
              : 'bg-[#2b1507] text-[#d9bc8c] border-[#5c3419]'"
          >
            ➕ Cadastrar Novo Perfil
          </button>
        </div>

        <div v-if="profileFeedback" class="mb-3 p-2.5 rounded bg-emerald-950/90 border border-emerald-500 text-emerald-200 text-xs font-bold">
          ✅ {{ profileFeedback }}
        </div>

        <!-- TAB 1: EDIT CURRENT PROFILE -->
        <form v-if="profileTab === 'edit'" @submit.prevent="saveProfileChanges" class="rpg-parchment-inner p-4 space-y-3 text-xs font-bold text-[#2b1507]">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Nome do Comandante *</label>
              <input
                v-model="profileForm.name"
                type="text"
                required
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">E-mail de Login *</label>
              <input
                v-model="profileForm.email"
                type="email"
                required
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Cargo / Título</label>
              <input
                v-model="profileForm.title"
                type="text"
                placeholder="Comandante Soberano"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Negócio Principal em Foco</label>
              <select
                v-model="profileForm.focus_business_slug"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe</option>
                <option value="kdp-factory">📚 KDP Factory</option>
                <option value="digital-products">📄 Digital Products</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Motor de IA Preferido</label>
              <select
                v-model="profileForm.preferred_provider"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              >
                <option value="hybrid">⚡ Híbrido (Gemini Free + Ollama)</option>
                <option value="gemini">✨ Google Gemini Flash</option>
                <option value="ollama">🦙 Ollama Local (Custo Zero)</option>
                <option value="openai">🧠 OpenAI GPT-4o-mini</option>
              </select>
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Telegram ID / @handle</label>
              <input
                v-model="profileForm.telegram_id"
                type="text"
                placeholder="Ex: @spirandeli"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div class="sm:col-span-3">
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Meta Diária Pessoal</label>
              <input
                v-model="profileForm.daily_goal"
                type="text"
                placeholder="Ex: 3 vídeos virais TikTok Shop + 1 roteiro YouTube Dark por dia"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Nível RPG</label>
              <input
                v-model.number="profileForm.level"
                type="number"
                min="1"
                max="99"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
          </div>

          <div>
            <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Biografia / Notas do Perfil</label>
            <textarea
              v-model="profileForm.bio"
              rows="2"
              placeholder="Resumo das operações e prioridades deste perfil..."
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
            ></textarea>
          </div>

          <div>
            <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Diretrizes Fixas para o Jeffrey AI (Salvas na Memória Operacional)</label>
            <textarea
              v-model="profileForm.custom_instructions"
              rows="2"
              placeholder="Ex: Sempre entregue ganchos de 3s, hashtags de conversão e links da vitrine TikTok Shop nas respostas."
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
            ></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              type="button"
              @click="showProfileModal = false"
              class="px-4 py-2 rounded border-2 border-[#5c3419] text-[#4a2810] hover:bg-[#e5cfa3]"
            >
              Fechar
            </button>
            <button
              type="submit"
              :disabled="savingProfile"
              class="pixel-btn-gold px-5 py-2 text-xs uppercase"
            >
              {{ savingProfile ? 'Salvando...' : '💾 Salvar Informações do Perfil' }}
            </button>
          </div>
        </form>

        <!-- TAB 2: LIST ALL PROFILES -->
        <div v-else-if="profileTab === 'list'" class="rpg-parchment-inner p-4 space-y-2.5 text-xs text-[#2b1507]">
          <p class="font-bold text-[11px] text-[#4a2810] mb-2">
            Perfis registrados no SpirandeliEmpire OS (cada perfil guarda suas próprias metas e diretrizes):
          </p>
          <div
            v-for="prof in profilesList"
            :key="prof.id"
            class="p-3 rounded border-2 border-[#5c3419] bg-[#fdf3de] flex items-center justify-between gap-3"
          >
            <div>
              <div class="font-extrabold text-sm text-[#1e0d04] flex items-center gap-2">
                <span>{{ prof.name }}</span>
                <span class="px-2 py-0.5 text-[10px] rounded bg-[#3b200e] text-[#fbbf24]">
                  Lv. {{ prof.profile_data?.level || 3 }} • {{ prof.profile_data?.title || 'Comandante' }}
                </span>
                <span
                  v-if="prof.id === currentUser?.id"
                  class="px-2 py-0.5 text-[10px] rounded bg-emerald-700 text-white"
                >
                  ATIVO AGORA
                </span>
              </div>
              <div class="text-[11px] text-[#4a2810] mt-0.5">
                📧 {{ prof.email }} • 🎯 Foco: <strong>{{ prof.profile_data?.focus_business_slug || 'tiktok-shop-afiliados' }}</strong>
              </div>
              <div v-if="prof.profile_data?.daily_goal" class="text-[11px] text-[#5c3419] mt-0.5">
                🏆 Meta: {{ prof.profile_data.daily_goal }}
              </div>
            </div>
            <button
              v-if="prof.id !== currentUser?.id"
              @click="switchProfileLogin(prof)"
              class="pixel-btn-gold px-3 py-1.5 text-[11px] shrink-0"
            >
              Trocar para este Perfil
            </button>
          </div>
        </div>

        <!-- TAB 3: CREATE NEW PROFILE -->
        <form v-else-if="profileTab === 'new'" @submit.prevent="registerNewProfileFromModal" class="rpg-parchment-inner p-4 space-y-3 text-xs font-bold text-[#2b1507]">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Nome do Novo Perfil *</label>
              <input
                v-model="newProfileForm.name"
                type="text"
                required
                placeholder="Ex: Operação TikTok Shop #2"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Cargo / Especialidade</label>
              <input
                v-model="newProfileForm.title"
                type="text"
                placeholder="Ex: Gestor de Afiliados"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">E-mail de Acesso *</label>
              <input
                v-model="newProfileForm.email"
                type="email"
                required
                placeholder="perfil2@spirandeliempire.tech"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Senha (mín. 6 caracteres) *</label>
              <input
                v-model="newProfileForm.password"
                type="password"
                required
                minlength="6"
                placeholder="••••••••"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Negócio em Foco</label>
              <select
                v-model="newProfileForm.focus_business_slug"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              >
                <option value="tiktok-shop-afiliados">🔥 TikTok Shop Afiliados</option>
                <option value="risada-exe">🎬 RISADA.exe</option>
                <option value="kdp-factory">📚 KDP Factory</option>
                <option value="digital-products">📄 Digital Products</option>
                <option value="printable-factory">🖨️ Printable Factory</option>
              </select>
            </div>
            <div>
              <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Meta Diária</label>
              <input
                v-model="newProfileForm.daily_goal"
                type="text"
                placeholder="Ex: 5 vídeos TikTok Shop por dia"
                class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
              />
            </div>
          </div>
          <div>
            <label class="block mb-1 uppercase text-[10px] text-[#4a2810]">Diretrizes para o Agente Jeffrey neste Perfil</label>
            <textarea
              v-model="newProfileForm.custom_instructions"
              rows="2"
              placeholder="Instruções específicas que o agente seguirá quando este perfil estiver ativo..."
              class="w-full bg-[#fdf3de] border-2 border-[#5c3419] rounded px-2.5 py-1.5 text-[#1e0d04]"
            ></textarea>
          </div>
          <div class="flex justify-end pt-2">
            <button
              type="submit"
              :disabled="savingProfile"
              class="pixel-btn-gold px-5 py-2 text-xs uppercase"
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
