<template>
  <el-drawer v-model="visible" :title="t('execution.viewLog')" size="60%" @open="loadLog">
    <div v-if="logData">
      <el-descriptions :column="2" border style="margin-bottom: 16px">
        <el-descriptions-item :label="t('execution.caseName')">{{ logData.case_name }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.duration')">{{ logData.duration_ms ? logData.duration_ms + ' ms' : '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.result')"><StatusTag :status="logData.status" :map="CASE_RESULT_MAP" /></el-descriptions-item>
        <el-descriptions-item :label="t('execution.startTime')">{{ formatTime(logData.start_time) }}</el-descriptions-item>
      </el-descriptions>
      <el-tabs>
        <el-tab-pane :label="t('execution.requestInfo')">
          <template v-if="logData.snapshot">
            <el-descriptions :column="1" border>
              <el-descriptions-item :label="t('execution.requestMethod')">{{ logData.snapshot.method || logData.snapshot.interface?.method || '-' }}</el-descriptions-item>
              <el-descriptions-item :label="t('execution.requestUrl')">{{ logData.snapshot.url || logData.snapshot.interface?.url || '-' }}</el-descriptions-item>
              <el-descriptions-item label="Headers"><pre class="code-block">{{ JSON.stringify(logData.snapshot.headers || {}, null, 2) }}</pre></el-descriptions-item>
              <el-descriptions-item :label="t('execution.requestBody')"><pre class="code-block">{{ formatJson(logData.snapshot.request?.data || logData.snapshot.request?.json) }}</pre></el-descriptions-item>
            </el-descriptions>
            <div v-if="logData.snapshot.assertions?.length" style="margin-top: 12px">
              <h4>{{ t('execution.assertions') }}</h4>
              <el-table :data="logData.snapshot.assertions" size="small" border>
                <el-table-column prop="field" :label="t('execution.assertField')" />
                <el-table-column prop="type" :label="t('execution.assertCompareMethod')" width="100" />
                <el-table-column prop="expected" :label="t('execution.assertExpected')" />
              </el-table>
            </div>
            <div v-if="logData.snapshot.extract?.length" style="margin-top: 12px">
              <h4>{{ t('execution.extract') }}</h4>
              <el-table :data="logData.snapshot.extract" size="small" border>
                <el-table-column prop="var_name" :label="t('execution.extractVarName')" />
                <el-table-column prop="extract_expr" :label="t('execution.extractExpr')" />
              </el-table>
            </div>
          </template>
          <el-empty v-else :description="t('execution.noSnapshot')" />
        </el-tab-pane>
        <el-tab-pane :label="t('execution.responseInfo')">
          <div v-if="responseBody" style="margin-bottom: 12px">
            <h4>{{ t('execution.responseBody') }}</h4>
            <pre class="code-block" style="max-height: 300px; overflow: auto">{{ responseBody }}</pre>
          </div>
          <div v-if="responseHeaders" style="margin-bottom: 12px">
            <h4>{{ t('execution.responseHeaders') }}</h4>
            <pre class="code-block">{{ responseHeaders }}</pre>
          </div>
          <div v-if="logLines.length" style="margin-top: 12px">
            <h4>{{ t('execution.runLog') }}</h4>
            <div class="log-viewer">
              <div v-for="(line, i) in logLines" :key="i">
                <span :style="{ color: lineColor(line) }">{{ formatLine(line) }}</span>
              </div>
            </div>
          </div>
          <div v-if="logData.error_message" style="margin-top: 12px">
            <h4>{{ t('execution.errorMessage') }}</h4>
            <el-alert type="error" :description="logData.error_message" show-icon :closable="false" />
          </div>
        </el-tab-pane>
      </el-tabs>
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
import { formatTime, formatResponseBody } from '@/utils/format'
import StatusTag from '@/components/common/StatusTag.vue'

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

const responseBody = computed(() => {
  var body = logData.value?.api_requests_info?.response_info?.body
  return body ? formatResponseBody(body) : ''
})

const responseHeaders = computed(() => {
  var h = logData.value?.api_requests_info?.response_info?.headers
  return h ? JSON.stringify(h, null, 2) : ''
})

const logLines = computed(() => {
  if (!logData.value) return []
  return logData.value.api_requests_info?._debug_detail?.log_data
    || logData.value.api_requests_info?.log_data
    || []
})

function formatJson(val) {
  if (val == null) return '-'
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return String(val)
}

function lineColor(line) {
  var level = Array.isArray(line) ? line[0] : ''
  if (level === 'ERROR') return '#f56c6c'
  if (level === 'WARNING') return '#e6a23c'
  return '#d4d4d4'
}

function formatLine(line) {
  return Array.isArray(line) ? line.join(' ') : String(line)
}

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

<style scoped>
.code-block {
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  margin: 0;
  font-size: 13px;
}
.log-viewer {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
  font-family: monospace;
  font-size: 13px;
}
</style>
