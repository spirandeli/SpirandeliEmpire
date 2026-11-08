import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export const useLanguageStore = defineStore('language', () => {
  const profile = ref(null)
  const hasProfile = ref(false)
  const stats = ref({
    due_reviews_count: 0,
    total_vault_words: 0,
    streak_days: 0,
    flash_tokens_used: 0,
    flash_cost_usd: 0.0,
    flash_calls_count: 0,
  })

  const currentSession = ref(null)
  const placementTest = ref(null)
  const vaultItems = ref([])
  const vaultStats = ref({
    total: 0,
    mastered: 0,
    learning: 0,
    due_today: 0,
  })

  // Estado da Conversação Aberta e Prática de Áudio
  const conversationMessages = ref([])
  const practiceTopics = ref([])
  const conversationLoading = ref(false)
  const pronunciationLoading = ref(false)
  const pronunciationResult = ref(null)

  const loading = ref(false)
  const sessionLoading = ref(false)
  const actionLoading = ref(false)
  const error = ref(null)

  const isPlacementNeeded = computed(() => {
    return hasProfile.value && (!profile.value?.cefr_level || profile.value?.cefr_level === 'UNSET')
  })

  const cefrProgressPercentage = computed(() => {
    const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    const current = profile.value?.cefr_level
    const index = levels.indexOf(current)
    if (index === -1) return 10
    return Math.min(100, Math.round(((index + 1) / levels.length) * 100))
  })

  async function fetchProfile() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/languages/profile')
      profile.value = response.data.profile
      hasProfile.value = response.data.has_profile
      if (response.data.stats) {
        stats.value = response.data.stats
      }
      return profile.value
    } catch (err) {
      error.value = err.response?.data?.message || 'Erro ao carregar perfil de idiomas.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createProfile(payload) {
    actionLoading.value = true
    try {
      const response = await api.post('/languages/profile', payload)
      profile.value = response.data.profile
      hasProfile.value = true
      return response.data
    } finally {
      actionLoading.value = false
    }
  }

  async function updateSchedule(payload) {
    if (!profile.value?.id) return
    actionLoading.value = true
    try {
      const response = await api.put(`/languages/profiles/${profile.value.id}/schedule`, payload)
      profile.value = response.data.profile
      return response.data
    } finally {
      actionLoading.value = false
    }
  }

  async function fetchPlacementTest() {
    if (!profile.value?.id) return
    sessionLoading.value = true
    try {
      const response = await api.get(`/languages/profiles/${profile.value.id}/placement-test`)
      placementTest.value = response.data.placement_test || response.data
      return placementTest.value
    } finally {
      sessionLoading.value = false
    }
  }

  async function submitPlacementTest(payload) {
    if (!profile.value?.id) return
    actionLoading.value = true
    try {
      const response = await api.post(`/languages/profiles/${profile.value.id}/placement-test`, payload)
      profile.value = response.data.profile
      placementTest.value = null
      return response.data
    } finally {
      actionLoading.value = false
    }
  }

  async function fetchTodaySession() {
    if (!profile.value?.id) return
    sessionLoading.value = true
    try {
      const response = await api.get(`/languages/profiles/${profile.value.id}/today`)
      currentSession.value = response.data.session
      return currentSession.value
    } finally {
      sessionLoading.value = false
    }
  }

  async function submitDailySession(payload) {
    if (!profile.value?.id || !currentSession.value?.id) return
    actionLoading.value = true
    try {
      const response = await api.post(
        `/languages/profiles/${profile.value.id}/sessions/${currentSession.value.id}/submit`,
        payload
      )
      currentSession.value = response.data.session
      profile.value = response.data.profile
      await fetchProfile()
      return response.data
    } finally {
      actionLoading.value = false
    }
  }

  async function fetchVault() {
    if (!profile.value?.id) return
    try {
      const response = await api.get(`/languages/profiles/${profile.value.id}/vault`)
      vaultItems.value = response.data.items
      vaultStats.value = response.data.stats
      return response.data
    } catch (err) {
      console.error('Erro ao buscar cofre:', err)
    }
  }

  async function addVaultWord(payload) {
    if (!profile.value?.id) return
    const response = await api.post(`/languages/profiles/${profile.value.id}/vault`, payload)
    vaultItems.value.unshift(response.data.item)
    vaultStats.value.total += 1
    return response.data
  }

  async function deleteVaultWord(wordId) {
    if (!profile.value?.id) return
    await api.delete(`/languages/profiles/${profile.value.id}/vault/${wordId}`)
    vaultItems.value = vaultItems.value.filter((item) => item.id !== wordId)
    vaultStats.value.total = Math.max(0, vaultStats.value.total - 1)
  }

  async function reviewVaultWord(wordId, remembered = true) {
    if (!profile.value?.id) return
    const response = await api.post(`/languages/profiles/${profile.value.id}/vault/${wordId}/review`, {
      remembered,
    })
    const idx = vaultItems.value.findIndex((item) => item.id === wordId)
    if (idx !== -1) {
      vaultItems.value[idx] = response.data.item
    }
    await fetchVault()
    return response.data
  }

  async function analyzePronunciation(payload) {
    if (!profile.value?.id) return
    pronunciationLoading.value = true
    try {
      const response = await api.post(`/languages/profiles/${profile.value.id}/pronunciation/analyze`, payload)
      pronunciationResult.value = response.data.analysis
      return response.data.analysis
    } finally {
      pronunciationLoading.value = false
    }
  }

  async function fetchConversation() {
    if (!profile.value?.id) return
    conversationLoading.value = true
    try {
      const response = await api.get(`/languages/profiles/${profile.value.id}/conversation`)
      conversationMessages.value = response.data.messages || []
      practiceTopics.value = response.data.topics || []
      return response.data
    } finally {
      conversationLoading.value = false
    }
  }

  async function sendConversationMessage(payload) {
    if (!profile.value?.id) return
    conversationLoading.value = true
    try {
      const response = await api.post(`/languages/profiles/${profile.value.id}/conversation/message`, payload)
      if (response.data.user_message && response.data.assistant_message) {
        conversationMessages.value.push(response.data.user_message)
        conversationMessages.value.push(response.data.assistant_message)
      }
      return response.data
    } finally {
      conversationLoading.value = false
    }
  }

  async function clearConversation() {
    if (!profile.value?.id) return
    conversationLoading.value = true
    try {
      const response = await api.delete(`/languages/profiles/${profile.value.id}/conversation`)
      conversationMessages.value = []
      return response.data
    } finally {
      conversationLoading.value = false
    }
  }

  return {
    profile,
    hasProfile,
    stats,
    currentSession,
    placementTest,
    vaultItems,
    vaultStats,
    conversationMessages,
    practiceTopics,
    conversationLoading,
    pronunciationLoading,
    pronunciationResult,
    loading,
    sessionLoading,
    actionLoading,
    error,
    isPlacementNeeded,
    cefrProgressPercentage,
    fetchProfile,
    createProfile,
    updateSchedule,
    fetchPlacementTest,
    submitPlacementTest,
    fetchTodaySession,
    submitDailySession,
    fetchVault,
    addVaultWord,
    deleteVaultWord,
    reviewVaultWord,
    analyzePronunciation,
    fetchConversation,
    sendConversationMessage,
    clearConversation,
  }
})
