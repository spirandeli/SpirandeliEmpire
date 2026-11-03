<template>
  <div class="space-y-6 max-w-7xl mx-auto pb-10">
    <!-- ============================================================================== -->
    <!-- 1. TOP GUILD HALL BANNER & COMANDANTE PROFILE -->
    <!-- ============================================================================== -->
    <div class="pixel-wood p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center space-x-4">
        <!-- Player Guild Crest / Avatar Frame -->
        <div class="w-16 h-16 bg-[#160c07] border-4 border-[#5a381f] shadow-[inset_3px_3px_0_#0a0503,0_4px_0_#000] flex items-center justify-center text-3xl relative">
          👑
          <span class="absolute -bottom-2 -right-2 bg-[#d97706] text-[#1c0e05] border-2 border-[#120803] font-pixel-title text-[8px] px-1 py-0.5">
            NV.12
          </span>
        </div>

        <div>
          <div class="flex items-center gap-2">
            <h2 class="font-pixel-title text-sm sm:text-base text-[#fde68a] uppercase tracking-wider">
              Feudo Central do Império
            </h2>
            <span class="text-[9px] font-pixel-title px-1.5 py-0.5 bg-[#15803d] text-[#dcfce7] border border-[#14532d]">
              REINO SEGURO
            </span>
          </div>
          <p class="font-pixel-body text-xs text-[#d6b88d] mt-1">
            SpirandeliEmpire OS • Comandante Soberano • 1 Aliança Central (Jeffrey) • 4 Feudos Digitais
          </p>
        </div>
      </div>

      <!-- Action Pixel Buttons -->
      <div class="flex items-center space-x-3">
        <router-link
          to="/jeffrey"
          class="pixel-btn-wood py-2.5 px-3 flex items-center gap-1.5"
        >
          <span>🧙‍♂️</span> AUDIÊNCIA COM JEFFREY
        </router-link>
        <router-link
          to="/factory"
          class="pixel-btn-gold py-2.5 px-3 flex items-center gap-1.5"
        >
          <span>⚒️</span> FORJAR EXPEDIÇÃO
        </router-link>
      </div>
    </div>

    <!-- ============================================================================== -->
    <!-- 2. STARDEW / GRAVEYARD KEEPER STYLE RPG HUD BARS (HP, STAMINA, MANA, GOLD) -->
    <!-- ============================================================================== -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Vida da Infraestrutura (HP) -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">❤️</span>
            <span class="font-pixel-title text-[9px] text-[#fca5a5]">HP INFRAESTRUTURA</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">100/100</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-hp h-full w-[100%] transition-all duration-500"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>Docker VPS Online</span>
          <span class="text-[#86efac]">● Saudável</span>
        </div>
      </div>

      <!-- 2. Energia da VPS (Stamina) -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">⚡</span>
            <span class="font-pixel-title text-[9px] text-[#86efac]">ENERGIA / RAM</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">{{ stats.ram_usage }}%</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-energy h-full transition-all duration-500" :style="{ width: stats.ram_usage + '%' }"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>CPU: {{ stats.cpu_usage }}%</span>
          <span>Disco: {{ stats.disk_usage }}%</span>
        </div>
      </div>

      <!-- 3. Mana Mágica da IA (Gemini + OpenAI + Llama) -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">🔮</span>
            <span class="font-pixel-title text-[9px] text-[#67e8f9]">MANA DE IA (GATEWAY)</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">100% MP</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-mana h-full w-[100%] transition-all duration-500"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>Gemini Free + Llama</span>
          <span class="text-[#38bdf8]">Ativo</span>
        </div>
      </div>

      <!-- 4. Cofre Real de Ouro (Budget Guardrail) -->
      <div class="pixel-wood p-4">
        <div class="flex justify-between items-center mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm">🪙</span>
            <span class="font-pixel-title text-[9px] text-[#fcd34d]">BURSA REAL (TETO)</span>
          </div>
          <span class="font-pixel-title text-[9px] text-[#ffffff]">R$ {{ stats.budget_spent }}G</span>
        </div>
        <div class="pixel-bar-bg h-3.5 w-full">
          <div class="pixel-bar-gold h-full transition-all duration-500" :style="{ width: Math.max(5, stats.budget_percent) + '%' }"></div>
        </div>
        <div class="text-[10px] font-pixel-body text-[#d6b88d] mt-1.5 flex justify-between">
          <span>Limite: 200,00 G</span>
          <span class="text-[#fcd34d]">{{ stats.budget_percent }}% gasto</span>
        </div>
      </div>
    </div>

    <!-- ============================================================================== -->
    <!-- 3. DIÁLOGO DO MESTRE DA GUILDA (JEFFREY NPC SPEECH BOX) -->
    <!-- ============================================================================== -->
    <div class="pixel-parchment p-5 shadow-[4px_4px_0_#140b06]">
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <!-- Pixel Portrait -->
        <div class="w-16 h-16 bg-[#25150c] border-4 border-[#3d2413] shadow-[inset_2px_2px_0_#140a05] flex items-center justify-center text-4xl shrink-0">
          🧙‍♂️
        </div>

        <!-- Dialogue Box -->
        <div class="flex-1 space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-pixel-title text-xs text-[#52290d] uppercase">
              Mestre Jeffrey diz:
            </span>
            <span class="text-[9px] font-pixel-title px-1.5 py-0.5 bg-[#451a03] text-[#fef3c7] border border-[#260e02]">
              CONSELHEIRO REAL
            </span>
          </div>

          <p class="font-pixel-body text-xs sm:text-sm text-[#2b180d] leading-relaxed">
            "Saudações, Nobre Comandante! O reino está operando sob severa ordem financeira. Nossos 4 feudos digitais estão provisionados e a bursa real permanece intacta (R$ 0,00 gastos do limite de 200 Ouros). O motor de inteligência híbrido está pronto para produzir roteiros do RISADA.exe com Gemini e Llama. Quais são as ordens para hoje?"
          </p>

          <!-- Interactive Dialogue Choices (RPG Dialogue Tree) -->
          <div class="flex flex-wrap gap-2 pt-2">
            <router-link
              to="/jeffrey"
              class="text-[10px] font-pixel-title bg-[#78350f] hover:bg-[#92400e] text-[#fef3c7] px-2.5 py-1.5 border-2 border-[#451a03] shadow-[2px_2px_0_#291002] transition"
            >
              ▶ "Jeffrey, planeje o próximo vídeo do RISADA.exe"
            </router-link>
            <router-link
              to="/ai-engine"
              class="text-[10px] font-pixel-title bg-[#365314] hover:bg-[#4d7c0f] text-[#ecfccb] px-2.5 py-1.5 border-2 border-[#1a2e05] shadow-[2px_2px_0_#101f02] transition"
            >
              ▶ "Verificar cota de tokens do Gemini & Llama"
            </router-link>
            <router-link
              to="/factory"
              class="text-[10px] font-pixel-title bg-[#1e3a5f] hover:bg-[#1d4ed8] text-[#dbeafe] px-2.5 py-1.5 border-2 border-[#0f172a] shadow-[2px_2px_0_#020617] transition"
            >
              ▶ "Criar um novo feudo na forja"
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================================================================== -->
    <!-- 4. INVENTÁRIO DOS FEUDOS DIGITAIS (STARDEW FARM PLOTS / WORKSHOPS) -->
    <!-- ============================================================================== -->
    <div class="pixel-wood p-5 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b-2 border-[#452310] pb-3">
        <div>
          <div class="flex items-center space-x-2">
            <span class="text-lg">🗺️</span>
            <h3 class="font-pixel-title text-xs sm:text-sm text-[#fcd34d] uppercase">
              Inventário de Feudos & Fazendas Digitais
            </h3>
          </div>
          <p class="font-pixel-body text-xs text-[#d6b88d] mt-0.5">
            Negócios isolados produzindo ativos com orçamentos, diretórios e guardrails independentes
          </p>
        </div>

        <router-link
          to="/businesses"
          class="font-pixel-title text-[9px] text-[#f59e0b] hover:text-[#fde68a] transition flex items-center gap-1"
        >
          <span>VER GRIMÓRIO COMPLETO</span> →
        </router-link>
      </div>

      <!-- Business Inventory Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="biz in businesses"
          :key="biz.slug"
          class="pixel-slot p-4 flex flex-col justify-between relative group hover:border-[#f59e0b] transition-all"
        >
          <!-- Item Header & Rarity -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-[9px] font-pixel-title px-1.5 py-0.5 border" :class="getRarityBadge(biz.category)">
                {{ biz.category }}
              </span>
              <span
                class="text-[8px] font-pixel-title px-1.5 py-0.5 border"
                :class="biz.status === 'active' ? 'bg-[#14532d] text-[#86efac] border-[#22c55e]' : 'bg-[#78350f] text-[#fde68a] border-[#d97706]'"
              >
                {{ biz.status === 'active' ? '● OPERANDO' : '⚡ SETUP' }}
              </span>
            </div>

            <!-- Business Title with RPG Icon -->
            <div class="flex items-center space-x-2 mt-1">
              <span class="text-2xl">{{ getBusinessIcon(biz.category) }}</span>
              <div>
                <h4 class="font-pixel-title text-xs text-[#ffffff] group-hover:text-[#fde68a] transition">
                  {{ biz.name }}
                </h4>
                <div class="text-[9px] font-pixel-title text-[#a16207]">NÍVEL 1</div>
              </div>
            </div>

            <p class="font-pixel-body text-xs text-[#d6b88d] mt-2 line-clamp-3 leading-relaxed">
              {{ biz.description }}
            </p>
          </div>

          <!-- Bottom Stats & Action -->
          <div class="mt-4 pt-3 border-t-2 border-[#2b170c] space-y-2">
            <div class="flex justify-between items-center text-[10px] font-pixel-body text-[#a88d6c]">
              <span>Teto: <span class="text-[#fcd34d] font-bold">{{ biz.budget_limit_brl }} G</span></span>
              <span>Rendimento: <span class="text-[#86efac] font-bold">0 G</span></span>
            </div>

            <router-link
              :to="'/businesses/' + biz.slug"
              class="pixel-btn-stone w-full py-1.5 text-center block text-[8px] uppercase tracking-wider"
            >
              ⚔️ INSPECIONAR FEUDO
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================================================================== -->
    <!-- 5. QUADRO DE MISSÕES (STARDEW BULLETIN BOARD) & MURALHAS DA INFRA -->
    <!-- ============================================================================== -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Stardew Valley Pierre's Style Bulletin Quest Board -->
      <div class="pixel-parchment p-5 shadow-[4px_4px_0_#140b06] space-y-3">
        <div class="flex items-center justify-between border-b-2 border-[#52290d] pb-2">
          <div class="flex items-center space-x-2">
            <span class="text-lg">📌</span>
            <h3 class="font-pixel-title text-xs text-[#2b180d] uppercase">
              Quadro de Missões & Supervisão Real
            </h3>
          </div>
          <span class="text-[8px] font-pixel-title px-2 py-0.5 bg-[#451a03] text-[#fde68a] border border-[#2b1102]">
            0 APROVAÇÕES PENDENTES
          </span>
        </div>

        <div class="space-y-2 text-xs font-pixel-body">
          <div class="p-2.5 bg-[#d8ba78] border-2 border-[#6d4520] shadow-[inset_1px_1px_0_#f4e3b7] flex items-start gap-2">
            <span class="text-base text-[#15803d]">✓</span>
            <div>
              <div class="font-bold text-[#2b180d] font-pixel-title text-[9px]">DIRETRIZ SAGRADA (RISADA.EXE)</div>
              <div class="text-[11px] text-[#52290d]">Fidelidade absoluta às Escrituras. Jamais inventar versículos bíblicos.</div>
            </div>
          </div>

          <div class="p-2.5 bg-[#d8ba78] border-2 border-[#6d4520] shadow-[inset_1px_1px_0_#f4e3b7] flex items-start gap-2">
            <span class="text-base text-[#15803d]">✓</span>
            <div>
              <div class="font-bold text-[#2b180d] font-pixel-title text-[9px]">TETO ORÇAMENTÁRIO REAL</div>
              <div class="text-[11px] text-[#52290d]">Gastos bloqueados compulsoriamente aos 200 Ouros mensais. Alerta aos 80%.</div>
            </div>
          </div>

          <div class="p-2.5 bg-[#d8ba78] border-2 border-[#6d4520] shadow-[inset_1px_1px_0_#f4e3b7] flex items-start gap-2">
            <span class="text-base text-[#15803d]">✓</span>
            <div>
              <div class="font-bold text-[#2b180d] font-pixel-title text-[9px]">SOBERANIA HUMANA MANDATÓRIA</div>
              <div class="text-[11px] text-[#52290d]">Jeffrey e agentes subordinados não publicam nem gastam sem sua autorização expressa.</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Graveyard Keeper Stone Workshop / Server Runes -->
      <div class="pixel-stone p-5 shadow-[4px_4px_0_#08090b] space-y-3">
        <div class="flex items-center justify-between border-b-2 border-[#333a44] pb-2">
          <div class="flex items-center space-x-2">
            <span class="text-lg">🛡️</span>
            <h3 class="font-pixel-title text-xs text-[#f1f5f9] uppercase">
              Muralhas & Runas da VPS (Docker)
            </h3>
          </div>
          <span class="text-[8px] font-pixel-title px-2 py-0.5 bg-[#14532d] text-[#86efac] border border-[#22c55e]">
            ORQUESTRAÇÃO VIVA
          </span>
        </div>

        <div class="space-y-2 text-xs font-pixel-body">
          <div class="flex justify-between items-center p-2 bg-[#191c21] border border-[#333a44]">
            <div class="flex items-center space-x-2">
              <span class="text-sm">🏰</span>
              <span class="text-[#f1f5f9] font-pixel-title text-[9px]">Caddy Proxy TLS (HTTPS)</span>
            </div>
            <span class="text-[8px] font-pixel-title text-[#86efac] bg-[#052e16] px-1.5 py-0.5 border border-[#166534]">RUNA ATIVA</span>
          </div>

          <div class="flex justify-between items-center p-2 bg-[#191c21] border border-[#333a44]">
            <div class="flex items-center space-x-2">
              <span class="text-sm">⚙️</span>
              <span class="text-[#f1f5f9] font-pixel-title text-[9px]">Laravel Core (PHP 8.3)</span>
            </div>
            <span class="text-[8px] font-pixel-title text-[#86efac] bg-[#052e16] px-1.5 py-0.5 border border-[#166534]">RUNA ATIVA</span>
          </div>

          <div class="flex justify-between items-center p-2 bg-[#191c21] border border-[#333a44]">
            <div class="flex items-center space-x-2">
              <span class="text-sm">🗄️</span>
              <span class="text-[#f1f5f9] font-pixel-title text-[9px]">PostgreSQL 16 & Redis 7</span>
            </div>
            <span class="text-[8px] font-pixel-title text-[#86efac] bg-[#052e16] px-1.5 py-0.5 border border-[#166534]">RUNA ATIVA</span>
          </div>

          <div class="flex justify-between items-center p-2 bg-[#191c21] border border-[#333a44]">
            <div class="flex items-center space-x-2">
              <span class="text-sm">🦙</span>
              <span class="text-[#f1f5f9] font-pixel-title text-[9px]">Ollama Local (Llama 3.2:3b)</span>
            </div>
            <span class="text-[8px] font-pixel-title text-[#38bdf8] bg-[#082f49] px-1.5 py-0.5 border border-[#0369a1]">STANDBY</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const stats = ref({
  total_businesses: 4,
  active_businesses: 1,
  provisioning_businesses: 3,
  budget_spent: '0.00',
  budget_percent: 0,
  total_revenue: '0.00',
  estimated_profit: '0.00',
  ram_usage: 28.5,
  cpu_usage: 8.2,
  disk_usage: 14.1,
})

