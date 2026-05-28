import { defineStore } from 'pinia'
import { listProjects, listModules as fetchModulesApi } from '@/api/projects'
import { getCurrentProjectId, setCurrentProjectId } from '@/utils/auth'

export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProjectId: getCurrentProjectId(),
    modules: [],
    modulesProjectId: null,
    loading: false,
  }),

  getters: {
    currentProject(state) {
      return state.projects.find((p) => p.id === state.currentProjectId) ?? null
    },
  },

  actions: {
    async fetchProjects(params) {
      this.loading = true
      try {
        const res = await listProjects(params)
        this.projects = res.data.data?.items ?? []
        if (this.projects.length && !this.currentProjectId) {
          this.setCurrent(this.projects[0].id)
        } else if (
          this.currentProjectId &&
          !this.projects.some((p) => p.id === this.currentProjectId)
        ) {
          this.setCurrent(this.projects[0]?.id ?? null)
        }
      } finally {
        this.loading = false
      }
    },

    async fetchModules(projectId) {
      if (!projectId) {
        this.modules = []
        this.modulesProjectId = null
        return []
      }
      const res = await fetchModulesApi(projectId)
      this.modules = res.data.data?.items ?? res.data.data ?? []
      this.modulesProjectId = projectId
      return this.modules
    },

    setCurrent(id) {
      this.currentProjectId = id ?? null
      setCurrentProjectId(id ?? null)
      if (id !== this.modulesProjectId) {
        this.modules = []
        this.modulesProjectId = null
      }
    },
  },
})
