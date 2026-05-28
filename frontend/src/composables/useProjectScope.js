import { computed } from 'vue'
import { useProjectStore } from '@/stores/project'

export function useProjectScope() {
  const projectStore = useProjectStore()

  const projectId = computed(() => projectStore.currentProjectId)

  function requireProjectId() {
    if (!projectId.value) return null
    return projectId.value
  }

  function withProjectParams(params = {}) {
    if (!projectId.value) return null
    return { project_id: projectId.value, ...params }
  }

  return { projectId, requireProjectId, withProjectParams }
}
