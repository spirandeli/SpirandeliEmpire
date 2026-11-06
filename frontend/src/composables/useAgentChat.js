import { ref } from 'vue'
import { api } from '@/services/api'

export function useAgentChat() {
  const conversation = ref(null)
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function loadOrCreateConversation(businessId = null, contextType = null) {
    loading.value = true
    error.value = null
    try {
      // Tenta recuperar a conversa mais recente desse contexto
      const params = { per_page: 1 }
      if (businessId) {
        params.business_id = businessId
      } else if (contextType) {
        params.context_type = contextType
      }

      const listRes = await api.get('/agent/conversations', { params })
      const existing = listRes.data.data?.[0]

      if (existing) {
        const detailRes = await api.get(`/agent/conversations/${existing.uuid}`)
        conversation.value = detailRes.data.data
        messages.value = detailRes.data.data.messages || []
        return conversation.value
      }

      // Cria uma nova conversa
      const createRes = await api.post('/agent/conversations', {
        business_id: businessId,
        context_type: contextType || (businessId ? 'business_chat' : 'incubator'),
      })
      conversation.value = createRes.data.data
      messages.value = []
      return conversation.value
    } catch (err) {
      error.value = err.response?.data?.message || 'Falha ao carregar conversa com o agente.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(text) {
    if (!conversation.value || !text.trim()) return

    const userText = text.trim()

    // Otimista: adiciona mensagem temporária do usuário no chat
    const tempUserMessage = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString(),
    }
    messages.value.push(tempUserMessage)

    loading.value = true
    error.value = null

    try {
      const response = await api.post(`/agent/conversations/${conversation.value.uuid}/messages`, {
        message: userText,
      })

      // Substitui / anexa as mensagens retornadas pelo backend (incluindo tool calls e resposta do modelo)
      const newMsgs = response.data.new_messages || []
      // Remove o temporário e adiciona as oficiais
      messages.value = messages.value.filter((m) => m.id !== tempUserMessage.id)
      messages.value.push(...newMsgs)

      if (response.data.conversation) {
        conversation.value = response.data.conversation
      }

      return response.data.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erro ao comunicar com o Gemini 3.8.'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    conversation,
    messages,
    loading,
    error,
    loadOrCreateConversation,
    sendMessage,
  }
}

