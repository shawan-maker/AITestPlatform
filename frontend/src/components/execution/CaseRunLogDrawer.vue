<template>
  <el-drawer v-model="visible" :title="t('execution.viewLog')" size="60%" @open="loadLog">
    <div v-if="logData">
      <el-descriptions :column="2" border style="margin-bottom: 16px">
        <el-descriptions-item :label="t('execution.caseName')">{{ logData.case_name }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.duration')">{{ logData.duration_ms ? logData.duration_ms + ' ms' : '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.execResult')"><StatusTag :status="logData.status" :map="CASE_RESULT_MAP" /></el-descriptions-item>
      </el-descriptions>
      <ApiResponsePanel
        :result="panelResult"
        :response-headers="panelResponseHeaders"
        :request-headers="panelRequestHeaders"
        :extract-info="panelExtractInfo"
        :assert-info="panelAssertInfo"
        :log-data="panelLogData"
        :show-records="false"
      />
    </div>
    <el-empty v-else-if="!loading" :description="t('execution.noData')" />
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getCaseRunLog } from '@/api/testExecution'
import { CASE_RESULT_MAP } from '@/utils/constants'
import StatusTag from '@/components/common/StatusTag.vue'
import ApiResponsePanel from '@/components/api-test/ApiResponsePanel.vue'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseRunId: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const logData = ref(null)

// Transform api_requests_info into ApiResponsePanel format
const panelResult = computed(() => {
  if (!logData.value) return null
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  var ri = detail.response_info || data.response_info || {}
  var reqInfo = detail.request_info || data.request_info || {}
  return {
    success: logData.value.status === 'success',
    status_code: ri.status_code || data.response_code || '',
    duration_ms: logData.value.duration_ms || ri.elapsed_ms || 0,
    method: reqInfo.method || data.method || '',
    url: reqInfo.url || data.url || '',
    error_message: logData.value.error_message || '',
    response_body: ri.body || data.response_body || null,
    request_body: reqInfo.body || data.request_body || null,
  }
})

const panelResponseHeaders = computed(() => {
  if (!logData.value) return {}
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  var ri = detail.response_info || data.response_info || {}
  return ri.headers || data.response_headers || {}
})

const panelRequestHeaders = computed(() => {
  if (!logData.value) return {}
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  var reqInfo = detail.request_info || data.request_info || {}
  return reqInfo.headers || data.request_headers || {}
})

const panelExtractInfo = computed(() => {
  if (!logData.value) return []
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  return detail.extract_info || data.extract_info || []
})

const panelAssertInfo = computed(() => {
  if (!logData.value) return []
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  return (detail.assert_info || data.assert_info || []).map(function (a) {
    return {
      field: a.field || a.target || '',
      method: a.type || a.method || 'eq',
      expected: a.expected !== undefined ? String(a.expected) : '',
      actual: a.actual !== undefined ? String(a.actual) : '',
      passed: a.passed !== undefined ? a.passed : true,
    }
  })
})

const panelLogData = computed(() => {
  if (!logData.value) return []
  var data = logData.value.api_requests_info || {}
  var detail = data._debug_detail || data
  return detail.log_data || data.log_data || []
})

async function loadLog() {
  if (!props.caseRunId) return
  loading.value = true
  logData.value = null
  try {
    const res = await getCaseRunLog(props.caseRunId)
    logData.value = res.data.data
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>
