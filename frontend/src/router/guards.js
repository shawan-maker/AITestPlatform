import { getAccessToken } from '@/utils/auth'
import { getProject } from '@/api/projects'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { usePermissionStore } from '@/stores/permission'
import i18n from '@/i18n'

const PUBLIC_PATHS = ['/login', '/register', '/403']

export function setupRouterGuards(router) {
  router.beforeEach(async (to, from, next) => {
    const auth = useAuthStore()
    const projectStore = useProjectStore()
    const permissionStore = usePermissionStore()
    const { t } = i18n.global

    if (!auth.initialized) {
      await auth.restoreSession()
    }

    const requiresAuth = to.meta.requiresAuth !== false
    const hasToken = !!getAccessToken()

    if (requiresAuth && !hasToken && !PUBLIC_PATHS.includes(to.path)) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }

    if ((to.path === '/login' || to.path === '/register') && auth.isLoggedIn) {
      return next('/agent')
    }

    if (requiresAuth && auth.isLoggedIn) {
      if (projectStore.projects.length === 0 && !projectStore.loading) {
        await projectStore.fetchProjects()
      }

      if (to.meta.superAdminOnly && !auth.isSuperAdmin) {
        return next('/403')
      }

      if (to.meta.projectMemberRequired) {
        const projectId = Number(to.params.id)
        if (!projectId) {
          return next('/403')
        }
        if (!auth.isSuperAdmin) {
          try {
            await getProject(projectId)
          } catch {
            return next('/403')
          }
        }
      }

      if (projectStore.currentProjectId) {
        await permissionStore.loadRoleForProject(projectStore.currentProjectId)
      }
    }

    if (to.meta.titleKey) {
      document.title = `${t(to.meta.titleKey)} - ${t('common.appName')}`
    }

    next()
  })
}
