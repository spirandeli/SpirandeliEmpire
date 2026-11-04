import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import JeffreyChatView from '../views/JeffreyChatView.vue'
import BusinessesView from '../views/BusinessesView.vue'
import BusinessFactoryView from '../views/BusinessFactoryView.vue'
import ProjectsView from '../views/ProjectsView.vue'
import AiEngineView from '../views/AiEngineView.vue'
import FinancialView from '../views/FinancialView.vue'
import VpsAdminView from '../views/VpsAdminView.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: DashboardView },
  { path: '/jeffrey', name: 'Jeffrey', component: JeffreyChatView },
  { path: '/businesses', name: 'Businesses', component: BusinessesView },
  { path: '/factory', name: 'BusinessFactory', component: BusinessFactoryView },
  { path: '/projects', name: 'Projects', component: ProjectsView },
  { path: '/ai-engine', name: 'AiEngine', component: AiEngineView },
  { path: '/financial', name: 'Financial', component: FinancialView },
  { path: '/analytics', name: 'Analytics', component: FinancialView },
  { path: '/vps', name: 'VpsAdmin', component: VpsAdminView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
