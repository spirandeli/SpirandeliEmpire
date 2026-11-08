<script setup>
import { ref, computed } from 'vue'
import { useLanguageStore } from '@/stores/language'
import { useSwal } from '@/composables/useSwal'
import AudioRecorder from '@/components/AudioRecorder.vue'

const languageStore = useLanguageStore()
const swal = useSwal()

// Frases de treino por idioma e nível
const DRILL_PHRASES_BY_LANG = {
  Inglês: [
    {
      level: 'A1-A2',
      category: 'Apresentação & Conexões Básicas',
      text: 'I am an operations manager and I work with international teams.',
      focus: 'Vogais curtas em "am/and", pronúncia do "work" sem som de "rqui"',
    },
    {
      level: 'A2-B1',
      category: 'Horários & Verbos Regulares',
      text: 'What time do you usually start work in the morning?',
      focus: 'Linking sound "what time", "usually" com som suave de /ʒ/',
    },
    {
      level: 'B1-B2',
      category: 'Idiom Corporativo (Touch base)',
      text: "Let's touch base next Tuesday to review the launch metrics.",
      focus: 'Terminação em consoante sem vogal de apoio ("touch base")',
    },
    {
      level: 'B2-C1',
      category: 'Colocações de Negociação',
      text: 'After intense deliberation, both commercial teams reached a solid compromise.',
      focus: 'Pronúncia do passado em -ed ("reached" com som de /t/), tonicidade em "compromise"',
    },
    {
      level: 'C1',
      category: 'Estimativas Executivas (Ballpark figure)',
      text: 'Could you please provide a ballpark figure for the quarterly infrastructure budget?',
      focus: 'Dark L em "ballpark", som aspirado do "could you" (/kʊdʒuː/)',
    },
  ],
  Espanhol: [
    {
      level: 'A1-A2',
      category: 'Presentación Profesional',
      text: 'Soy gerente de operaciones y trabajo con equipos internacionales.',
      focus: 'Sonido suave de la "g" en "gerente" y "j" en "trabajo" sin aspiración inglesa',
    },
    {
      level: 'B1-B2',
      category: 'Alineación de Negocios (Ponerse al día)',
      text: 'Pongámonos al día el próximo martes para revisar las métricas clave.',
      focus: 'Entonación fluida y unión de palabras en "al día el"',
    },
    {
      level: 'B2-C1',
      category: 'Negociación y Acuerdos',
      text: 'Ambos equipos comerciales lograron alcanzar un acuerdo mutuamente beneficioso.',
      focus: 'Vibrante simple vs múltiple en "lograron" y "alcanzar"',
    },
  ],
  Francês: [
    {
      level: 'A1-A2',
      category: 'Présentation',
      text: 'Je suis responsable des opérations et je travaille avec des équipes internationales.',
      focus: 'Vogais nasais e o "r" uvular suave em "responsable"',
    },
    {
      level: 'B1-B2',
      category: 'Point d\'étape (Faire le point)',
      text: 'Faisons le point mardi prochain pour passer en revue les résultats.',
      focus: 'Liaison entre "en" e "revue", ritmo acentual no final das palavras',
    },
  ],
  Alemão: [
    {
      level: 'A1-A2',
      category: 'Vorstellung',
      text: 'Ich bin Operations Manager und arbeite mit internationalen Teams.',
      focus: 'Som de ich-Laut em "Ich", sem som de "X" português',
    },
    {
      level: 'B1-B2',
      category: 'Abstimmung (Kurzschließen)',
      text: 'Lassen Sie uns nächste Woche kurzschließen, um die Zahlen durchzugehen.',
      focus: 'Umlaut em "nächste" e oclusão glotal antes de vogais iniciais',
    },
  ],
  Italiano: [
    {
      level: 'A1-A2',
      category: 'Presentazione',
      text: 'Sono responsabile delle operazioni e lavoro con team internazionali.',
      focus: 'Consoantes duplas em "delle" e abertura das vogais',
    },
    {
      level: 'B1-B2',
      category: 'Aggiornamento (Aggiorniamoci)',
      text: 'Aggiorniamoci martedì prossimo per verificare insieme le metriche chiave.',
      focus: 'Som suave de "ch" em "chiave" e entonação melódica',
    },
  ],
  Mandarim: [
    {
      level: 'A1-A2',
      category: '自我介绍 (Apresentação)',
      text: '我是运营经理，我和国际团队一起工作。(Wǒ shì yùnyíng jīnglǐ, wǒ hé guójì tuánduì yīqǐ gōngzuò.)',
      focus: 'Tons corretos: shì (4º), jīnglǐ (1º e 3º)',
    },
    {
      level: 'B1-B2',
      category: '商务沟通 (Touch Base)',
      text: '我们下周二碰一下，对一下关键数据指标。(Wǒmen xià zhōu èr pèng yīxià, duì yīxià guānjiàn shùjù zhǐbiāo.)',
      focus: 'Ritmo natural de "pèng yīxià", tons 4º em "duì" e "shùjù"',
    },
  ],
}

