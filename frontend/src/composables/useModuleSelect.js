import { computed, watch } from 'vue'
import { useProjectStore } from '@/stores/project'

export function useModuleSelect() {
  const projectStore = useProjectStore()

  const modules = computed(() => projectStore.modules)

  async function loadModules(projectId) {
    if (!projectId) return []
    if (projectStore.modulesProjectId === projectId && projectStore.modules.length) {
      return projectStore.modules
    }
    return projectStore.fetchModules(projectId)
  }

  watch(
    () => projectStore.currentProjectId,
    (id) => {
      if (id) loadModules(id)
    },
    { immediate: true },
  )

  return { modules, loadModules }
}
