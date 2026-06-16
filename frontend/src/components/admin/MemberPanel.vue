<template>
  <div class="member-panel">
    <div class="member-panel__toolbar">
      <el-button v-if="canEdit" type="primary" @click="showAdd = true">{{ t('page.projectSettings.addMember') }}</el-button>
      <el-button
        v-if="canEdit"
        type="primary"
        :disabled="!hasPending"
        :loading="saving"
        @click="saveRoles"
      >
        {{ t('page.projectSettings.membersSave') }}
      </el-button>
    </div>
    <AppTable :data="members" :loading="loading">
      <AppTableColumn prop="username" variant="content" :label="t('page.login.username')" />
      <AppTableColumn prop="email" variant="content" :label="t('page.register.email')" />
      <AppTableColumn variant="fixed" :label="t('page.projectSettings.role')" :width="200">
        <template #default="{ row }">
          <el-tag v-if="row.is_super_admin" type="danger">{{ t('role.superAdminInProject') }}</el-tag>
          <MemberRoleSelect
            v-else-if="canEdit && row.role !== PROJECT_ROLE.OWNER"
            :model-value="displayRole(row)"
            :allow-admin="allowAdmin"
            @update:model-value="(v) => setPendingRole(row, v)"
          />
          <el-tag v-else-if="row.role === PROJECT_ROLE.OWNER" type="warning">{{ t('role.admin') }}</el-tag>
          <span v-else>{{ t(`role.${PROJECT_ROLE_LABEL[row.role] || 'viewer'}`) }}</span>
        </template>
      </AppTableColumn>
      <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="120">
        <template #default="{ row }">
          <ConfirmDelete
            v-if="!row.is_super_admin && row.role !== PROJECT_ROLE.OWNER"
            @confirm="$emit('remove', row)"
          >
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </AppTableColumn>
    </AppTable>

    <el-dialog :close-on-click-modal="false" v-model="showAdd" :title="t('page.projectSettings.addMember')" width="480px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.login.username')">
          <UserSearchPicker v-model="addForm.user_id" />
        </el-form-item>
        <el-form-item :label="t('page.projectSettings.role')">
          <MemberRoleSelect v-model="addForm.role" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitAdd">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { PROJECT_ROLE, PROJECT_ROLE_LABEL } from '@/utils/constants'
import MemberRoleSelect from './MemberRoleSelect.vue'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

const props = defineProps({
  members: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: true },
  allowAdmin: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['add', 'remove', 'save-roles'])
const { t } = useI18n()
const showAdd = ref(false)
const addForm = reactive({ user_id: null, role: PROJECT_ROLE.VIEWER })
const pendingRoles = ref({})

watch(
  () => props.members,
  () => {
    pendingRoles.value = {}
  },
  { deep: true },
)

const hasPending = computed(() => Object.keys(pendingRoles.value).length > 0)

function memberKey(row) {
  return row.user_id ?? row.id
}

function displayRole(row) {
  const key = memberKey(row)
  if (pendingRoles.value[key] !== undefined) {
    return pendingRoles.value[key]
  }
  return row.role
}

function setPendingRole(row, role) {
  const key = memberKey(row)
  if (role === row.role) {
    const next = { ...pendingRoles.value }
    delete next[key]
    pendingRoles.value = next
  } else {
    pendingRoles.value = { ...pendingRoles.value, [key]: role }
  }
}

function saveRoles() {
  const changes = Object.entries(pendingRoles.value).map(([userId, role]) => ({
    user_id: Number(userId),
    role,
  }))
  if (changes.length) {
    emit('save-roles', changes)
  }
}

function clearPending() {
  pendingRoles.value = {}
}

function submitAdd() {
  emit('add', { ...addForm })
  showAdd.value = false
  addForm.user_id = null
  addForm.role = PROJECT_ROLE.VIEWER
}

defineExpose({ hasPending, clearPending })
</script>

<style scoped lang="scss">
.member-panel__toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
</style>
