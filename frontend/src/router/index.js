import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'
import ForbiddenView from '@/views/error/ForbiddenView.vue'
import NotFoundView from '@/views/error/NotFoundView.vue'
import { setupRouterGuards } from './guards'

import authRoutes from './routes/auth'
import agentRoutes from './routes/agent'
import casesRoutes from './routes/cases'
import testRoutes from './routes/test'
import docsRoutes from './routes/docs'
import envRoutes from './routes/env'
import adminRoutes from './routes/admin'
import projectRoutes from './routes/project'
import profileRoutes from './routes/profile'

const routes = [
  {
    path: '/',
    redirect: '/agent',
  },
  {
    path: '/',
    component: DefaultLayout,
    meta: { requiresAuth: true },
    children: [
      ...agentRoutes,
      ...casesRoutes,
      ...testRoutes,
      ...docsRoutes,
      ...envRoutes,
      ...projectRoutes,
      ...adminRoutes,
      ...profileRoutes,
    ],
  },
  {
    path: '/',
    component: AuthLayout,
    meta: { requiresAuth: false },
    children: authRoutes,
  },
  {
    path: '/403',
    component: BlankLayout,
    meta: { requiresAuth: false },
    children: [
      {
        path: '',
        name: 'Forbidden',
        component: ForbiddenView,
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    component: BlankLayout,
    meta: { requiresAuth: false },
    children: [
      {
        path: '',
        name: 'NotFound',
        component: NotFoundView,
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

setupRouterGuards(router)

export default router
