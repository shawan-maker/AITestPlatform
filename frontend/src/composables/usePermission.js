import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'

export function usePermission() {
  const permission = usePermissionStore()
  const auth = useAuthStore()
  const canEdit = computed(() => permission.canEdit || auth.isSuperAdmin)
  return {
    canEdit,
    canView: permission.canView,
    isOwner: computed(() => permission.isOwner || auth.isSuperAdmin),
    role: computed(() => permission.role),
    roleLabel: computed(() => permission.roleLabel),
  }
}
