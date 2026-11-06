import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/services/api'

export const useApprovalStore = defineStore('approvals', () => {
  const pendingItems = ref([])
  const summary = ref({ pending: 0, revision: 0, total_awaiting: 0 })
  const loading = ref(false)

  async function fetchSummary() {
    try {
      const response = await api.get('/approvals/summary')
      summary.value = response.data.data
      return summary.value
    } catch {
      return summary.value
    }
  }

  async function fetchPending(params = {}) {
    loading.value = true
    try {
      const response = await api.get('/approvals', {
        params: { status: 'awaiting', ...params },
      })
      pendingItems.value = response.data.data
      await fetchSummary()
      return pendingItems.value
    } finally {
      loading.value = false
    }
  }

  async function approve(id, { scheduledFor = null, selectedHookIndex = null } = {}) {
    const payload = {}
    if (scheduledFor) payload.scheduled_for = scheduledFor
    if (selectedHookIndex !== null) payload.selected_hook_index = selectedHookIndex

    const response = await api.post(`/approvals/${id}/approve`, payload)
    const updated = response.data.data

    pendingItems.value = pendingItems.value.filter((item) => item.id !== id)
    await fetchSummary()
    return updated
  }

  async function requestRevision(id, feedbackOrOptions, maybeSection = 'all') {
    let feedback = ''
    let section = 'all'

    if (typeof feedbackOrOptions === 'object' && feedbackOrOptions !== null) {
      feedback = feedbackOrOptions.feedback
      section = feedbackOrOptions.section || 'all'
    } else {
      feedback = feedbackOrOptions
      section = maybeSection || 'all'
    }

    const response = await api.post(`/approvals/${id}/revision`, {
      feedback,
      section: section === 'all' ? null : section,
    })
    const updated = response.data.data

    // Atualiza o item na lista local
    const idx = pendingItems.value.findIndex((item) => item.id === id)
    if (idx !== -1) {
      pendingItems.value[idx] = updated
    }
    await fetchSummary()
    return updated
  }

  async function reject(id, reasonOrOptions = null, discardProduct = false) {
    let reason = null
    let discard = discardProduct

    if (typeof reasonOrOptions === 'object' && reasonOrOptions !== null) {
      reason = reasonOrOptions.reason || null
      discard = reasonOrOptions.discardProduct ?? discardProduct
    } else {
      reason = reasonOrOptions
    }

    const response = await api.post(`/approvals/${id}/reject`, {
      reason,
      discard_product: discard,
    })
    const updated = response.data.data

    pendingItems.value = pendingItems.value.filter((item) => item.id !== id)
    await fetchSummary()
    return updated
  }

  return {
    pendingItems,
    summary,
    loading,
    fetchSummary,
    fetchPending,
    approve,
    requestRevision,
    reject,
  }
})

