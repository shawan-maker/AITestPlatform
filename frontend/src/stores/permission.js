import { defineStore } from 'pinia'
import { PROJECT_ROLE } from '@/utils/constants'
import { getProject } from '@/api/projects'

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    role: null,
    roleLabel: null,
  }),

  getters: {
    canEdit(state) {
      return state.role === PROJECT_ROLE.EDITOR || state.role === PROJECT_ROLE.OWNER
    },
    canView() {
      return true
    },
    isOwner(state) {
      return state.role === PROJECT_ROLE.OWNER
    },
  },

  actions: {
    async loadRoleForProject(projectId) {
      if (!projectId) {
        this.role = null
        this.roleLabel = null
        return
      }
      try {
        const res = await getProject(projectId)
        const detail = res.data.data
        this.role = detail.my_role ?? null
        this.roleLabel = detail.my_role_label ?? null
      } catch {
        this.role = null
        this.roleLabel = null
      }
    },

    clear() {
      this.role = null
      this.roleLabel = null
    },
  },
})
