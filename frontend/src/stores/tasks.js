import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/services/api'

export const useTaskStore = defineStore('tasks', () => {
  const boardColumns = ref([])
  const loading = ref(false)
  const agentLogs = ref([])
  const lastLogId = ref(0)
  const isPollingLogs = ref(false)
  let pollInterval = null

  const lastBoardParams = ref({})

  async function fetchBoard(params = {}, silent = false) {
    lastBoardParams.value = { ...params }
    if (!silent) loading.value = true
    try {
      const response = await api.get('/tasks/board', { params })
      boardColumns.value = response.data.data
      return boardColumns.value
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function createTask(payload) {
    loading.value = true
    try {
      const response = await api.post('/tasks', payload)
      const task = response.data.data
      // Insere na coluna correspondente do board
      const col = boardColumns.value.find((c) => c.status === task.status)
      if (col) {
        col.tasks.unshift(task)
        col.count++
      }
      return task
    } finally {
      loading.value = false
    }
  }

  async function moveTask(taskId, targetStatus, position = null) {
    // Atualização otimista
    let movedTask = null
    boardColumns.value.forEach((col) => {
      const idx = col.tasks.findIndex((t) => t.id === taskId)
      if (idx !== -1) {
        movedTask = col.tasks.splice(idx, 1)[0]
        col.count = Math.max(0, col.count - 1)
      }
    })

    if (movedTask) {
      movedTask.status = targetStatus
      const targetCol = boardColumns.value.find((c) => c.status === targetStatus)
      if (targetCol) {
        if (position !== null) {
          targetCol.tasks.splice(position, 0, movedTask)
        } else {
          targetCol.tasks.push(movedTask)
        }
        targetCol.count++
      }
    }

    try {
      const response = await api.patch(`/tasks/${taskId}/move`, {
        status: targetStatus,
        position,
      })
      return response.data.data
    } catch (err) {
      // Reverte em caso de erro
      await fetchBoard()
      throw err
    }
  }

  async function deleteTask(taskId) {
    loading.value = true
    try {
      await api.delete(`/tasks/${taskId}`)
      boardColumns.value.forEach((col) => {
        const idx = col.tasks.findIndex((t) => t.id === taskId)
        if (idx !== -1) {
          col.tasks.splice(idx, 1)
          col.count = Math.max(0, col.count - 1)
        }
      })
    } finally {
      loading.value = false
    }
  }

  // Polling incremental dos logs do agente
  async function pollLogs(businessId = null) {
    try {
      const params = { limit: 50 }
      if (lastLogId.value > 0) {
        params.after_id = lastLogId.value
      }
      if (businessId) {
        params.business_id = businessId
      }

      const response = await api.get('/agent/logs', { params })
      const newLogs = response.data.data || []

      const hasRunningTasks = boardColumns.value.some(
        (col) => col.status === 'in_progress_agent' && col.tasks && col.tasks.length > 0
      )

      if (newLogs.length > 0) {
        // Se for a primeira carga
        if (lastLogId.value === 0) {
          agentLogs.value = newLogs
        } else {
          agentLogs.value = [...agentLogs.value, ...newLogs]
          await fetchBoard(lastBoardParams.value, true)
        }
        lastLogId.value = response.data.meta?.last_id || Math.max(...newLogs.map((l) => l.id))
      } else if (hasRunningTasks) {
        await fetchBoard(lastBoardParams.value, true)
      }
    } catch {
      // Falha silenciosa no polling
    }
  }

  function startLogPolling(businessId = null, intervalMs = 3000) {
    if (pollInterval) return
    isPollingLogs.value = true
    pollLogs(businessId)
    pollInterval = setInterval(() => pollLogs(businessId), intervalMs)
  }

  function stopLogPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    isPollingLogs.value = false
  }

  return {
    boardColumns,
    loading,
    agentLogs,
    lastLogId,
    isPollingLogs,
    fetchBoard,
    createTask,
    moveTask,
    deleteTask,
    pollLogs,
    startLogPolling,
    stopLogPolling,
  }
})

