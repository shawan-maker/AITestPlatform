<template>
  <div class="member-panel">
    <div class="member-panel__toolbar">
      <el-button v-if="canEdit" type="primary" @click="showAdd = true">{{ t('page.projectSettings.addMember') }}</el-button>
    </div>
    <el-table v-loading="loading" :data="members" border>
      <el-table-column prop="username" :label="t('page.login.username')" />
      <el-table-column prop="email" :label="t('page.register.email')" />
      <el-table-column :label="t('page.projectSettings.role')" width="160">
        <template #default="{ row }">
          <MemberRoleSelect
            v-if="canEdit && row.role !== PROJECT_ROLE.OWNER"
            :model-value="row.role"
            @update:model-value="(v) => $emit('update-role', row, v)"
          />
          <el-tag v-else type="warning">{{ t('role.owner') }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="canEdit" :label="t('common.actions')" width="100">
        <template #default="{ row }">
          <ConfirmDelete v-if="row.role !== PROJECT_ROLE.OWNER" @confirm="$emit('remove', row)">
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" :title="t('page.projectSettings.addMember')" width="480px">
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
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { PROJECT_ROLE } from '@/utils/constants'
import MemberRoleSelect from './MemberRoleSelect.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

defineProps({
  members: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['add', 'update-role', 'remove'])
const { t } = useI18n()
const showAdd = ref(false)
const addForm = reactive({ user_id: null, role: PROJECT_ROLE.VIEWER })

function submitAdd() {
  emit('add', { ...addForm })
  showAdd.value = false
  addForm.user_id = null
  addForm.role = PROJECT_ROLE.VIEWER
}
</script>

<style scoped lang="scss">
.member-panel__toolbar {
  margin-bottom: 12px;
}
</style>
