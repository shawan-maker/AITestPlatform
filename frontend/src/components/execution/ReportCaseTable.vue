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
    <el-table
      :data="cases"
      border
      @selection-change="onSelectionChange"
    >
      <el-table-column v-if="canEdit" type="selection" width="48" />
      <el-table-column prop="case_name" :label="t('page.functional.caseName')" min-width="160" />
      <el-table-column prop="status" :label="t('common.status')" width="100">
        <template #default="{ row }">
          <StatusTag :status="row.status" :map="CASE_RESULT_MAP" />
        </template>
      </el-table-column>
      <el-table-column prop="duration_ms" :label="t('execution.duration')" width="100">
        <template #default="{ row }">{{ row.duration_ms != null ? `${row.duration_ms}ms` : '—' }}</template>
      </el-table-column>
      <el-table-column prop="defect_id" :label="t('page.defects.title')" width="100">
        <template #default="{ row }">{{ row.defect_id ?? '—' }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="$emit('view-log', row)">{{ t('execution.viewLog') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { batchLinkDefects } from '@/api/testExecution'
import { CASE_RESULT_MAP } from '@/utils/constants'
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
.report-case-table__toolbar {
  margin-bottom: 12px;
}
</style>
