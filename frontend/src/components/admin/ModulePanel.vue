<template>
  <div class="module-panel">
    <div class="module-panel__toolbar">
      <el-button v-if="canEdit" type="primary" @click="openCreate">{{ t('page.projectSettings.addModule') }}</el-button>
    </div>
    <AppTable :data="modules" :loading="loading">
      <AppTableColumn prop="name" variant="content" :label="t('page.projectSettings.moduleName')" />
      <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </AppTableColumn>
      <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :button-labels="[t('common.edit'), t('common.delete')]">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <ConfirmDelete @confirm="$emit('delete', row)">
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </AppTableColumn>
    </AppTable>

    <el-dialog :close-on-click-modal="false" v-model="dialogVisible" :title="editRow ? t('common.edit') : t('page.projectSettings.addModule')" width="400px">
      <el-form label-width="auto">
        <el-form-item :label="t('page.projectSettings.moduleName')">
          <el-input v-model="formName" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'

defineProps({
  modules: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['create', 'update', 'delete'])
const { t } = useI18n()

const dialogVisible = ref(false)
const editRow = ref(null)
const formName = ref('')

function openCreate() {
  editRow.value = null
  formName.value = ''
  dialogVisible.value = true
}

function openEdit(row) {
  editRow.value = row
  formName.value = row.name
  dialogVisible.value = true
}

function submit() {
  if (editRow.value) {
    emit('update', editRow.value, { name: formName.value })
  } else {
    emit('create', { name: formName.value })
  }
  dialogVisible.value = false
}
</script>

<style scoped lang="scss">
.module-panel__toolbar {
  margin-bottom: 12px;
}
</style>
