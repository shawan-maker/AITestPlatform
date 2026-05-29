<template>
  <div class="report-case-table">
    <div v-if="canEdit && selectedIds.length" class="report-case-table__toolbar">
      <el-button type="primary" @click="showBatchLink = true">
        {{ t('execution.batchLink') }} ({{ selectedIds.length }})
      </el-button>
      <DefectBatchLinkDialog
        v-model="showBatchLink"
        :case-run-ids="selectedIds"
        :loading="linking"
        @submit="onBatchLink"
      />
    </div>
    <AppTable :data="cases" @selection-change="onSelectionChange">
      <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="48" />
      <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" />
      <AppTableColumn variant="fixed" :label="t('common.status')" :width="120">
        <template #default="{ row }">
          <StatusTag :status="row.status" :map="CASE_RESULT_MAP" />
        </template>
      </AppTableColumn>
      <AppTableColumn prop="duration_ms" variant="fixed" :label="t('execution.duration')" :width="120">
        <template #default="{ row }">{{ row.duration_ms != null ? `${row.duration_ms}ms` : '—' }}</template>
      </AppTableColumn>
      <AppTableColumn prop="defect_id" variant="fixed" :label="t('page.defects.title')" :width="120">
        <template #default="{ row }">{{ row.defect_id ?? '—' }}</template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click="$emit('view-log', row)">{{ t('execution.viewLog') }}</el-button>
        </template>
      </AppTableColumn>
    </AppTable>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { batchLinkDefects } from '@/api/testExecution'
import { CASE_RESULT_MAP } from '@/utils/constants'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import DefectBatchLinkDialog from './DefectBatchLinkDialog.vue'

defineProps({
  cases: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['view-log', 'linked'])

const { t } = useI18n()
const selectedIds = ref([])
const showBatchLink = ref(false)
const linking = ref(false)

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

async function onBatchLink(payload) {
  linking.value = true
  try {
    await batchLinkDefects(payload)
    ElMessage.success(t('execution.batchLinkOk'))
    showBatchLink.value = false
    selectedIds.value = []
    emit('linked')
  } finally {
    linking.value = false
  }
}
</script>

<style scoped lang="scss">
.report-case-table {
  width: 100%;
}

.report-case-table__toolbar {
  margin-bottom: 12px;
}
</style>