const targetLanguage = computed(() => languageStore.profile?.target_language || 'Inglês')
const availableDrills = computed(() => DRILL_PHRASES_BY_LANG[targetLanguage.value] || DRILL_PHRASES_BY_LANG['Inglês'])

const selectedPhrase = ref(availableDrills.value[0]?.text || 'I work with international teams.')
const customPhraseMode = ref(false)
const customPhraseInput = ref('')

const activePhraseToPractice = computed(() => {
  if (customPhraseMode.value && customPhraseInput.value.trim()) {
    return customPhraseInput.value.trim()
  }
  return selectedPhrase.value
})

const analysisResult = computed(() => languageStore.pronunciationResult)
const isLoading = computed(() => languageStore.pronunciationLoading)

function selectDrill(drill) {
  customPhraseMode.value = false
  selectedPhrase.value = drill.text
  languageStore.pronunciationResult = null
}

function speakText(text) {
  if (!window.speechSynthesis || !text) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  const lang = targetLanguage.value
  const langCodeMap = {
    Inglês: 'en-US',
    Espanhol: 'es-ES',
    Francês: 'fr-FR',
    Alemão: 'de-DE',
    Italiano: 'it-IT',
    Mandarim: 'zh-CN',
  }
  utterance.lang = langCodeMap[lang] || 'en-US'
  utterance.rate = 0.9
  window.speechSynthesis.speak(utterance)
}

