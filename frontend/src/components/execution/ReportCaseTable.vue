<template>
  <div class="report-case-table">
    <div class="report-case-table__toolbar">
      <el-input v-model="searchKey" :placeholder="t('execution.caseName') + ' / ' + t('execution.requestPath')" clearable style="width: 260px; margin-right: 8px" />
      <el-select v-model="statusFilter" :placeholder="t('execution.execResult')" clearable style="width: 120px; margin-right: 8px">
        <el-option v-for="(cfg, val) in FILTER_STATUS_MAP" :key="val" :label="cfg.label" :value="val" />
      </el-select>
      <el-button v-if="canEdit && selectedIds.length" type="primary" @click="showBatchLink = true">
        {{ t('execution.batchLink') }} ({{ selectedIds.length }})
      </el-button>
      <DefectBatchLinkDialog
        v-model="showBatchLink"
        :case-run-ids="selectedIds"
        :loading="linking"
        @submit="onBatchLink"
      />
    </div>
    <AppTable :data="filteredCases" @selection-change="onSelectionChange">
      <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="48" :selectable="isSelectable" />
      <AppTableColumn prop="case_id" variant="fixed" label="ID" :width="70" />
      <AppTableColumn prop="case_name" variant="content" :label="t('execution.caseName')" />
      <AppTableColumn variant="fixed" :label="t('execution.requestMethod')" :width="80">
        <template #default="{ row }">
          <el-tag v-if="row.interface_method" size="small">{{ row.interface_method }}</el-tag>
          <span v-else>-</span>
        </template>
      </AppTableColumn>
      <AppTableColumn prop="interface_path" variant="fixed" :label="t('execution.requestPath')" :width="200">
        <template #default="{ row }">{{ row.interface_path || '-' }}</template>
      </AppTableColumn>
      <AppTableColumn prop="duration_ms" variant="fixed" :label="t('execution.duration')" :width="100">
        <template #default="{ row }">{{ row.duration_ms != null ? (row.duration_ms < 1000 ? row.duration_ms + 'ms' : (row.duration_ms / 1000).toFixed(1) + 's') : '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('execution.startTime')" :width="170">
        <template #default="{ row }">{{ row.start_time ? formatTime(row.start_time) : '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('execution.execResult')" :width="100">
        <template #default="{ row }">
          <StatusTag :status="row.status" :map="caseResultMap" />
        </template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('execution.linkDefect')" :width="140">
        <template #default="{ row }">
          <template v-if="row.external_key">{{ row.external_key }}</template>
          <template v-else-if="row.defect_code">{{ row.defect_code }}</template>
          <template v-else-if="row.defect_id">#{{ row.defect_id }}</template>
          <span v-else>-</span>
        </template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('execution.viewLog'), t('execution.linkDefect')]">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="!row.id" @click="$emit('view-log', row)">{{ t('execution.viewLog') }}</el-button>
          <el-button v-if="canEdit && isFailed(row)" link type="danger" @click="$emit('create-defect', row)">{{ t('execution.linkDefect') }}</el-button>
        </template>
      </AppTableColumn>
    </AppTable>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { batchLinkDefects } from '@/api/testExecution'
import { getCaseResultMap } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import DefectBatchLinkDialog from './DefectBatchLinkDialog.vue'

const props = defineProps({
  cases: { type: Array, default: () => [] },
  suiteName: { type: String, default: '' },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['view-log', 'linked', 'create-defect'])

const { t } = useI18n()
const caseResultMap = computed(() => getCaseResultMap(t))

// Filter status options: success, fail, error, pending(not started)
const FILTER_STATUS_MAP = computed(() => ({
  success: caseResultMap.value.success,
  fail: caseResultMap.value.fail,
  error: caseResultMap.value.error,
  pending: { type: 'info', label: t('status.result.pending') },
}))
const selectedIds = ref([])
const showBatchLink = ref(false)
const linking = ref(false)
const searchKey = ref('')
const statusFilter = ref('')

const filteredCases = computed(function () {
  var list = props.cases
  if (searchKey.value) {
    var kw = searchKey.value.toLowerCase()
    list = list.filter(function (c) {
      return (c.case_name || '').toLowerCase().includes(kw) ||
        (c.interface_path || '').toLowerCase().includes(kw)
    })
  }
  if (statusFilter.value) {
    list = list.filter(function (c) { return c.status === statusFilter.value })
  }
  return list
})

function isFailed(row) {
  return row.status === 'fail' || row.status === 'failed' || row.status === 'error'
}

function isSelectable(row) {
  return isFailed(row) && row.id
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id }).filter(Boolean)
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
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
</style>
