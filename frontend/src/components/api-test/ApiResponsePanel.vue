<template>
  <div class="api-response-panel">
    <div class="response-toolbar">
      <el-tabs v-model="activeTab" class="response-sub-tabs">
        <el-tab-pane name="result">
          <template #label>
            <span>{{ t('page.apiCases.resultInfo') }}</span>
            <el-tag v-if="result && result.status_code" :type="result.success ? 'success' : 'danger'" size="small" style="margin-left:4px;font-size:12px">{{ result.status_code }}</el-tag>
          </template>
        </el-tab-pane>
        <el-tab-pane :label="t('page.apiCases.responseInfo')" name="responseInfo" />
        <el-tab-pane :label="t('page.apiCases.requestInfo')" name="requestInfo" />
        <el-tab-pane :label="t('page.apiCases.response.tabHeaders')" name="requestHeaders" />
        <el-tab-pane :label="t('page.apiCases.extractInfo')" name="extractInfo" />
        <el-tab-pane :label="t('page.apiCases.assertInfo')" name="assertInfo" />
        <el-tab-pane :label="t('page.apiCases.response.tabLog')" name="logInfo" />
      </el-tabs>
      <el-button v-if="showRecords" link type="primary" :icon="Clock" @click="$emit('toggleRecords')">{{ t('page.apiCases.testRecord') }}</el-button>
    </div>

    <div class="response-body">
      <!-- 返回结果 -->
      <template v-if="activeTab === 'result'">
        <div v-if="result" class="run-result-block" :class="result.success ? 'success' : 'fail'">
          <el-icon :color="result.success ? '#67C23A' : '#F56C6C'">
            <CircleCheckFilled v-if="result.success" /><CircleCloseFilled v-else />
          </el-icon>
          <span class="result-label">{{ result.success ? t('common.success') : t('common.failed') }}</span>
          <el-tag v-if="result.status_code" :type="result.success ? 'success' : 'danger'" size="small" style="margin-left:8px">{{ result.status_code }}</el-tag>
          <span class="result-meta">{{ t('page.apiCases.response.duration') }}: {{ result.duration_ms || 0 }}ms</span>
        </div>
        <div v-if="result && result.error_message" class="error-message"><strong>{{ t('page.apiCases.response.errorMsg') }}:</strong> {{ result.error_message }}</div>
        <pre v-if="result && result.response_body" class="response-pre">{{ formatJson(result.response_body) }}</pre>
        <el-empty v-if="!result" :description="t('page.apiCases.response.noExecResult')" :image-size="48" />
      </template>

      <!-- 响应头 -->
      <template v-else-if="activeTab === 'responseInfo'">
        <table v-if="responseHeaders && Object.keys(responseHeaders).length" class="info-table">
          <thead><tr><th>Header</th><th>Value</th></tr></thead>
          <tbody><tr v-for="(v, k) in responseHeaders" :key="k"><td class="info-key">{{ k }}</td><td>{{ v }}</td></tr></tbody>
        </table>
        <el-empty v-else :description="t('page.apiCases.response.noHeaders')" :image-size="48" />
      </template>

      <!-- 请求数据 -->
      <template v-else-if="activeTab === 'requestInfo'">
        <div v-if="result" class="structured-response">
          <div class="info-row"><strong>{{ t('page.apiCases.response.requestMethod') }}:</strong> <el-tag size="small">{{ (result.method || 'GET').toUpperCase() }}</el-tag></div>
          <div class="info-row"><strong>{{ t('page.apiCases.response.requestUrl') }}:</strong> <code>{{ result.url || '-' }}</code></div>
          <template v-if="result.request_body">
            <div v-if="isFormData(result)" class="form-params-display">
              <strong>{{ t('page.apiCases.response.formDataParams') }}:</strong>
              <table class="info-table">
                <thead><tr><th>{{ t('page.apiCases.response.paramName') }}</th><th>{{ t('page.apiCases.response.paramValue') }}</th></tr></thead>
                <tbody><tr v-for="(v, k) in parseFormData(result.request_body)" :key="k"><td class="info-key">{{ k }}</td><td>{{ v }}</td></tr></tbody>
              </table>
            </div>
            <pre v-else class="response-pre">{{ formatJson(result.request_body) }}</pre>
          </template>
        </div>
        <el-empty v-else :description="t('page.apiCases.response.noRequestData')" :image-size="48" />
      </template>

      <!-- 请求头 -->
      <template v-else-if="activeTab === 'requestHeaders'">
        <table v-if="requestHeaders && Object.keys(requestHeaders).length" class="info-table">
          <thead><tr><th>Header</th><th>Value</th></tr></thead>
          <tbody><tr v-for="(v, k) in requestHeaders" :key="k"><td class="info-key">{{ k }}</td><td>{{ v }}</td></tr></tbody>
        </table>
        <el-empty v-else :description="t('page.apiCases.response.noRequestHeaders')" :image-size="48" />
      </template>

      <!-- 提取信息 -->
      <template v-else-if="activeTab === 'extractInfo'">
        <table v-if="extractInfo && extractInfo.length" class="info-table">
          <thead><tr><th>{{ t('page.apiCases.response.varName') }}</th><th>{{ t('page.apiCases.response.expression') }}</th><th>{{ t('page.apiCases.response.value') }}</th></tr></thead>
          <tbody>
            <tr v-for="(item, idx) in extractInfo" :key="idx">
              <td>{{ item.var_name || item.name }}</td>
              <td>{{ item.extract_expr || item.expression }}</td>
              <td>{{ item.value !== undefined ? item.value : '-' }}</td>
            </tr>
          </tbody>
        </table>
        <el-empty v-else :description="t('page.apiCases.response.noExtractData')" :image-size="48" />
      </template>

      <!-- 断言信息 -->
      <template v-else-if="activeTab === 'assertInfo'">
        <table v-if="assertInfo && assertInfo.length" class="info-table assert-table">
          <thead><tr><th style="width:40px">{{ t('page.apiCases.response.result') }}</th><th>{{ t('page.apiCases.response.assertTarget') }}</th><th>{{ t('page.apiCases.response.compareMethod') }}</th><th>{{ t('page.apiCases.response.expectedValue') }}</th><th>{{ t('page.apiCases.response.actualValue') }}</th></tr></thead>
          <tbody>
            <tr v-for="(item, idx) in assertInfo" :key="idx" :class="item.passed === true ? 'assert-passed' : item.passed === false ? 'assert-failed' : ''">
              <td>
                <el-icon v-if="item.passed === true" color="#67C23A"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="item.passed === false" color="#F56C6C"><CircleCloseFilled /></el-icon>
                <span v-else>-</span>
              </td>
              <td>{{ item.field || item.target || item.name }}</td>
              <td>{{ assertMethodLabel(item.type || item.method || 'eq') }}</td>
              <td>{{ item.expected }}</td>
              <td>{{ item.actual !== undefined ? item.actual : '-' }}</td>
            </tr>
          </tbody>
        </table>
        <el-empty v-else :description="t('page.apiCases.response.noAssertData')" :image-size="48" />
      </template>

      <!-- 日志信息 -->
      <template v-else-if="activeTab === 'logInfo'">
        <div v-if="logData && logData.length" class="log-container">
          <div v-for="(item, idx) in logData" :key="idx" class="log-item" :class="'log-' + (Array.isArray(item) ? (item[0] || 'info').toLowerCase() : (item.level || 'info').toLowerCase())">
            <span class="log-level-badge" :class="'badge-' + (Array.isArray(item) ? (item[0] || 'info').toLowerCase() : (item.level || 'info').toLowerCase())">
              {{ Array.isArray(item) ? (item[0] || 'INFO') : (item.level || 'INFO') }}
            </span>
            <span class="log-message">{{ Array.isArray(item) ? item.slice(1).join(' ') : (item.message || '') }}</span>
          </div>
        </div>
        <el-empty v-else :description="t('page.apiCases.response.noLogData')" :image-size="48" />
      </template>

      <!-- 测试记录 slot -->
      <slot name="records" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Clock, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps({
  result: { type: Object, default: null },
  responseHeaders: { type: Object, default: () => ({}) },
  requestHeaders: { type: Object, default: () => ({}) },
  extractInfo: { type: Array, default: () => [] },
  assertInfo: { type: Array, default: () => [] },
  logData: { type: Array, default: () => [] },
  showRecords: { type: Boolean, default: false },
})

