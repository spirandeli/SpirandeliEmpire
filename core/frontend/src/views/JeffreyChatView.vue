<template>
  <div
    class="h-[calc(100dvh-6.5rem)] md:h-[calc(100dvh-7.5rem)] flex flex-col md:flex-row gap-2 sm:gap-3 max-w-[1500px] w-full relative"
    @dragover.prevent="isDraggingOver = true"
    @dragleave.prevent="isDraggingOver = false"
    @drop.prevent="handleDropFiles"
  >
    <!-- MOBILE VIEW TABS (< md) -->
    <div class="md:hidden flex items-center justify-between gap-1 pixel-wood rpg-rivets p-1 shrink-0 select-none">
      <button
        type="button"
        @click="mobileTab = 'chat'"
        class="flex-1 py-1.5 px-2 rounded text-xs font-black uppercase transition-all flex items-center justify-center gap-1.5"
        :class="mobileTab === 'chat'
          ? 'bg-[#f59e0b] text-[#1e0d04] border border-[#fef08a] shadow'
          : 'bg-[#2b1507] text-[#d9bc8c] border border-[#5c3419]'"
      >
        <span>💬 Chat</span>
      </button>
      <button
        type="button"
        @click="mobileTab = 'history'"
        class="flex-1 py-1.5 px-2 rounded text-xs font-black uppercase transition-all flex items-center justify-center gap-1.5"
        :class="mobileTab === 'history'
          ? 'bg-[#f59e0b] text-[#1e0d04] border border-[#fef08a] shadow'
          : 'bg-[#2b1507] text-[#d9bc8c] border border-[#5c3419]'"
      >
        <span>🗂️ Histórico</span>
        <span class="text-[10px] px-1 py-0.5 rounded bg-[#3b200e] text-[#fde68a]">
          {{ conversations.length }}
        </span>
      </button>
      <button
        type="button"
        @click="mobileTab = 'monitor'"
        class="flex-1 py-1.5 px-2 rounded text-xs font-black uppercase transition-all flex items-center justify-center gap-1.5 relative"
        :class="mobileTab === 'monitor'
          ? 'bg-[#f59e0b] text-[#1e0d04] border border-[#fef08a] shadow'
          : 'bg-[#2b1507] text-[#d9bc8c] border border-[#5c3419]'"
      >
        <span class="relative">
          📡 Monitor
          <span
            v-if="jeffreyActivity.is_working"
            class="absolute -top-1 -right-2 w-2 h-2 rounded-full bg-emerald-400 animate-ping"
          ></span>
        </span>
        <span
          v-if="jeffreyActivity.counts?.in_progress || jeffreyActivity.counts?.pending"
          class="text-[10px] px-1 py-0.5 rounded bg-amber-800 text-amber-100 font-mono"
        >
          {{ (jeffreyActivity.counts?.in_progress || 0) + (jeffreyActivity.counts?.pending || 0) }}
        </span>
      </button>
    </div>

    <!-- 1. LEFT SIDEBAR: Persistent Conversations History -->
    <div
      v-if="(!isMobile && showConversationsPanel) || (isMobile && mobileTab === 'history')"
      class="pixel-wood rpg-rivets p-2 sm:p-2.5 flex flex-col overflow-hidden shrink-0"
      :class="isMobile ? 'w-full flex-1 h-full' : 'w-56 lg:w-60 h-full'"
    >
      <button
        @click="createNewConversationMobile"
        :disabled="creatingChat"
        class="pixel-btn-gold w-full py-2 px-3 text-xs flex items-center justify-center gap-1.5 mb-2.5 shrink-0"
      >
        <span>+</span> Nova Conversa
      </button>

      <div class="flex-1 overflow-y-auto pixel-wood-inset p-1.5 space-y-1 text-xs">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversationMobile(conv.id)"
          class="p-2 rounded cursor-pointer transition flex items-center justify-between border"
          :class="activeConversationId === conv.id
            ? 'bg-[#5c3419] text-[#fef08a] border-[#f59e0b]'
            : 'text-[#e2c699] border-transparent hover:bg-[#3d210f]'"
        >
          <div class="truncate pr-1">
            <div class="truncate text-[11px] font-bold">{{ conv.title }}</div>
            <div class="text-[9px] text-[#c49a6c] mt-0.5">{{ conv.messages_count || 0 }} msgs</div>
          </div>
          <button
            @click.stop="deleteConversation(conv.id)"
            class="text-[#c49a6c] hover:text-red-400 p-1 text-[10px]"
            title="Excluir conversa"
          >
            ✕
          </button>
        </div>

        <div v-if="!loadingConversations && conversations.length === 0" class="text-center py-6 text-[#c49a6c] text-xs">
          Nenhuma conversa anterior.
        </div>
      </div>
    </div>

    <!-- 2. CENTER AREA: Chat Messages Stream, Attachments, Voice & Rich Editor -->
    <div
      v-if="!isMobile || mobileTab === 'chat'"
      class="flex-1 min-w-0 pixel-wood rpg-rivets p-2.5 sm:p-3 flex flex-col overflow-hidden relative h-full"
    >
      <!-- Drag & Drop Overlay -->
      <div
        v-if="isDraggingOver"
        class="absolute inset-2 z-40 rounded-xl bg-black/80 border-4 border-dashed border-[#f59e0b] flex flex-col items-center justify-center text-[#fef08a] pointer-events-none"
      >
        <span class="text-4xl mb-2">📎</span>
        <span class="font-extrabold text-sm uppercase">Solte arquivos, imagens ou áudios aqui para enviar ao Jeffrey</span>
      </div>

      <!-- Top Header Bar -->
      <div class="pixel-wood-inset p-2 sm:p-2.5 mb-2 sm:mb-2.5 flex flex-wrap items-center justify-between gap-1.5 sm:gap-2">
        <div class="flex items-center space-x-2 min-w-0 flex-1">
          <!-- Toggle Conversations Button on Desktop/Tablet -->
          <button
            type="button"
            @click="showConversationsPanel = !showConversationsPanel"
            class="hidden md:flex pixel-btn-wood h-8 px-2 items-center justify-center text-xs shrink-0"
            :title="showConversationsPanel ? 'Ocultar Histórico' : 'Mostrar Histórico'"
          >
            <span>🗂️</span>
            <span class="hidden xl:inline ml-1 text-[10px]">{{ showConversationsPanel ? 'Ocultar' : 'Histórico' }}</span>
          </button>

          <div class="w-8 h-8 sm:w-9 sm:h-9 rounded bg-[#5c3419] border-2 border-[#f59e0b] text-base sm:text-lg flex items-center justify-center shrink-0">
            🧙‍♂️
          </div>
          <div class="min-w-0 flex-1">
            <div class="font-extrabold text-[11.5px] sm:text-xs text-[#fff6e0] flex items-center gap-1.5 flex-wrap">
              <span class="truncate max-w-[140px] sm:max-w-[220px]">{{ currentConversation?.title || 'Jeffrey AI' }}</span>
              <span
                v-if="jeffreyActivity.is_working"
                class="text-[9.5px] sm:text-[10px] px-1.5 py-0.5 rounded bg-[#78350f] text-[#fef08a] border border-[#f59e0b] flex items-center gap-1 animate-pulse"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#fbbf24]"></span>
                <span>TRABALHANDO</span>
              </span>
              <span
                v-else-if="jeffreyActivity.has_queued || (jeffreyActivity.counts?.pending || 0) > 0"
                class="text-[9.5px] sm:text-[10px] px-1.5 py-0.5 rounded bg-[#451a03] text-[#fde68a] border border-[#d97706] flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#f59e0b]"></span>
                <span>NA FILA</span>
              </span>
              <span
                v-else
                class="text-[9.5px] sm:text-[10px] px-1.5 py-0.5 rounded bg-[#14532d] text-[#86efac] border border-[#22c55e] hidden sm:flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[#4ade80]"></span>
                OCIOSO
              </span>
            </div>
            <div class="text-[9.5px] sm:text-[10px] text-[#d9bc8c] truncate hidden sm:block">
              Suporte a Texto, Prints, Documentos e Voz
            </div>
          </div>
        </div>

        <div class="flex items-center gap-1 sm:gap-1.5 shrink-0 flex-wrap">
          <select
            v-model="chosenProvider"
            @change="onProviderChange"
            class="bg-[#241207] text-[#fbbf24] text-[10.5px] sm:text-[11px] font-bold rounded px-1.5 sm:px-2 py-1 sm:py-1.5 border border-[#784725] max-w-[130px] sm:max-w-[200px] truncate"
          >
            <option
              v-for="opt in availableAiOptions"
              :key="opt.id || opt.value"
              :value="opt.id || opt.value"
            >
              {{ opt.label }}
            </option>
          </select>

          <button
            @click="promptNewBackgroundTask"
            class="pixel-btn-gold px-2 sm:px-2.5 py-1 sm:py-1.5 text-[10.5px] sm:text-[11px] flex items-center gap-1"
            title="Criar Tarefa Real em Segundo Plano"
          >
            <span>⚡</span>
            <span class="hidden sm:inline">+ Tarefa</span>
          </button>

          <button
            @click="isMobile ? (mobileTab = 'monitor') : (showActivityPanel = !showActivityPanel)"
            class="pixel-btn-wood px-2 sm:px-2.5 py-1 sm:py-1.5 text-[10.5px] sm:text-[11px] flex items-center gap-1"
            :title="showActivityPanel ? 'Ocultar Monitor' : 'Abrir Monitor ao Vivo'"
          >
            <span>📋</span>
            <span class="hidden sm:inline">Progresso</span>
            <span>({{ jeffreyActivity.counts?.total || 0 }})</span>
          </button>
        </div>
      </div>

      <!-- LIVE WORKER PROGRESS BANNER -->
      <div
        v-if="jeffreyActivity.is_working"
        class="mb-2.5 p-2.5 rounded bg-[#2b1507] border-2 border-[#f59e0b] text-xs text-[#fff6e0] shadow-md"
      >
        <div class="flex items-center justify-between gap-2 mb-1.5">
          <div class="font-extrabold text-[#fbbf24] flex items-center gap-2 truncate">
            <span class="inline-block w-2.5 h-2.5 rounded-full bg-[#fbbf24] animate-ping"></span>
            <span>
              Trabalhando agora:
              <strong class="text-white">#{{ jeffreyActivity.worker_state?.task_id || '?' }}</strong>
              — {{ jeffreyActivity.worker_state?.title || 'Executando pesquisa/tarefa...' }}
            </span>
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#451a03] text-[#fde68a] border border-[#8c5828] shrink-0">
            {{ jeffreyActivity.worker_state?.agent_name || 'Jeffrey' }}
          </span>
        </div>
        <div class="text-[11px] text-[#e2c699] mb-1.5 flex justify-between">
          <span>{{ jeffreyActivity.worker_state?.step || 'Processando no worker assíncrono...' }}</span>
          <span class="font-bold text-[#fbbf24]">{{ jeffreyActivity.worker_state?.progress_percent || 50 }}%</span>
        </div>
        <div class="pixel-bar-bg w-full h-3">
          <div
            class="pixel-bar-energy h-full transition-all duration-500"
            :style="{ width: (jeffreyActivity.worker_state?.progress_percent || 50) + '%' }"
          ></div>
        </div>
      </div>

      <!-- Messages Stream (Selectable & Copyable) -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto rpg-parchment-inner p-4 space-y-4 select-text">
        <div
          v-for="(msg, msgIdx) in messages"
          :key="msg.id || msgIdx"
          class="flex flex-col"
          :class="msg.role === 'user' ? 'items-end' : 'items-start'"
        >
          <!-- Message Header + Action Buttons (Copy / Speak / Quote) -->
          <div class="text-[10px] font-bold text-[#5c3419] mb-1 flex items-center gap-2 flex-wrap">
            <span>{{ msg.role === 'user' ? '👑 Comandante' : '🧙‍♂️ Jeffrey AI' }}</span>
            <span
              v-if="msg.provider && msg.provider !== 'system'"
              class="text-[9px] px-1.5 py-0.5 rounded bg-[#3b200e] text-[#fbbf24]"
            >
              {{ msg.provider }} <span v-if="msg.model">({{ msg.model }})</span> <span v-if="msg.latency_ms">• {{ msg.latency_ms }}ms</span>
            </span>

            <!-- Copy Message Button -->
            <button
              type="button"
              @click="copyText(msg.content, `msg_${msg.id || msgIdx}`)"
              class="px-2 py-0.5 rounded border text-[9.5px] font-extrabold transition flex items-center gap-1"
              :class="copiedId === `msg_${msg.id || msgIdx}`
                ? 'bg-emerald-700 text-white border-emerald-900'
                : 'bg-[#e9d5b0] hover:bg-[#d8bc8a] text-[#2b1507] border-[#8c5828]'"
              title="Copiar texto desta mensagem"
            >
              <span>{{ copiedId === `msg_${msg.id || msgIdx}` ? '✓ Copiado!' : '📋 Copiar' }}</span>
            </button>

            <!-- Speak / Listen Button (TTS) -->
            <button
              v-if="msg.role !== 'user' && msg.content"
              type="button"
              @click="toggleSpeakMessage(msg.content, `tts_${msg.id || msgIdx}`)"
              class="px-2 py-0.5 rounded border border-[#8c5828] bg-[#e9d5b0] hover:bg-[#d8bc8a] text-[#2b1507] text-[9.5px] font-extrabold transition"
              title="Ouvir resposta em voz alta"
            >
              {{ speakingId === `tts_${msg.id || msgIdx}` ? '⏹️ Parar Voz' : '🔊 Ouvir' }}
            </button>
          </div>

          <!-- Message Content Bubble -->
          <div
            class="w-full sm:max-w-3xl p-2.5 sm:p-3.5 rounded-lg text-xs leading-relaxed border-2 select-text"
            :class="msg.role === 'user'
              ? 'bg-[#5c3419] text-[#fff6e0] border-[#1e0d04] font-medium whitespace-pre-wrap'
              : 'bg-[#fbf0d9] text-[#231104] border-[#8c5828] whitespace-pre-wrap font-medium'"
          >
            <!-- Attached Files / Images / Voice Audio inside Message -->
            <div
              v-if="msg.attachments && msg.attachments.length > 0"
              class="mb-2.5 space-y-2"
            >
              <div
                v-for="(att, aIdx) in msg.attachments"
                :key="aIdx"
                class="p-2 rounded border"
                :class="msg.role === 'user' ? 'bg-[#3b200e] border-[#8c5828]' : 'bg-[#f3e1be] border-[#b88746]'"
              >
                <!-- Image Attachment Preview -->
                <div v-if="att.is_image || (att.mime_type && att.mime_type.startsWith('image/'))" class="space-y-1">
                  <a :href="att.url || att.preview_url" target="_blank" rel="noopener">
                    <img
                      :src="att.url || att.preview_url"
                      :alt="att.name"
                      class="max-h-60 rounded border border-[#1e0d04] object-contain"
                    />
                  </a>
                  <div class="text-[10px] opacity-80 flex items-center justify-between">
                    <span>🖼️ {{ att.name }}</span>
                    <a v-if="att.url" :href="att.url" download class="underline">Baixar</a>
                  </div>
                </div>

                <!-- Voice / Audio Attachment Player -->
                <div v-else-if="att.is_voice || (att.mime_type && att.mime_type.startsWith('audio/'))" class="space-y-1">
                  <div class="text-[10px] font-bold flex items-center gap-1.5">
                    <span>🎙️ Mensagem de Voz ({{ att.name }})</span>
                  </div>
                  <audio
                    :src="att.url || att.preview_url"
                    controls
                    class="h-8 w-64 max-w-full"
                  ></audio>
                </div>

                <!-- Document / Code / Spreadsheet Attachment -->
                <div v-else class="flex items-center justify-between gap-3 text-[11px]">
                  <span class="truncate font-bold">📄 {{ att.name }} ({{ formatBytes(att.size) }})</span>
                  <a
                    v-if="att.url"
                    :href="att.url"
                    target="_blank"
                    download
                    class="px-2 py-0.5 rounded bg-[#f59e0b] text-[#1e0d04] text-[10px] font-extrabold shrink-0"
                  >
                    Baixar ⬇
                  </a>
                </div>
              </div>
            </div>

            <!-- Text Content: Rich Markdown for Assistant, Clean Pre-wrap for User -->
            <div
              v-if="msg.role === 'assistant'"
              class="select-text break-words leading-relaxed space-y-1"
              v-html="renderMarkdown(stripActionsTag(msg.content))"
            ></div>
            <div
              v-else
              class="select-text break-words whitespace-pre-wrap leading-relaxed font-medium"
            >{{ msg.content }}</div>

            <!-- Tool Execution Cards -->
            <div
              v-if="msg.tool_calls && msg.tool_calls.length > 0"
              class="mt-2.5 space-y-1.5"
            >
              <div
                v-for="(tc, tcIdx) in msg.tool_calls"
                :key="tcIdx"
                class="p-2 bg-[#2b1507] text-[#fde68a] rounded border border-[#8c5828] text-[10px] select-text shadow-sm"
              >
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-1.5">
                    <span class="px-1.5 py-0.5 rounded bg-[#451a03] text-[#fbbf24] font-black border border-[#8c5828]">
                      ⚙️ {{ formatToolName(tc.name) }}
                    </span>
                    <span class="text-[9px] text-[#86efac] font-bold">✓ Executado com Sucesso</span>
                  </div>
                  <button
                    v-if="tc.name === 'create_task' || tc.name === 'create_task_pipeline'"
                    type="button"
                    @click="openActivityMonitor"
                    class="text-[9px] px-2 py-0.5 rounded bg-[#f59e0b] text-[#1e0d04] font-black hover:brightness-110 transition flex items-center gap-1"
                  >
                    📡 Ver no Monitor
                  </button>
                </div>
                <!-- Tool Arguments Summary -->
                <div v-if="tc.arguments?.title" class="text-[10.5px] text-[#fff6e0] font-semibold mt-1">
                  Missão: <span class="italic text-[#fbbf24]">"{{ tc.arguments.title }}"</span>
                </div>
                <div v-if="tc.arguments?.steps" class="text-[10px] text-[#d9bc8c] mt-0.5">
                  Pipeline: {{ tc.arguments.steps.length }} etapas encadeadas
                </div>
                <!-- Collapsible Details -->
                <details class="mt-1">
                  <summary class="cursor-pointer text-[9px] text-[#c49a6c] hover:text-[#fde68a]">
                    Ver parâmetros técnicos (JSON)
                  </summary>
                  <pre class="mt-1 p-1.5 bg-[#1e0d04] rounded text-[9px] font-mono text-[#d9bc8c] overflow-x-auto max-h-32">{{ JSON.stringify(tc.arguments, null, 2) }}</pre>
                </details>
              </div>
            </div>

            <!-- Suggested Follow-up Actions -->
            <div
              v-if="msg.role !== 'user' && getSuggestedActions(msg).length > 0"
              class="mt-3 pt-2 border-t border-[#8c5828]/30 flex flex-wrap items-center gap-1.5"
            >
              <div class="w-full text-[9.5px] font-black uppercase text-[#8c5828] flex items-center gap-1">
                <span>⚡ Próximos Passos Sugeridos:</span>
              </div>
              <button
                v-for="(action, aIdx) in getSuggestedActions(msg)"
                :key="aIdx"
                type="button"
                @click="sendQuickPrompt(action)"
                class="px-2 py-1 rounded bg-[#e9d5b0] hover:bg-[#d8bc8a] text-[#2b1507] text-[10px] font-bold border border-[#8c5828] transition flex items-center gap-1 shadow-sm active:scale-95"
              >
                <span>👉</span> {{ action }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="loading" class="flex items-center space-x-2 text-[#5c3419] text-xs font-bold p-2 bg-[#fbf0d9] rounded border border-[#8c5828] animate-pulse">
          <span class="w-2.5 h-2.5 rounded-full bg-[#d97706] animate-ping"></span>
          <span>{{ loadingStepText }}</span>
        </div>
      </div>

      <!-- ===================================================================== -->
      <!-- RICH COMPOSER: ATTACHMENTS PREVIEW + VOICE RECORDER + MULTILINE EDITOR -->
      <!-- ===================================================================== -->
      <div class="pt-2.5 space-y-2">
        <!-- Quick Action Contextual Chips -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-[10.5px] scrollbar-none select-none">
          <span class="text-[#8c5828] font-black shrink-0 text-[10px] uppercase">Ações Rápidas:</span>
          <button
            v-for="(qp, qIdx) in quickActionPrompts"
            :key="qIdx"
            type="button"
            @click="sendQuickPrompt(qp.prompt)"
            class="px-2 py-0.5 rounded bg-[#3b200e] hover:bg-[#5c3419] text-[#fef08a] border border-[#784725] shrink-0 font-bold transition flex items-center gap-1 active:scale-95 shadow-sm"
          >
            <span>{{ qp.icon }}</span>
            <span>{{ qp.label }}</span>
          </button>
        </div>
        <!-- 1. Pending Attachments Preview Bar -->
        <div
          v-if="pendingAttachments.length > 0"
          class="p-2 rounded bg-[#241207] border border-[#f59e0b] flex items-center gap-2 overflow-x-auto"
        >
          <div
            v-for="(att, idx) in pendingAttachments"
            :key="idx"
            class="flex items-center gap-2 bg-[#3b200e] border border-[#8c5828] rounded px-2.5 py-1.5 text-xs text-[#fff6e0] shrink-0"
          >
            <img
              v-if="att.is_image && att.preview_url"
              :src="att.preview_url"
              class="w-8 h-8 rounded object-cover border border-[#f59e0b]"
            />
            <span v-else-if="att.is_voice" class="text-base">🎙️</span>
            <span v-else class="text-base">📄</span>

            <div class="max-w-[160px]">
              <div class="truncate text-[11px] font-bold">{{ att.name }}</div>
              <div class="text-[9px] text-[#d9bc8c]">{{ formatBytes(att.size) }}</div>
            </div>

            <audio
              v-if="att.is_voice && att.preview_url"
              :src="att.preview_url"
              controls
              class="h-6 w-36"
            ></audio>

            <button
              type="button"
              @click="removePendingAttachment(idx)"
              class="text-red-400 hover:text-red-200 font-black px-1"
              title="Remover anexo"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- 2. Active Voice Recording Banner -->
        <div
          v-if="isRecordingVoice"
          class="p-2.5 rounded bg-[#450a0a] border-2 border-red-500 text-xs text-white flex items-center justify-between gap-3 animate-pulse"
        >
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="w-3 h-3 rounded-full bg-red-500 animate-ping shrink-0"></span>
            <span class="font-extrabold">
              🎙️ Gravando Voz ({{ formatRecordingDuration(recordingSeconds) }})
            </span>
            <span v-if="liveSpeechTranscript" class="text-amber-200 truncate italic">
              "{{ liveSpeechTranscript }}"
            </span>
            <span v-else class="text-red-200 text-[11px]">
              Fale agora... (o áudio e a transcrição serão enviados ao Jeffrey)
            </span>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              @click="stopVoiceRecording(false)"
              class="px-3 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold text-[11px]"
            >
              ⏹️ Parar & Revisar
            </button>
            <button
              type="button"
              @click="stopVoiceRecording(true)"
              class="px-3 py-1 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold text-[11px]"
            >
              🚀 Parar & Enviar Agora
            </button>
            <button
              type="button"
              @click="cancelVoiceRecording"
              class="px-2 py-1 rounded bg-red-800 hover:bg-red-700 text-white font-bold text-[11px]"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- 3. Quick Prompt Chips + Hidden File Input -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 max-w-full">
            <button
              v-for="chip in quickChips"
              :key="chip.label"
              type="button"
              @click="applyQuickChip(chip.prompt)"
              class="px-2 py-1 rounded bg-[#2b1507] hover:bg-[#452612] text-[#fde68a] border border-[#6b3f20] text-[10px] font-bold shrink-0 transition"
            >
              {{ chip.label }}
            </button>
          </div>
          <span class="text-[10px] text-[#d9bc8c] hidden xl:inline shrink-0">
            💡 <kbd class="px-1 py-0.5 bg-[#241207] rounded border border-[#5c3419]">Enter</kbd> envia • <kbd class="px-1 py-0.5 bg-[#241207] rounded border border-[#5c3419]">Shift+Enter</kbd> quebra linha
          </span>
        </div>

        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept="image/*,audio/*,.pdf,.txt,.md,.csv,.json,.py,.php,.js,.ts,.html,.xml,.log"
          class="hidden"
          @change="handleFileSelect"
        />

        <!-- 4. Main Multiline Editor + Attachment + Voice + Send Buttons -->
        <div class="flex items-end gap-1.5 sm:gap-2">
          <!-- Attach File / Image Button -->
          <button
            type="button"
            @click="triggerFilePicker"
            :disabled="loading"
            class="pixel-btn-wood h-10 sm:h-11 px-2.5 sm:px-3 flex items-center justify-center gap-1 text-xs shrink-0"
            title="Anexar imagens, prints, roteiros, PDFs, CSVs ou áudios"
          >
            <span class="text-sm sm:text-base">📎</span>
            <span class="hidden sm:inline font-bold">Anexar</span>
          </button>

          <!-- Voice Message / Microphone Button -->
          <button
            type="button"
            @click="toggleVoiceRecording"
            :disabled="loading"
            class="h-10 sm:h-11 px-2.5 sm:px-3 rounded flex items-center justify-center gap-1 text-xs font-extrabold border-2 transition shrink-0"
            :class="isRecordingVoice
              ? 'bg-red-600 text-white border-red-300 animate-pulse'
              : 'pixel-btn-wood'"
            title="Gravar mensagem de voz e transcrever fala em português"
          >
            <span class="text-sm sm:text-base">🎙️</span>
            <span class="hidden sm:inline font-bold">{{ isRecordingVoice ? 'Gravando...' : 'Voz' }}</span>
          </button>

          <!-- Multiline Textarea -->
          <textarea
            ref="composerTextarea"
            v-model="inputMessage"
            rows="2"
            placeholder="Mensagem para o Jeffrey... (Cole prints com Ctrl+V)"
            :disabled="loading"
            @keydown="handleEditorKeydown"
            @paste="handleEditorPaste"
            class="flex-1 pixel-wood-inset px-2.5 sm:px-3.5 py-2 text-xs text-[#fff6e0] placeholder-[#a8865e] focus:outline-none focus:border-[#f59e0b] resize-y min-h-[40px] sm:min-h-[44px] max-h-32 sm:max-h-36 select-text leading-relaxed"
          ></textarea>

          <!-- Send Button -->
          <button
            type="button"
            @click="sendMessage"
            :disabled="loading || (!inputMessage.trim() && pendingAttachments.length === 0)"
            class="pixel-btn-gold h-10 sm:h-11 px-3.5 sm:px-5 text-xs font-extrabold shrink-0 flex items-center gap-1"
          >
            <span class="hidden sm:inline">Enviar</span>
            <span>➔</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 3. RIGHT SIDEBAR: LIVE JEFFREY ACTIVITY, TASKS & PROGRESS MONITOR -->
    <div
      v-if="(!isMobile && showActivityPanel) || (isMobile && mobileTab === 'monitor')"
      class="pixel-wood rpg-rivets p-2 sm:p-2.5 flex flex-col overflow-hidden shrink-0 select-text"
      :class="isMobile ? 'w-full flex-1 h-full' : 'w-72 lg:w-80 xl:w-96 h-full'"
    >
      <div class="pixel-wood-inset p-2 sm:p-2.5 mb-2 flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="font-extrabold text-xs text-[#fef08a] flex items-center gap-1.5 truncate">
            <span>📡</span>
            <span class="truncate">Monitor do Jeffrey (Ao Vivo)</span>
          </div>
          <div class="text-[9.5px] sm:text-[10px] text-[#d9bc8c] truncate">
            Atualiza a cada 4s • Fila: {{ jeffreyActivity.queue_length || 0 }}
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <button @click="fetchJeffreyActivity" class="pixel-btn-wood px-2 py-1 text-[10px]">
            ↻
          </button>
          <button
            v-if="isMobile"
            @click="mobileTab = 'chat'"
            class="pixel-btn-gold px-2 py-1 text-[10px] font-black"
            title="Voltar ao Chat"
          >
            💬 Chat
          </button>
          <button
            v-else
            @click="showActivityPanel = false"
            class="pixel-btn-wood px-2 py-1 text-[10px] font-bold"
            title="Fechar Monitor"
          >
            ✕
          </button>
        </div>
      </div>

      <div class="grid grid-cols-4 gap-1.5 mb-2 text-center">
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Na Fila</div>
          <div class="text-sm font-black text-[#fbbf24]">{{ jeffreyActivity.counts?.pending || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Fazendo</div>
          <div class="text-sm font-black text-[#38bdf8]">{{ jeffreyActivity.counts?.in_progress || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Prontas</div>
          <div class="text-sm font-black text-[#4ade80]">{{ jeffreyActivity.counts?.completed || 0 }}</div>
        </div>
        <div class="pixel-wood-inset p-1.5">
          <div class="text-[9px] text-[#d9bc8c] font-bold uppercase">Falhas</div>
          <div class="text-sm font-black text-[#f87171]">{{ jeffreyActivity.counts?.failed || 0 }}</div>
        </div>
      </div>

      <div class="flex gap-1.5 mb-2">
        <button
          @click="activitySubTab = 'tasks'"
          class="flex-1 py-1.5 px-2 rounded text-[11px] font-extrabold border transition"
          :class="activitySubTab === 'tasks'
            ? 'bg-[#63391b] text-[#fef08a] border-[#f59e0b]'
            : 'bg-[#2b1507] text-[#c49a6c] border-[#1a0b03] hover:text-white'"
        >
          📋 Trabalhos ({{ jeffreyActivity.recent_tasks?.length || 0 }})
        </button>
        <button
          @click="activitySubTab = 'decisions'"
          class="flex-1 py-1.5 px-2 rounded text-[11px] font-extrabold border transition"
          :class="activitySubTab === 'decisions'
            ? 'bg-[#63391b] text-[#fef08a] border-[#f59e0b]'
            : 'bg-[#2b1507] text-[#c49a6c] border-[#1a0b03] hover:text-white'"
        >
          🔍 Log de Ações ({{ jeffreyActivity.recent_decisions?.length || 0 }})
        </button>
      </div>

      <!-- SUB-TAB 1: TASKS -->
      <div v-if="activitySubTab === 'tasks'" class="flex-1 overflow-y-auto pixel-wood-inset p-2 space-y-2 text-xs">
        <div
          class="p-2.5 rounded border-2"
          :class="jeffreyActivity.is_working
            ? 'bg-[#3b200e] border-[#f59e0b]'
            : (jeffreyActivity.has_queued || (jeffreyActivity.counts?.pending || 0) > 0)
              ? 'bg-[#2b1507] border-[#d97706]'
              : 'bg-[#241207] border-[#4a2810]'"
        >
          <div class="flex items-center justify-between text-[11px] font-bold">
            <span class="text-[#fef08a]">Estado Real do Worker:</span>
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-black uppercase"
              :class="jeffreyActivity.is_working
                ? 'bg-[#0284c7] text-white'
                : (jeffreyActivity.has_queued || (jeffreyActivity.counts?.pending || 0) > 0)
                  ? 'bg-[#f59e0b] text-[#1e0d04]'
                  : 'bg-[#14532d] text-[#86efac]'"
            >
              {{
                jeffreyActivity.is_working
                  ? 'EM EXECUÇÃO'
                  : (jeffreyActivity.has_queued || (jeffreyActivity.counts?.pending || 0) > 0)
                    ? 'NA FILA'
                    : 'OCIOSO / LIVRE'
              }}
            </span>
          </div>
          <div class="text-[11px] text-[#e2c699] mt-1 leading-snug">
            {{ jeffreyActivity.worker_state?.step || 'Nenhuma tarefa rodando em background no momento.' }}
          </div>
        </div>

        <div
          v-if="!jeffreyActivity.recent_tasks || jeffreyActivity.recent_tasks.length === 0"
          class="rpg-parchment-inner p-4 text-center space-y-2"
        >
          <div class="text-base">📭</div>
          <div class="font-extrabold text-[#2b1507] text-xs">Nenhuma tarefa registrada</div>
          <p class="text-[11px] text-[#4a2810]">
            Clique abaixo para disparar uma pesquisa ou trabalho real em segundo plano!
          </p>
          <button @click="promptNewBackgroundTask" class="pixel-btn-gold px-3 py-1.5 text-[11px] w-full">
            + Criar Tarefa Real para o Jeffrey
          </button>
        </div>

        <div
          v-for="t in jeffreyActivity.recent_tasks"
          :key="t.id"
          class="rpg-parchment-inner p-2.5 space-y-1.5 border-2 border-[#3a1e0b] select-text"
        >
          <div class="flex items-start justify-between gap-1.5">
            <div class="font-extrabold text-[11.5px] text-[#1e0d04] leading-snug">
              <span class="font-mono text-[#78350f]">#{{ t.id }}</span> {{ t.title }}
            </div>
            <span
              class="px-1.5 py-0.5 rounded text-[9px] font-black uppercase shrink-0 border"
              :class="{
                'bg-[#0284c7] text-white border-[#0369a1] animate-pulse': t.status === 'in_progress',
                'bg-[#4f46e5] text-white border-[#312e81]': t.status === 'pending' && t.payload?.depends_on_task_id,
                'bg-[#d97706] text-[#1e0d04] border-[#78350f]': t.status === 'pending' && !t.payload?.depends_on_task_id,
                'bg-[#15803d] text-white border-[#052e16]': t.status === 'completed',
                'bg-[#b91c1c] text-white border-[#450a0a]': t.status === 'failed',
                'bg-[#57534e] text-white border-[#292524]': t.status === 'cancelled'
              }"
            >
              {{ t.status === 'pending' && t.payload?.depends_on_task_id ? `⛓️ AGUARDANDO #${t.payload.depends_on_task_id}` : formatTaskStatus(t.status) }}
            </span>
          </div>

          <div class="flex items-center justify-between text-[10px] text-[#4a2810] font-semibold">
            <span>🤖 {{ t.agent_name || 'Jeffrey' }} ({{ t.type }})</span>
            <span>{{ formatTimeShort(t.completed_at || t.started_at || t.created_at) }}</span>
          </div>

          <div v-if="t.status === 'in_progress' || t.status === 'pending'" class="pt-1 space-y-1">
            <div class="pixel-bar-bg w-full h-2.5">
              <div
                class="pixel-bar-energy h-full transition-all"
                :style="{
                  width: t.status === 'in_progress'
                    ? ((String(jeffreyActivity.worker_state?.task_id) === String(t.id) && jeffreyActivity.worker_state?.progress_percent)
                        ? jeffreyActivity.worker_state.progress_percent + '%'
                        : '65%')
                    : (t.payload?.depends_on_task_id ? '8%' : '15%')
                }"
              ></div>
            </div>
            <div class="text-[10px] text-[#5c3419] font-semibold">
              {{
                t.status === 'in_progress'
                  ? ((String(jeffreyActivity.worker_state?.task_id) === String(t.id) && jeffreyActivity.worker_state?.step)
                      ? jeffreyActivity.worker_state.step
                      : '⚙️ Worker processando no motor de IA...')
                  : (t.payload?.depends_on_task_id
                      ? `⛓️ Aguardando o resultado da Tarefa #${t.payload.depends_on_task_id} para planejar automaticamente...`
                      : '⏳ Aguardando vez na fila do worker...')
              }}
            </div>
          </div>

          <div v-if="t.error_message" class="p-1.5 rounded bg-red-100 border border-red-400 text-[10px] text-red-900 font-semibold">
            ⚠️ {{ t.error_message }}
          </div>

          <div class="pt-1 flex flex-wrap items-center justify-between gap-1 border-t border-[#c4924d]">
            <button
              v-if="t.result?.response"
              @click="expandedTaskId = (expandedTaskId === t.id ? null : t.id)"
              class="text-[10.5px] font-extrabold text-[#78350f] hover:underline"
            >
              {{ expandedTaskId === t.id ? '▲ Ocultar Resultado' : '👁️ Ver Entrega Completa' }}
            </button>
            <span v-else class="text-[10px] text-[#5c3419] italic">
              {{ t.status === 'completed' ? 'Concluído' : 'Sem resultado ainda' }}
            </span>

            <div class="flex items-center gap-1">
              <button
                v-if="t.result?.response"
                @click="copyText(t.result.response, `task_${t.id}`)"
                class="px-2 py-0.5 rounded bg-[#3b200e] text-[#fbbf24] text-[9.5px] font-bold hover:brightness-110"
              >
                {{ copiedId === `task_${t.id}` ? '✓ Copiado' : '📋 Copiar' }}
              </button>
              <button
                v-if="t.result?.response"
                @click="sendTaskResultToChat(t)"
                class="px-2 py-0.5 rounded bg-[#5c3419] text-[#fef08a] text-[9.5px] font-bold hover:brightness-110"
              >
                📥 No Chat
              </button>
              <button
                v-if="t.status === 'failed' || t.status === 'cancelled' || t.status === 'pending'"
                @click="retryTask(t.id)"
                class="px-2 py-0.5 rounded bg-[#d97706] text-[#1e0d04] text-[9.5px] font-bold hover:brightness-110"
              >
                🔄 Rodar
              </button>
              <button
                v-if="t.status === 'pending' || t.status === 'in_progress'"
                @click="cancelTask(t.id)"
                class="px-1.5 py-0.5 rounded bg-[#991b1b] text-white text-[9.5px] font-bold"
              >
                ✕
              </button>
            </div>
          </div>

          <div
            v-if="expandedTaskId === t.id && t.result?.response"
            class="mt-1.5 p-2 rounded bg-[#fbf0d9] border border-[#8c5828] text-[11px] text-[#1e0d04] whitespace-pre-wrap max-h-60 overflow-y-auto font-medium select-text"
          >
            {{ t.result.response }}
          </div>
        </div>
      </div>

      <!-- SUB-TAB 2: DECISIONS -->
      <div v-else class="flex-1 overflow-y-auto pixel-wood-inset p-2 space-y-2 text-xs">
        <div
          v-for="d in jeffreyActivity.recent_decisions"
          :key="d.id"
          class="rpg-parchment-inner p-2.5 space-y-1 border border-[#3a1e0b] select-text"
        >
          <div class="flex items-center justify-between">
            <span class="font-extrabold text-[11px] text-[#1e0d04]">⚡ {{ d.agent_name }}</span>
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#3b200e] text-[#fbbf24]">
              {{ d.action_type }}
            </span>
          </div>
          <div class="text-[10.5px] text-[#3a1f0d] font-medium">{{ d.justification }}</div>
          <div class="flex justify-between text-[9.5px] text-[#5c3419] font-semibold pt-0.5">
            <span>Motor: {{ d.input_payload?.provider || 'system' }} ({{ d.input_payload?.latency_ms || 0 }}ms)</span>
            <span>{{ formatTimeShort(d.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL DE DISPARO DE TAREFA EM 2º PLANO (AGENTES AUTÔNOMOS) -->
    <div
      v-if="showNewTaskModal"
      class="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50"
    >
      <div class="pixel-wood rpg-rivets p-4 max-w-md w-full space-y-3">
        <div class="flex items-center justify-between border-b border-[#784725] pb-2">
          <div class="font-extrabold text-sm text-[#fef08a] flex items-center gap-2">
            <span>⚡</span>
            <span>Delegar Tarefa em 2º Plano ao Agente</span>
          </div>
          <button @click="showNewTaskModal = false" class="text-[#c49a6c] hover:text-white text-xs font-bold">✕</button>
        </div>

        <div class="space-y-2.5 text-xs">
          <div>
            <label class="block text-[11px] font-bold text-[#e2c699] mb-1">Agente Especialista</label>
            <select
              v-model="newTaskForm.agent_name"
              class="w-full bg-[#241207] text-[#fef08a] text-xs font-bold rounded px-2.5 py-2 border border-[#784725]"
            >
              <option value="TikTok Shop Strategist">🔥 TikTok Shop Strategist (Produtos Virais, Hooks & Conversão)</option>
              <option value="Research Agent">🔎 Research Agent (Pesquisa Web, TikTok Shop, Bíblia & Tendências)</option>
              <option value="Content Creator">✍️ Content Creator (Roteiros Shorts, Vídeos Longos & Livros KDP)</option>
              <option value="Business Analyst">📊 Business Analyst (Viabilidade, Nichos & Monetização)</option>
              <option value="Jeffrey">🧙‍♂️ Jeffrey (Orquestrador & Arquiteto Geral)</option>
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-[#e2c699] mb-1">Tipo de Operação</label>
            <select
              v-model="newTaskForm.type"
              class="w-full bg-[#241207] text-[#fef08a] text-xs font-bold rounded px-2.5 py-2 border border-[#784725]"
            >
              <option value="research_and_execution">🌐 Pesquisa Web Ao Vivo + Relatório Prático</option>
              <option value="content_creation">🎬 Criação de Roteiro / Copywriting / Manuscrito KDP</option>
              <option value="market_analysis">📈 Análise de Produtos Virais & Afiliados</option>
              <option value="tiktok_video_pipeline">📱 Pipeline Vídeo TikTok Shop (Roteiro + TTS + Render)</option>
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-[#e2c699] mb-1">Missão / Prompt Detalhado</label>
            <textarea
              v-model="newTaskForm.prompt"
              rows="4"
              placeholder="Ex: Identificar 10 produtos viralizados na TikTok Shop Brasil com alta margem de comissão e criar 3 ganchos de vídeo para os melhores..."
              class="w-full pixel-wood-inset p-2.5 text-xs text-[#fff6e0] placeholder-[#a8865e] focus:outline-none focus:border-[#f59e0b]"
            ></textarea>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            @click="showNewTaskModal = false"
            class="pixel-btn-wood px-3 py-1.5 text-xs"
          >
            Cancelar
          </button>
          <button
            type="button"
            @click="submitNewBackgroundTask"
            :disabled="submittingTask || !newTaskForm.prompt.trim()"
            class="pixel-btn-gold px-4 py-1.5 text-xs"
          >
            {{ submittingTask ? 'Enfileirando...' : '🚀 Disparar no Worker' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'

// Viewport & Responsive Layout State
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const onResize = () => {
  windowWidth.value = window.innerWidth
}
const isMobile = computed(() => windowWidth.value < 768)
const mobileTab = ref('chat') // 'chat' | 'history' | 'monitor'
const showConversationsPanel = ref(typeof window !== 'undefined' ? window.innerWidth >= 1280 : true)

const conversations = ref([])
const activeConversationId = ref(null)
const currentConversation = ref(null)
const messages = ref([])

const loading = ref(false)
const loadingConversations = ref(false)
const creatingChat = ref(false)
const inputMessage = ref('')
const chosenProvider = ref(localStorage.getItem('empire_chosen_ai_provider') || 'gemini')
const canUseGemini = ref(true)
const availableAiOptions = ref([
  { id: 'gemini', value: 'gemini', label: '✨ Google Gemini 3.8 Flash (Recomendado)' },
  { id: 'hybrid', value: 'hybrid', label: '⚡ Cooperativo (Llama Analisa → Gemini 3.8 Executa)' },
  { id: 'openai', value: 'openai', label: '🤖 OpenAI GPT-4o-mini' },
  { id: 'ollama', value: 'ollama', label: '🦙 Llama Local (Ollama R$ 0)' },
])

const onProviderChange = () => {
  localStorage.setItem('empire_chosen_ai_provider', chosenProvider.value)
}

const fetchAiAvailabilityForUser = async () => {
  try {
    const res = await axios.get('/api/v1/ai-engine/status')
    if (res.data?.user_access) {
      canUseGemini.value = res.data.user_access.can_use_gemini !== false
      if (Array.isArray(res.data.user_access.available_options) && res.data.user_access.available_options.length > 0) {
        const backendOpts = res.data.user_access.available_options.map((opt) => ({
          ...opt,
          id: opt.id || opt.value,
          value: opt.value || opt.id,
        }))
        // Ensure Gemini is always present and selectable
        if (!backendOpts.some((o) => (o.id || o.value) === 'gemini')) {
          backendOpts.unshift({
            id: 'gemini',
            value: 'gemini',
            label: '✨ Google Gemini 3.8 Flash (Recomendado)',
            enabled: true,
          })
        }
        availableAiOptions.value = backendOpts

        // Ensure user preference from localStorage or active selection is never reset to ollama/hybrid
        const saved = localStorage.getItem('empire_chosen_ai_provider')
        if (saved) {
          chosenProvider.value = saved
        }
      }
    }
  } catch (e) {
    // Keep default options if status endpoint is unreachable
  }
}

// --- Enriquecimento de Contexto & Ações Rápidas ---
const quickActionPrompts = ref([
  { icon: '🔥', label: '5 Produtos Virais', prompt: 'Pesquise na internet os 5 produtos mais viralizados e vendidos na TikTok Shop Brasil esta semana com estimativa de preço e comissão.' },
  { icon: '🎯', label: '3 Hooks de 3s', prompt: 'Crie 3 ganchos (hooks) de 3 segundos de alta retenção psicológica e curiosidade para vender produtos no TikTok Shop.' },
  { icon: '📊', label: 'Métricas & Teto', prompt: 'Apresente o resumo executivo dos negócios do império, status do orçamento mensal e tarefas ativas.' },
  { icon: '⚙️', label: 'Monitor da VPS', prompt: 'Inspecione a integridade da VPS, uso de recursos dos containers e status dos workers em segundo plano.' },
])

const loadingStepText = computed(() => {
  if (chosenProvider.value === 'gemini') {
    return '✨ Processando inferência executiva via Google Gemini 3.8 Flash...'
  }
  if (chosenProvider.value === 'openai') {
    return '🤖 Processando inferência via OpenAI GPT-4o-mini...'
  }
  return '⚡ Jeffrey processando contexto, memórias e ferramentas...'
})

const openActivityMonitor = () => {
  if (isMobile.value) {
    mobileTab.value = 'monitor'
  } else {
    showActivityPanel.value = true
  }
  activitySubTab.value = 'tasks'
}

const formatToolName = (name) => {
  const map = {
    create_task_pipeline: 'Pipeline de Tarefas Encadeadas',
    create_task: 'Tarefa em Segundo Plano',
    web_search: 'Pesquisa Web em Tempo Real',
    list_projects: 'Inspeção de Projetos',
    read_project_file: 'Leitura de Arquivo',
    inspect_project: 'Análise de Código',
    list_businesses: 'Listagem de Negócios',
    get_business_status: 'Diagnóstico de Negócio',
    get_system_metrics: 'Métricas da VPS',
    list_docker_containers: 'Containers Docker',
  }
  return map[name] || name || 'Ação Automatizada'
}

const stripActionsTag = (text) => {
  if (!text) return ''
  return text.replace(/<suggested_actions>[\s\S]*?<\/suggested_actions>/gi, '').trim()
}

const getSuggestedActions = (msg) => {
  if (!msg || msg.role === 'user') return []
  if (Array.isArray(msg.tokens?.suggested_actions) && msg.tokens.suggested_actions.length > 0) {
    return msg.tokens.suggested_actions
  }
  const match = (msg.content || '').match(/<suggested_actions>([\s\S]*?)<\/suggested_actions>/i)
  if (match) {
    return match[1]
      .split('\n')
      .map((l) => l.replace(/^[-*•\d.]+\s*/, '').trim())
      .filter((l) => l.length > 0 && l.length < 80)
  }
  return []
}

const sendQuickPrompt = async (prompt) => {
  inputMessage.value = prompt
  await sendMessage()
}

const renderMarkdown = (text) => {
  if (!text) return ''
  let out = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks
  out = out.replace(/```([a-zA-Z0-9_\-\.]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const langLabel = lang ? lang.toUpperCase() : 'CÓDIGO'
    const cleanCode = code.trim()
    return `<div class="my-2.5 rounded bg-[#1e0d04] border border-[#784725] overflow-hidden text-[11px] font-mono shadow-sm">
      <div class="bg-[#2e1507] px-2.5 py-1 text-[10px] text-[#fbbf24] font-bold flex items-center justify-between border-b border-[#5c3419]">
        <span>💻 ${langLabel}</span>
      </div>
      <pre class="p-2.5 overflow-x-auto text-[#fff6e0] leading-relaxed select-text">${cleanCode}</pre>
    </div>`
  })

  // Inline code
  out = out.replace(/`([^`\n]+)`/g, '<code class="bg-[#2e1507] text-[#fbbf24] px-1 py-0.5 rounded text-[10.5px] font-mono border border-[#5c3419]">$1</code>')

  // Headers
  out = out.replace(/^### (.*$)/gim, '<h3 class="text-xs sm:text-sm font-black text-[#5c3419] border-b border-[#c49a6c]/40 pb-1 mt-3 mb-1.5 flex items-center gap-1">📌 $1</h3>')
  out = out.replace(/^## (.*$)/gim, '<h2 class="text-sm sm:text-base font-black text-[#3d1a08] border-b-2 border-[#8c5828]/50 pb-1 mt-3.5 mb-2">⚡ $1</h2>')
  out = out.replace(/^# (.*$)/gim, '<h1 class="text-base sm:text-lg font-black text-[#2b1507] border-b-2 border-[#f59e0b] pb-1.5 mt-4 mb-2.5">$1</h1>')

  // Bold & Italic
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-black text-[#1e0d04]">$1</strong>')
  out = out.replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>')

  // Blockquotes
  out = out.replace(/^> (.*$)/gim, '<blockquote class="border-l-4 border-[#f59e0b] pl-2.5 py-1 my-1.5 bg-[#f5ebd7] text-[#451a03] italic rounded-r text-[11px]">$1</blockquote>')

  // Bullet and numbered lists
  out = out.replace(/^[*\-] (.*$)/gim, '<div class="flex items-start gap-1.5 my-1 ml-1"><span class="text-[#d97706] font-black shrink-0">•</span><span>$1</span></div>')
  out = out.replace(/^(\d+)\. (.*$)/gim, '<div class="flex items-start gap-1.5 my-1 ml-1"><span class="text-[#d97706] font-bold shrink-0">$1.</span><span>$2</span></div>')

  // Links
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="text-blue-700 underline font-bold hover:text-blue-900 inline-flex items-center gap-0.5">$1 ↗</a>')

  // Horizontal rules
  out = out.replace(/^---$/gim, '<hr class="my-2.5 border-t border-[#8c5828]/40" />')

  // Line breaks
  out = out.replace(/\n\n/g, '<div class="h-2"></div>')
  out = out.replace(/\n/g, '<br />')

  return out
}

const chatContainer = ref(null)
const composerTextarea = ref(null)
const fileInputRef = ref(null)

// Copy & TTS State
const copiedId = ref(null)
const speakingId = ref(null)

// Attachments & Drag-and-drop State
const isDraggingOver = ref(false)
const pendingAttachments = ref([])

// Voice Recording & Speech Recognition State
const isRecordingVoice = ref(false)
const recordingSeconds = ref(0)
const liveSpeechTranscript = ref('')
let mediaRecorder = null
let recordedAudioChunks = []
let recordingTimer = null
let speechRecognition = null
let autoSendOnStop = false

const quickChips = [
  {
    label: '🔥 10 Virais TikTok Shop',
    prompt: 'Pesquise e identifique 10 produtos viralizados na TikTok Shop Brasil hoje com comissão >= 15% e crie 3 ganchos (hooks) de 3 segundos para cada um.',
  },
  {
    label: '🎬 Roteiro 30s Alta Conversão',
    prompt: 'Crie um roteiro completo de 30 segundos para TikTok Shop com gancho de impacto nos 3 primeiros segundos, demonstração de dor/solução e chamada para o carrinho laranja.',
  },
  {
    label: '📊 Status dos Meus Negócios',
    prompt: 'Liste todos os meus negócios ativos, suas contas vinculadas e parâmetros de automação atuais.',
  },
]

const applyQuickChip = (promptText) => {
  inputMessage.value = promptText
  nextTick(() => {
    composerTextarea.value?.focus()
  })
}

const copyText = async (text, id) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copiedId.value = id
    setTimeout(() => {
      if (copiedId.value === id) copiedId.value = null
    }, 2200)
  } catch (_) {
    // Fallback for non-HTTPS or older browsers
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copiedId.value = id
    setTimeout(() => {
      if (copiedId.value === id) copiedId.value = null
    }, 2200)
  }
}

const toggleSpeakMessage = (text, id) => {
  if (!('speechSynthesis' in window)) {
    return alert('Seu navegador não suporta síntese de voz.')
  }
  if (speakingId.value === id) {
    window.speechSynthesis.cancel()
    speakingId.value = null
    return
  }
  window.speechSynthesis.cancel()
  const cleanText = text.replace(/[#*_`~>\[\]]/g, '')
  const utter = new SpeechSynthesisUtterance(cleanText)
  utter.lang = 'pt-BR'
  utter.rate = 1.05
  utter.onend = () => {
    if (speakingId.value === id) speakingId.value = null
  }
  speakingId.value = id
  window.speechSynthesis.speak(utter)
}

const formatBytes = (bytes) => {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / (1024 * 1024)).toFixed(2)} MB`
}

const formatRecordingDuration = (sec) => {
  const m = String(Math.floor(sec / 60)).padStart(2, '0')
  const s = String(sec % 60).padStart(2, '0')
  return `${m}:${s}`
}

const triggerFilePicker = () => {
  fileInputRef.value?.click()
}

const processFileObject = (file, isVoice = false) => {
  return new Promise((resolve) => {
    const mime = file.type || (isVoice ? 'audio/webm' : 'application/octet-stream')
    const isImage = mime.startsWith('image/')
    const isAudio = isVoice || mime.startsWith('audio/')
    const isTextLike = /(text\/|json|xml|csv|javascript|markdown|\.md$|\.txt$|\.csv$|\.py$|\.php$|\.js$|\.ts$|\.html$|\.log$)/i.test(
      mime + ' ' + file.name
    )

    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result || ''
      if (isTextLike) {
        const textReader = new FileReader()
        textReader.onload = (tev) => {
          resolve({
            name: file.name,
            mime_type: mime,
            size: file.size,
            is_image: isImage,
            is_voice: isAudio,
            preview_url: isImage || isAudio ? URL.createObjectURL(file) : '',
            data_base64: dataUrl,
            text_content: String(tev.target?.result || '').slice(0, 24000),
          })
        }
        textReader.readAsText(file)
      } else {
        resolve({
          name: file.name,
          mime_type: mime,
          size: file.size,
          is_image: isImage,
          is_voice: isAudio,
          preview_url: isImage || isAudio ? URL.createObjectURL(file) : '',
          data_base64: dataUrl,
          text_content: '',
        })
      }
    }
    reader.readAsDataURL(file)
  })
}

const handleFileSelect = async (e) => {
  const files = Array.from(e.target?.files || [])
  for (const f of files.slice(0, 6)) {
    const att = await processFileObject(f)
    pendingAttachments.value.push(att)
  }
  if (fileInputRef.value) fileInputRef.value.value = ''
}

const handleDropFiles = async (e) => {
  isDraggingOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  for (const f of files.slice(0, 6)) {
    const att = await processFileObject(f)
    pendingAttachments.value.push(att)
  }
}

const handleEditorPaste = async (e) => {
  const items = Array.from(e.clipboardData?.items || [])
  for (const item of items) {
    if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file) {
        const att = await processFileObject(file)
        pendingAttachments.value.push(att)
      }
    }
  }
}

const removePendingAttachment = (idx) => {
  pendingAttachments.value.splice(idx, 1)
}

const handleEditorKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// --- VOICE RECORDING (MediaRecorder + Web Speech API Live Transcription) ---
const toggleVoiceRecording = async () => {
  if (isRecordingVoice.value) {
    stopVoiceRecording(false)
    return
  }

  liveSpeechTranscript.value = ''
  recordedAudioChunks = []
  recordingSeconds.value = 0
  autoSendOnStop = false

  // 1. Start Web Speech API (pt-BR) if available in browser for instant transcription
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SpeechRec) {
    try {
      speechRecognition = new SpeechRec()
      speechRecognition.lang = 'pt-BR'
      speechRecognition.continuous = true
      speechRecognition.interimResults = true
      speechRecognition.onresult = (event) => {
        let transcript = ''
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript + ' '
        }
        liveSpeechTranscript.value = transcript.trim()
      }
      speechRecognition.start()
    } catch (_) {}
  }

  // 2. Start MediaRecorder for real voice audio file attachment
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus') ? 'audio/ogg;codecs=opus' : '')

      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      mediaRecorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) {
          recordedAudioChunks.push(ev.data)
        }
      }
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        if (recordedAudioChunks.length > 0) {
          const blob = new Blob(recordedAudioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
          const ext = (mediaRecorder.mimeType || '').includes('ogg') ? 'ogg' : 'webm'
          const voiceFile = new File([blob], `voz_${Date.now()}.${ext}`, { type: blob.type || 'audio/webm' })
          const att = await processFileObject(voiceFile, true)
          pendingAttachments.value.push(att)
        }
        if (liveSpeechTranscript.value) {
          inputMessage.value = (inputMessage.value ? inputMessage.value + ' ' : '') + liveSpeechTranscript.value
          liveSpeechTranscript.value = ''
        }
        if (autoSendOnStop) {
          autoSendOnStop = false
          await sendMessage()
        }
      }

      mediaRecorder.start(250)
      isRecordingVoice.value = true
      recordingTimer = setInterval(() => {
        recordingSeconds.value += 1
      }, 1000)
    } catch (err) {
      alert('Não foi possível acessar o microfone. Verifique a permissão de áudio no navegador.')
    }
  } else if (speechRecognition) {
    isRecordingVoice.value = true
    recordingTimer = setInterval(() => {
      recordingSeconds.value += 1
    }, 1000)
  } else {
    alert('Seu navegador não suporta gravação de áudio.')
  }
}

const stopVoiceRecording = (sendImmediately = false) => {
  autoSendOnStop = sendImmediately
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  if (speechRecognition) {
    try {
      speechRecognition.stop()
    } catch (_) {}
    speechRecognition = null
  }
  isRecordingVoice.value = false
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  } else if (liveSpeechTranscript.value) {
    inputMessage.value = (inputMessage.value ? inputMessage.value + ' ' : '') + liveSpeechTranscript.value
    liveSpeechTranscript.value = ''
    if (sendImmediately) sendMessage()
  }
}

const cancelVoiceRecording = () => {
  autoSendOnStop = false
  recordedAudioChunks = []
  liveSpeechTranscript.value = ''
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  if (speechRecognition) {
    try {
      speechRecognition.stop()
    } catch (_) {}
    speechRecognition = null
  }
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.onstop = () => {}
    mediaRecorder.stop()
  }
  isRecordingVoice.value = false
}

const showActivityPanel = ref(typeof window !== 'undefined' ? window.innerWidth >= 1440 : false)

const selectConversationMobile = (id) => {
  selectConversation(id)
  if (isMobile.value) {
    mobileTab.value = 'chat'
  }
}

const createNewConversationMobile = async () => {
  await createNewConversation()
  if (isMobile.value) {
    mobileTab.value = 'chat'
  }
}

const activitySubTab = ref('tasks')
const expandedTaskId = ref(null)
const jeffreyActivity = ref({
  is_working: false,
  queue_length: 0,
  worker_state: { status: 'idle', step: 'Ocioso — Aguardando novas ordens.', progress_percent: 0 },
  counts: { total: 0, pending: 0, in_progress: 0, completed: 0, failed: 0, cancelled: 0 },
  active_tasks: [],
  recent_tasks: [],
  recent_decisions: [],
})
let lastCompletedCount = 0

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const fetchJeffreyActivity = async () => {
  try {
    const res = await axios.get('/api/v1/jeffrey/activity')
    if (res.data?.success) {
      const prevCompleted = lastCompletedCount
      const newCompleted = res.data.counts?.completed || 0
      jeffreyActivity.value = res.data
      lastCompletedCount = newCompleted

      if (newCompleted > prevCompleted && activeConversationId.value && !loading.value) {
        selectConversation(activeConversationId.value)
      }
    }
  } catch (e) {
    console.error('Falha ao obter atividades do Jeffrey:', e)
  }
}

const formatTaskStatus = (st) => {
  const map = {
    pending: '⏳ NA FILA',
    in_progress: '⚙️ FAZENDO',
    completed: '✅ CONCLUÍDO',
    failed: '❌ FALHOU',
    cancelled: '🚫 CANCELADO',
  }
  return map[st] || st
}

const formatTimeShort = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (_) {
    return ''
  }
}

const showNewTaskModal = ref(false)
const submittingTask = ref(false)
const newTaskForm = ref({
  agent_name: 'TikTok Shop Strategist',
  type: 'research_and_execution',
  prompt: '',
})

const promptNewBackgroundTask = () => {
  newTaskForm.value.prompt = ''
  showNewTaskModal.value = true
}

const submitNewBackgroundTask = async () => {
  const promptText = newTaskForm.value.prompt.trim()
  if (!promptText || submittingTask.value) return
  submittingTask.value = true
  try {
    const res = await axios.post('/api/v1/tasks', {
      title: promptText.slice(0, 120),
      type: newTaskForm.value.type,
      agent_name: newTaskForm.value.agent_name,
      payload: {
        prompt: promptText,
        provider: chosenProvider.value,
        conversation_id: activeConversationId.value,
      },
    })
    if (res.data?.task) {
      showNewTaskModal.value = false
      showActivityPanel.value = true
      if (isMobile.value) {
        mobileTab.value = 'monitor'
      }
      activitySubTab.value = 'tasks'
      await fetchJeffreyActivity()
      if (activeConversationId.value) {
        messages.value.push({
          role: 'assistant',
          content: `⚙️ **[Tarefa #${res.data.task.id} Enfileirada — ${res.data.task.agent_name}]:** _${res.data.task.title}_\n\nAcompanhe o progresso na barra lateral **Monitor do Jeffrey**. Assim que finalizar, o resultado completo será entregue aqui no chat!`,
          provider: 'jeffrey-worker',
        })
        scrollToBottom()
      }
    }
  } catch (e) {
    alert('Erro ao criar tarefa: ' + (e.response?.data?.message || e.message))
  } finally {
    submittingTask.value = false
  }
}

const retryTask = async (taskId) => {
  try {
    await axios.post(`/api/v1/tasks/${taskId}/retry`)
    await fetchJeffreyActivity()
  } catch (e) {
    alert('Erro ao reenfileirar tarefa: ' + (e.response?.data?.message || e.message))
  }
}

const cancelTask = async (taskId) => {
  try {
    await axios.post(`/api/v1/tasks/${taskId}/cancel`)
    await fetchJeffreyActivity()
  } catch (e) {
    alert('Erro ao cancelar tarefa: ' + (e.response?.data?.message || e.message))
  }
}

const sendTaskResultToChat = (task) => {
  if (!task?.result?.response) return
  messages.value.push({
    role: 'assistant',
    content: `📋 **[Resultado da Tarefa #${task.id} — ${task.title}]:**\n\n${task.result.response}`,
    provider: task.result.provider || 'worker',
    latency_ms: task.result.latency_ms || 0,
  })
  scrollToBottom()
  if (isMobile.value) {
    mobileTab.value = 'chat'
  }
}

const fetchConversations = async () => {
  loadingConversations.value = true
  try {
    const res = await axios.get('/api/v1/chat/conversations')
    if (res.data?.conversations) {
      conversations.value = res.data.conversations
      if (conversations.value.length > 0 && !activeConversationId.value) {
        selectConversation(conversations.value[0].id)
      } else if (conversations.value.length === 0) {
        createNewConversation()
      }
    }
  } catch (err) {
    console.error('Falha ao listar conversas:', err)
  } finally {
    loadingConversations.value = false
  }
}

const selectConversation = async (id) => {
  activeConversationId.value = id
  try {
    const res = await axios.get(`/api/v1/chat/conversations/${id}`)
    if (res.data?.conversation) {
      currentConversation.value = res.data.conversation
      messages.value = res.data.conversation.messages || []
      scrollToBottom()
    }
  } catch (err) {
    console.error('Falha ao obter mensagens da conversa:', err)
  }
}

const createNewConversation = async () => {
  creatingChat.value = true
  try {
    const res = await axios.post('/api/v1/chat/conversations', {
      title: 'Nova Conversa',
    })
    if (res.data?.conversation) {
      conversations.value.unshift(res.data.conversation)
      selectConversation(res.data.conversation.id)
    }
  } catch (err) {
    console.error('Falha ao criar conversa:', err)
  } finally {
    creatingChat.value = false
  }
}

const deleteConversation = async (id) => {
  if (!confirm('Deseja excluir esta conversa e seu histórico?')) return
  try {
    await axios.delete(`/api/v1/chat/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeConversationId.value === id) {
      if (conversations.value.length > 0) {
        selectConversation(conversations.value[0].id)
      } else {
        messages.value = []
        activeConversationId.value = null
        currentConversation.value = null
      }
    }
  } catch (err) {
    console.error('Falha ao excluir conversa:', err)
  }
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  const attachmentsToSend = [...pendingAttachments.value]

  if ((!text && attachmentsToSend.length === 0) || loading.value) return

  if (!activeConversationId.value) {
    await createNewConversation()
  }

  inputMessage.value = ''
  pendingAttachments.value = []

  const displayText = text || (attachmentsToSend.some(a => a.is_voice)
    ? '🎙️ [Mensagem de Voz enviada]'
    : `📎 [${attachmentsToSend.length} anexo(s) enviado(s)]`)

  messages.value.push({
    role: 'user',
    content: displayText,
    attachments: attachmentsToSend,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()
  loading.value = true

  try {
    const res = await axios.post(`/api/v1/chat/conversations/${activeConversationId.value}/messages`, {
      message: text,
      provider: chosenProvider.value,
      attachments: attachmentsToSend.map((a) => ({
        name: a.name,
        mime_type: a.mime_type,
        size: a.size,
        is_voice: a.is_voice,
        is_image: a.is_image,
        data_base64: a.data_base64,
        text_content: a.text_content,
      })),
    })

    if (res.data?.message) {
      messages.value.push(res.data.message)
      const conv = conversations.value.find(c => c.id === activeConversationId.value)
      if (conv && conv.title === 'Nova Conversa') {
        conv.title = displayText.slice(0, 30) + '...'
      }
      fetchJeffreyActivity()
      scrollToBottom()
    }
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: `[Jeffrey Modo Resiliente]: Erro ao processar mensagem via API. Detalhes: ${err.response?.data?.message || err.message}`,
      provider: 'offline-error',
    })
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

let pollTimer = null
onMounted(() => {
  window.addEventListener('resize', onResize)
  onResize()
  fetchAiAvailabilityForUser()
  fetchConversations()
  fetchJeffreyActivity()
  pollTimer = setInterval(fetchJeffreyActivity, 4000)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (pollTimer) clearInterval(pollTimer)
  cancelVoiceRecording()
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
})
</script>
