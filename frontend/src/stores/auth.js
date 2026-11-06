import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('abvos_user') || 'null'))
  const token = ref(localStorage.getItem('abvos_token') || null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAgentEnabled = computed(() => user.value?.agent_enabled ?? true)

  async function login(email, password, remember = false) {
    loading.value = true
    try {
      const response = await api.post('/auth/login', {
        email,
        password,
        remember,
        device_name: 'webapp',
      })

      const authToken = response.data.token
      const authUser = response.data.user?.data || response.data.user

      token.value = authToken
      user.value = authUser

      localStorage.setItem('abvos_token', authToken)
      localStorage.setItem('abvos_user', JSON.stringify(authUser))

      return authUser
    } finally {
      loading.value = false
    }
  }

  async function register(payload) {
    loading.value = true
    try {
      const response = await api.post('/auth/register', {
        ...payload,
        device_name: 'webapp',
      })

      const authToken = response.data.token
      const authUser = response.data.user?.data || response.data.user

      token.value = authToken
      user.value = authUser

      localStorage.setItem('abvos_token', authToken)
      localStorage.setItem('abvos_user', JSON.stringify(authUser))

      return authUser
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return null
    try {
      const response = await api.get('/auth/me')
      user.value = response.data.data
      localStorage.setItem('abvos_user', JSON.stringify(user.value))
      return user.value
    } catch {
      logout()
      return null
    }
  }

  async function toggleAgentKillSwitch() {
    if (!user.value) return
    const newState = !user.value.agent_enabled
    const response = await api.put('/auth/profile', {
      agent_enabled: newState,
    })
    user.value = response.data.data
    localStorage.setItem('abvos_user', JSON.stringify(user.value))
    return user.value
  }

  async function updateProfile(data) {
    const response = await api.put('/auth/profile', data)
    user.value = response.data.data
    localStorage.setItem('abvos_user', JSON.stringify(user.value))
    return user.value
  }

  async function logout() {
    try {
      if (token.value) {
        await api.post('/auth/logout').catch(() => {})
      }
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('abvos_token')
      localStorage.removeItem('abvos_user')
    }
  }

  return {
    user,
    token,
    loading,
    isAuthenticated,
    isAgentEnabled,
    login,
    register,
    fetchUser,
    toggleAgentKillSwitch,
    updateProfile,
    logout,
  }
})