defineEmits(['toggleRecords'])

const activeTab = ref('result')

var ASSERT_METHOD_MAP = {
  eq: () => t('page.apiCases.assertEqual'),
  eq_ignore_case: () => t('page.apiCases.assertEqualIgnoreCase'),
  ne: () => t('page.apiCases.assertNotEqual'),
  contains: () => t('page.apiCases.assertContains'),
  not_contains: () => t('page.apiCases.assertNotContains'),
  gt: () => t('page.apiCases.assertGreaterThan'),
  lt: () => t('page.apiCases.assertLessThan'),
  ge: () => t('page.apiCases.assertGreaterEqual'),
  le: () => t('page.apiCases.assertLessEqual'),
  regex: () => t('page.apiCases.assertRegex'),
}
function assertMethodLabel(method) {
  if (!method) return '-'
  var fn = ASSERT_METHOD_MAP[method]
  return fn ? fn() : method
}

function formatJson(data) {
  if (data === null || data === undefined) return ''
  if (typeof data === 'object') {
    try { return JSON.stringify(data, null, 2) } catch { return String(data) }
  }
  // 尝试解析 JSON 字符串
  if (typeof data === 'string') {
    try {
      var parsed = JSON.parse(data)
      return JSON.stringify(parsed, null, 2)
    } catch { return data }
  }
  return String(data)
}

