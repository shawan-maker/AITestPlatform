<template>
  <el-drawer :model-value="modelValue" :title="t('page.apiCases.execRecords.title')" direction="rtl" size="50%" :destroy-on-close="false" @update:model-value="$emit('update:modelValue', $event)">
    <!-- 列表视图 -->
    <div v-if="!selectedRecord">
      <el-table :data="records" v-loading="loading" size="small" stripe style="width: 100%" :empty-text="t('page.apiCases.execRecords.empty')">
        <el-table-column label="#" width="50" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column :label="t('page.apiCases.execRecords.colInterfaceCase')" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="nameMode === 'interface'">{{ row.interface_name || '-' }}</template>
            <template v-else-if="nameMode === 'case'">{{ row.case_name || '-' }}</template>
            <template v-else>
              <span v-if="row.interface_name">{{ row.interface_name }}</span>
              <span v-if="row.interface_name && row.case_name"> / </span>
              <span v-if="row.case_name">{{ row.case_name }}</span>
              <span v-if="!row.interface_name && !row.case_name">-</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="triggered_by_username" :label="t('page.apiCases.execRecords.colExecutor')" width="100">
          <template #default="{ row }">{{ row.triggered_by_username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('page.apiCases.execRecords.colExecTime')" min-width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="status" :label="t('page.apiCases.execRecords.colResult')" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" :label="t('execution.duration')" width="150">
          <template #default="{ row }">{{ row.status === 'running' ? '-' : formatDuration(row.duration_ms, locale) }}</template>
        </el-table-column>
        <el-table-column :label="t('page.apiCases.execRecords.colActions')" width="80">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'running'" link type="primary" @click="viewRecord(row)">{{ t('page.apiCases.execRecords.view') }}</el-button>
            <span v-else class="running-text">{{ t('page.apiCases.execRecords.running') }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 详情视图 -->
    <div v-else class="drawer-detail-view">
      <div class="drawer-detail-header">
        <el-button link type="primary" @click="selectedRecord = null">{{ t('page.apiCases.execRecords.backToList') }}</el-button>
        <span class="drawer-detail-meta">
          <el-tag :type="statusTagType(selectedRecord.status)" size="small">{{ selectedRecord.status }}</el-tag>
          {{ formatTime(selectedRecord.created_at) }} &nbsp; {{ t('execution.duration') }}: {{ formatDuration(selectedRecord.duration_ms, locale) }}
          <template v-if="selectedRecord.triggered_by_username"> &nbsp; {{ t('page.apiCases.execRecords.operator') }}: {{ selectedRecord.triggered_by_username }}</template>
        </span>
      </div>
      <ApiResponsePanel
        :result="detailExecResult"
        :response-headers="detailResponseHeaders"
        :request-headers="detailRequestHeaders"
        :extract-info="detailExtractInfo"
        :assert-info="detailAssertInfo"
        :log-data="detailLogData"
        :show-records="false"
      />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ApiResponsePanel from './ApiResponsePanel.vue'
import { formatDuration } from '@/utils/format'

const { t, locale } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  records: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  nameMode: { type: String, default: 'both' },  // 'both' | 'interface' | 'case'
})

defineEmits(['update:modelValue'])

const selectedRecord = ref(null)
const detailExecResult = ref(null)
const detailResponseHeaders = ref({})
const detailRequestHeaders = ref({})
const detailExtractInfo = ref([])
const detailAssertInfo = ref([])
const detailLogData = ref([])

function statusTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'fail') return 'warning'
  if (status === 'running') return 'info'
  return 'danger'
}

function statusLabel(status) {
  if (status === 'running') return t('page.apiCases.execRecords.statusRunning')
  if (status === 'success') return t('page.apiCases.execRecords.statusSuccess')
  if (status === 'fail') return t('page.apiCases.execRecords.statusFailed')
  if (status === 'error') return t('page.apiCases.execRecords.statusError')
  return status
}

function formatTime(val) {
  if (!val) return '-'
  var d = new Date(val)
  if (isNaN(d.getTime())) return val
  var pad = function (n) { return n < 10 ? '0' + n : '' + n }
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds())
}

function viewRecord(row) {
  selectedRecord.value = row
  if (row.api_requests_info) {
    var data = row.api_requests_info
    var detail = data._debug_detail || data
    var ri = detail.response_info || data.response_info || {}
    var reqInfo = detail.request_info || data.request_info || {}

    detailExecResult.value = {
      success: row.status === 'success',
      status_code: ri.status_code || data.response_code || '',
      duration_ms: row.duration_ms || ri.elapsed_ms || 0,
      method: reqInfo.method || data.method || '',
      url: reqInfo.url || data.url || '',
      error_message: row.error_message || '',
      response_body: ri.body || data.response_body || null,
      request_body: reqInfo.body || data.request_body || null,
    }
    detailResponseHeaders.value = ri.headers || data.response_headers || {}
    detailRequestHeaders.value = reqInfo.headers || data.request_headers || {}
    detailExtractInfo.value = detail.extract_info || data.extract_info || []
    detailAssertInfo.value = (detail.assert_info || data.assert_info || []).map(function (a) {
      return {
        field: a.field || a.target || '',
        method: a.type || a.method || 'eq',
        expected: a.expected !== undefined ? String(a.expected) : '',
        actual: a.actual !== undefined ? String(a.actual) : '',
        passed: a.passed !== undefined ? a.passed : true,
      }
    })
    var logRaw = detail.log_data || data.log_data || []
    detailLogData.value = logRaw.map(function (item) {
      if (Array.isArray(item)) return { level: item[0] || 'INFO', message: item.slice(1).join(' ') }
      return { level: item.level || 'INFO', message: item.message || String(item) }
    })
  } else {
    detailExecResult.value = null
    detailResponseHeaders.value = {}
    detailRequestHeaders.value = {}
    detailExtractInfo.value = []
    detailAssertInfo.value = []
    detailLogData.value = []
  }
}
</script>

<style scoped lang="scss">
.drawer-detail-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 12px;

  .drawer-detail-meta {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.running-text {
  font-size: 12px;
  color: var(--el-color-info);
}
</style>
