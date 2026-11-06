import axios from 'axios'

// Cliente Axios com baseURL /api (atendido pelo Nginx)
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  },
  withCredentials: false, // Autenticação moderna 100% via Bearer Token (sem atrito de CSRF)
})

// Interceptor para injetar Bearer Token caso esteja salvo no localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('abvos_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para redirecionamento em caso de 401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('abvos_token')
      localStorage.removeItem('abvos_user')
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

