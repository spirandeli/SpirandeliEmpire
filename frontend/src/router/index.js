import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/businesses',
    name: 'businesses.index',
    component: () => import('@/views/BusinessesIndexView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/businesses/:id',
    name: 'businesses.detail',
    component: () => import('@/views/BusinessDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks',
    name: 'tasks.board',
    component: () => import('@/views/TasksBoardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/storage-viewer',
    name: 'storage.viewer',
    component: () => import('@/views/StorageViewerView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/languages',
    name: 'languages.academy',
    component: () => import('@/views/LanguageAcademyView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/calendar/demo',
    name: 'calendar.demo',
    component: () => import('@/views/CalendarIntegrationDemoView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/integrations',
    name: 'settings.integrations',
    component: () => import('@/views/SettingsIntegrationsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin/ai-governance',
    name: 'admin.ai-governance',
    component: () => import('@/views/AdminAiGovernanceView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return next({ name: 'dashboard' })
  }

  if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    return next({ name: 'dashboard' })
  }

  next()
})

export default router