const businesses = ref([
  {
    name: 'RISADA.exe',
    slug: 'risada-exe',
    category: 'YouTube Dark',
    status: 'provisioning',
    description: 'Canal de histórias bíblicas com animações/ilustrações, voz brasileira e roteiros biblicamente fiéis.',
    budget_limit_brl: '60.00',
    storage_path: 'businesses/risada-exe',
  },
  {
    name: 'KDP Factory',
    slug: 'kdp-factory',
    category: 'Amazon KDP',
    status: 'provisioning',
    description: 'Oficina de eBooks, devocionais e manuscritos infantis para Amazon KDP.',
    budget_limit_brl: '50.00',
    storage_path: 'businesses/kdp-factory',
  },
  {
    name: 'Digital Products',
    slug: 'digital-products',
    category: 'Digital Goods',
    status: 'provisioning',
    description: 'Alquimia de estudos bíblicos em PDF, planners devocionais e apostilas de alta conversão.',
    budget_limit_brl: '40.00',
    storage_path: 'businesses/digital-products',
  },
  {
    name: 'Printable Factory',
    slug: 'printable-factory',
    category: 'Printables',
    status: 'provisioning',
    description: 'Ateliê de gravuras, quadros e artes em altíssima resolução para impressão física.',
    budget_limit_brl: '30.00',
    storage_path: 'businesses/printable-factory',
  },
])

const getRarityBadge = (category) => {
  if (category === 'YouTube Dark') return 'bg-[#581c87] text-[#e9d5ff] border-[#a855f7]'
  if (category === 'Amazon KDP') return 'bg-[#1e3a8a] text-[#bfdbfe] border-[#3b82f6]'
  if (category === 'Digital Goods') return 'bg-[#14532d] text-[#bbf7d0] border-[#22c55e]'
  return 'bg-[#374151] text-[#e5e7eb] border-[#9ca3af]'
}

const getBusinessIcon = (category) => {
  if (category === 'YouTube Dark') return '🎬'
  if (category === 'Amazon KDP') return '📖'
  if (category === 'Digital Goods') return '🧪'
  return '🖼️'
}
</script>
