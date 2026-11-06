import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/services/api'

export const useBusinessStore = defineStore('business', () => {
  const businesses = ref([])
  const currentBusiness = ref(null)
  const loading = ref(false)
  const pagination = ref({ page: 1, lastPage: 1, total: 0 })

  async function fetchBusinesses(params = {}) {
    loading.value = true
    try {
      const response = await api.get('/businesses', { params })
      businesses.value = response.data.data
      pagination.value = {
        page: response.data.meta?.current_page || 1,
        lastPage: response.data.meta?.last_page || 1,
        total: response.data.meta?.total || businesses.value.length,
      }
      return businesses.value
    } finally {
      loading.value = false
    }
  }

  async function fetchBusiness(id) {
    loading.value = true
    try {
      const response = await api.get(`/businesses/${id}`)
      currentBusiness.value = response.data.data
      return currentBusiness.value
    } finally {
      loading.value = false
    }
  }

  async function createBusiness(payload) {
    const response = await api.post('/businesses', payload)
    const created = response.data.data
    businesses.value.unshift(created)
    return created
  }

  async function updateBusiness(id, payload) {
    const response = await api.put(`/businesses/${id}`, payload)
    const updated = response.data.data
    if (currentBusiness.value?.id === id) {
      currentBusiness.value = updated
    }
    const idx = businesses.value.findIndex((b) => b.id === id)
    if (idx !== -1) {
      businesses.value[idx] = updated
    }
    return updated
  }

  async function activateBusiness(id) {
    const response = await api.post(`/businesses/${id}/activate`)
    const updated = response.data.data
    if (currentBusiness.value?.id === id) {
      currentBusiness.value = updated
    }
    const idx = businesses.value.findIndex((b) => b.id === id)
    if (idx !== -1) {
      businesses.value[idx] = updated
    }
    return updated
  }

  async function pauseBusiness(id) {
    const response = await api.post(`/businesses/${id}/pause`)
    const updated = response.data.data
    if (currentBusiness.value?.id === id) {
      currentBusiness.value = updated
    }
    const idx = businesses.value.findIndex((b) => b.id === id)
    if (idx !== -1) {
      businesses.value[idx] = updated
    }
    return updated
  }

  async function deleteBusiness(id) {
    await api.delete(`/businesses/${id}`)
    businesses.value = businesses.value.filter((b) => b.id !== id)
    if (currentBusiness.value?.id === id) {
      currentBusiness.value = null
    }
  }

  return {
    businesses,
    currentBusiness,
    loading,
    pagination,
    fetchBusinesses,
    fetchBusiness,
    createBusiness,
    updateBusiness,
    activateBusiness,
    pauseBusiness,
    deleteBusiness,
  }
})