function isFormData(result) {
  if (!result || !result.request_body) {
    return false
  }
  var ct = ''
  // 优先从 props.requestHeaders 读取，其次从 result.request_headers
  var headers = props.requestHeaders || result.request_headers || {}
  if (headers && typeof headers === 'object') {
    ct = (headers['Content-Type'] || headers['content-type'] || '').toLowerCase()
  }
  return ct.indexOf('form-urlencoded') >= 0 && typeof result.request_body === 'string' && result.request_body.indexOf('=') >= 0
}

function parseFormData(body) {
  if (!body || typeof body !== 'string') return {}
  var params = {}
  body.split('&').forEach(function (pair) {
    var parts = pair.split('=')
    if (parts.length === 2) {
      params[decodeURIComponent(parts[0])] = decodeURIComponent(parts[1])
    }
  })
  return params
}
</script>

<style scoped lang="scss">
.api-response-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 8px;
}

.response-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;

  .response-sub-tabs {
    flex: 1;
    :deep(.el-tabs__header) { margin: 0; }
    :deep(.el-tabs__nav-wrap::after) { display: none; }
  }
}

.response-body {
  flex: 1;
  min-height: 80px;
  overflow: auto;
  padding: 10px 16px;
  background: #fafafa;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  margin: 0 16px 12px;
}

.run-result-block {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 10px;

  &.success { background: var(--el-color-success-light-9); }
  &.fail { background: var(--el-color-danger-light-9); }

  .result-label { font-weight: 600; font-size: 14px; }
  .result-meta { font-size: 12px; color: var(--el-text-color-secondary); margin-left: auto; }
}

.error-message {
  padding: 8px 12px;
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--el-color-danger);
}

.response-pre {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  margin: 0;
}

.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td { padding: 6px 10px; border: 1px solid var(--el-border-color-lighter); text-align: left; }
  th { background: var(--el-fill-color); font-weight: 600; }
  .info-key { font-weight: 500; }
}

.structured-response {
  .info-row { margin-bottom: 8px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
}

.form-params-display {
  margin-top: 8px;

  strong { display: block; margin-bottom: 6px; font-size: 13px; }
}

.assert-passed { background: var(--el-color-success-light-9); }
.assert-failed { background: var(--el-color-danger-light-9); }

.log-container {
  height: 100%;
  overflow-y: auto;
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;

  .log-item {
    padding: 6px 10px;
    margin-bottom: 4px;
    border-radius: 4px;
    line-height: 1.6;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);

    .log-level-badge {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 3px;
      font-size: var(--font-small);
      font-weight: 600;
      margin-right: 8px;
      min-width: 50px;
      text-align: center;

      &.badge-debug { background: #6a9955; color: #fff; }
      &.badge-info { background: #569cd6; color: #fff; }
      &.badge-warning { background: #ce9178; color: #fff; }
      &.badge-error { background: #f44747; color: #fff; }
    }
    .log-message { color: #d4d4d4; word-break: break-all; }
  }
}
</style>
