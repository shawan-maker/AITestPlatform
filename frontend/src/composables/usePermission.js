import { usePermissionStore } from '@/stores/permission'

export function usePermission() {
  const permission = usePermissionStore()
  return {
    canEdit: permission.canEdit,
    canView: permission.canView,
    isOwner: permission.isOwner,
    role: permission.role,
    roleLabel: permission.roleLabel,
  }
}