async function handleAudioRecorded({ base64, mimeType }) {
  try {
    const analysis = await languageStore.analyzePronunciation({
      target_text: activePhraseToPractice.value,
      audio_base64: base64,
      mime_type: mimeType,
    })

    if (analysis.overall_score >= 80) {
      swal.toast(`Excelente dicção! Nota: ${analysis.overall_score}/100`, 'success')
    } else {
      swal.toast(`Análise concluída. Confira os pontos de correção anatômica abaixo!`, 'info')
    }
  } catch (err) {
    swal.error('Erro na análise de áudio', err.response?.data?.message || 'Falha ao processar o áudio no Gemini.')
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header do Treino de Dicção & Pronúncia -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div class="absolute -top-12 -right-12 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
            <span class="text-xs font-mono uppercase font-bold text-rose-400">Coach Fonético com Gemini 3.8 Flash</span>
          </div>
          <h2 class="text-xl font-bold text-white">Laboratório de Dicção & Pronúncia</h2>
          <p class="text-xs text-slate-400 max-w-2xl">
            Grave sua fala no idioma <strong class="text-white">{{ targetLanguage }}</strong>. A inteligência artificial analisa
            sua articulação fonética, ritmo e vícios comuns de brasileiros, ensinando onde posicionar língua e lábios para soar 100% natural.
          </p>
        </div>

        <div class="shrink-0 text-right bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
          <span class="text-[10px] font-mono uppercase text-slate-400 block font-bold">Idioma Ativo</span>
          <span class="text-sm font-bold text-white">{{ targetLanguage }}</span>
          <span class="text-[11px] font-mono text-emerald-400 block mt-0.5">Nível: {{ languageStore.profile?.cefr_level || 'B1' }}</span>
        </div>
      </div>
    </div>

    <!-- SELETOR DE FRASES DE TREINO -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-white flex items-center space-x-2">
          <span>🎯</span>
          <span>1. Escolha a Frase de Prática</span>
        </h3>

        <button
          type="button"
          @click="customPhraseMode = !customPhraseMode"
          class="text-xs font-mono text-slate-400 hover:text-rose-400 transition"
        >
          {{ customPhraseMode ? '← Usar Frases Recomendadas' : '+ Digitar Frase Própria' }}
        </button>
      </div>

      <!-- Modo 1: Frases Recomendadas por Nível -->
      <div v-if="!customPhraseMode" class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <button
          v-for="(drill, idx) in availableDrills"
          :key="idx"
          type="button"
          @click="selectDrill(drill)"
          class="p-4 rounded-xl border text-left transition space-y-2 flex flex-col justify-between"
          :class="selectedPhrase === drill.text
            ? 'bg-rose-500/10 border-rose-500/40 shadow-sm shadow-rose-500/10'
            : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'"
        >
          <div class="flex items-center justify-between w-full">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
              {{ drill.level }}
            </span>
            <span class="text-[10px] font-mono text-slate-400">{{ drill.category }}</span>
          </div>

          <p class="text-xs font-serif font-bold" :class="selectedPhrase === drill.text ? 'text-white' : 'text-slate-300'">
            "{{ drill.text }}"
          </p>

          <span class="text-[10px] text-slate-400 italic block">
            💡 Foco: {{ drill.focus }}
          </span>
        </button>
      </div>

      <!-- Modo 2: Digitar Frase Própria -->
      <div v-else class="space-y-2">
        <label class="text-xs font-mono text-slate-300 font-bold">Digite qualquer frase ou parágrafo em {{ targetLanguage }}:</label>
        <textarea
          v-model="customPhraseInput"
          rows="2"
          class="w-full bg-slate-950 border border-slate-800 focus:border-rose-500 rounded-xl p-3 text-xs text-white placeholder-slate-600 focus:outline-none transition"
          :placeholder="`Ex: Good morning everyone, let's review the strategic deliverables...`"
        ></textarea>
      </div>

      <!-- Preview da Frase Ativa com Botão de Ouvir Modelo Nativo -->
      <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="space-y-0.5">
          <span class="text-[10px] font-mono uppercase text-slate-400 font-bold block">Frase Selecionada para Gravação:</span>
          <p class="text-sm font-serif font-bold text-rose-300">"{{ activePhraseToPractice }}"</p>
        </div>

        <button
          type="button"
          @click="speakText(activePhraseToPractice)"
          class="px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 font-bold text-xs transition flex items-center justify-center space-x-2 shrink-0"
          title="Ouvir como um nativo pronuncia"
        >
          <span>🔊 Ouvir Pronúncia Modelo</span>
        </button>
      </div>
    </div>

    <!-- GRAVADOR DE ÁUDIO -->
    <div class="space-y-3">
      <h3 class="text-sm font-bold text-white flex items-center space-x-2">
        <span>🎙️</span>
        <span>2. Grave sua Voz e Submeta para a IA</span>
      </h3>

      <AudioRecorder
        submit-label="Analisar Dicção com Gemini"
        @recorded="handleAudioRecorded"
      />
    </div>

    <!-- LOADING DA ANÁLISE -->
    <div v-if="isLoading" class="p-12 text-center space-y-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
      <div class="w-10 h-10 rounded-full border-4 border-rose-500/20 border-t-rose-500 animate-spin mx-auto"></div>
      <p class="text-xs font-mono text-slate-300">Gemini 3.8 Flash analisando fonemas, cadência e dicção do áudio...</p>
    </div>

    <!-- RESULTADO DO DIAGNÓSTICO FONÉTICO -->
    <div v-else-if="analysisResult" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
      <!-- Top Score Badge -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border"
        :class="analysisResult.overall_score >= 80
          ? 'bg-emerald-950/20 border-emerald-500/30'
          : 'bg-amber-950/20 border-amber-500/30'"
      >
        <div>
          <span class="text-xs font-mono uppercase tracking-widest font-bold block mb-1"
            :class="analysisResult.overall_score >= 80 ? 'text-emerald-400' : 'text-amber-400'"
          >
            ⚡ Avaliação Fonética & Dicção
          </span>
          <h3 class="text-lg font-bold text-white">
            {{ analysisResult.overall_score >= 80 ? 'Excelente Articulação!' : 'Pontos de Ajuste Detectados' }}
          </h3>
          <p class="text-xs text-slate-300 mt-0.5">
            O que a IA ouviu: <strong class="text-white font-mono font-normal">"{{ analysisResult.transcription }}"</strong>
          </p>
        </div>

        <div class="flex items-center space-x-4">
          <div class="text-center">
            <span class="text-[10px] font-mono text-slate-400 uppercase block">Clareza</span>
            <span class="text-xl font-bold font-mono text-indigo-400">{{ analysisResult.clarity_score || 85 }}%</span>
          </div>
          <div class="text-center">
            <span class="text-[10px] font-mono text-slate-400 uppercase block">Ritmo</span>
            <span class="text-xl font-bold font-mono text-amber-400">{{ analysisResult.rhythm_score || 80 }}%</span>
          </div>
          <div class="text-center pl-3 border-l border-slate-800">
            <span class="text-[10px] font-mono text-slate-400 uppercase block font-bold">Nota Geral</span>
            <span class="text-3xl font-black font-mono"
              :class="analysisResult.overall_score >= 80 ? 'text-emerald-400' : 'text-amber-400'"
            >
              {{ analysisResult.overall_score }}
            </span>
            <span class="text-xs text-slate-500">/100</span>
          </div>
        </div>
      </div>

      <!-- Erros Fonéticos Específicos -->
      <div v-if="analysisResult.phonetic_errors?.length" class="space-y-3">
        <h4 class="text-xs font-mono font-bold uppercase text-rose-400 flex items-center space-x-2">
          <span>⚠️</span>
          <span>Desvios Fonéticos Identificados:</span>
        </h4>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            v-for="(err, eIdx) in analysisResult.phonetic_errors"
            :key="eIdx"
            class="p-4 rounded-xl bg-slate-950 border border-rose-500/20 space-y-2"
          >
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-xs font-mono">Palavra: <strong class="text-rose-400">{{ err.word }}</strong></span>
              <span v-if="err.phonetic_ipa" class="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded">{{ err.phonetic_ipa }}</span>
            </div>
            <p v-if="err.heard_as" class="text-xs text-slate-400">
              Soou como: <strong class="text-slate-200">"{{ err.heard_as }}"</strong>
            </p>
            <p class="text-xs text-slate-300 leading-relaxed font-sans">
              {{ err.issue || err.correction_tip }}
            </p>
          </div>
        </div>
      </div>

      <!-- Instrução Anatômica do Coach (Onde colocar língua/dentes) -->
      <div v-if="analysisResult.coaching_instruction" class="p-5 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-2">
        <div class="flex items-center space-x-2 text-indigo-400 text-xs font-mono font-bold">
          <span>🧠</span>
          <span>Instrução Corretiva do Coach Fonoaudiólogo:</span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-sans">
          {{ analysisResult.coaching_instruction }}
        </p>
      </div>

      <!-- Micro-Exercício de Repetição -->
      <div v-if="analysisResult.practice_drill" class="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="space-y-0.5">
          <span class="text-[10px] font-mono uppercase text-emerald-400 font-bold block">Micro-Exercício Recomendado:</span>
          <p class="text-xs text-slate-200 font-mono">"{{ analysisResult.practice_drill }}"</p>
        </div>
        <button
          type="button"
          @click="speakText(analysisResult.practice_drill)"
          class="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-xs font-bold transition flex items-center space-x-1.5 shrink-0"
        >
          <span>🔊 Ouvir Exercício</span>
        </button>
      </div>
    </div>
  </div>
</template>

