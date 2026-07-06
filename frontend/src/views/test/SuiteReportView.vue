<template>
  <div v-loading="loading" class="suite-report-view app-card">
    <PageHeader :title="t('page.test.report') + ' — ' + (report?.suite_name || '')" />
    <div class="report-actions">
      <el-button @click="goBack">{{ t('common.back') }}</el-button>
    </div>

    <div class="suite-report-body">
      <ReportSummary
        v-if="report"
        :report="report"
        :can-edit="canEdit"
        @view-log="openLog"
        @linked="reloadReport"
        @create-defect="openDefectFromReport"
      />
    </div>

    <!-- 用例执行日志 Drawer -->
    <CaseRunLogDrawer v-model="logVisible" :case-run-id="logCaseRunId" />

    <!-- 从报告创建缺陷对话框 -->
    <DefectCreateDialog
      v-model="showDefectDialog"
      :case-run-id="defectCaseRunId"
      :default-title="defectDefaultTitle"
      :default-steps="defectDefaultSteps"
      :loading="defectSaving"
      @submit="submitDefectFromReport"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getSuiteReport, getCaseRunLog, createDefectFromRun } from '@/api/testExecution'
import { usePermission } from '@/composables/usePermission'
import { useReportViewer } from '@/composables/useReportViewer'
import PageHeader from '@/components/common/PageHeader.vue'
import ReportSummary from '@/components/execution/ReportSummary.vue'
import CaseRunLogDrawer from '@/components/execution/CaseRunLogDrawer.vue'
import DefectCreateDialog from '@/components/execution/DefectCreateDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()

const runId = Number(route.params.runId)
const loading = ref(false)

const { report, reportRunId, reloadReport } = useReportViewer(getSuiteReport)

// Log drawer
const logVisible = ref(false)
const logCaseRunId = ref(null)
function openLog(row) { logCaseRunId.value = row.id; logVisible.value = true }

// Defect from report
const showDefectDialog = ref(false)
const defectCaseRunId = ref(null)
const defectDefaultTitle = ref('')
const defectDefaultSteps = ref('')
const defectSaving = ref(false)

function buildDefectSteps(logData) {
  var parts = []
  var data = logData?.api_requests_info
  if (data) {
    var detail = data._debug_detail || data
    var ri = detail.response_info || data.response_info || {}
    var reqInfo = detail.request_info || data.request_info || {}
    var reqParts = []
    var method = reqInfo.method || data.method || ''
    var url = reqInfo.url || data.url || ''
    if (method || url) reqParts.push(method.toUpperCase() + ' ' + url)
    var reqHeaders = reqInfo.headers || data.request_headers || {}
    var ct = reqHeaders['Content-Type'] || reqHeaders['content-type'] || ''
    if (ct) reqParts.push('Content-Type: ' + ct)
    var reqBody = reqInfo.body || data.request_body
    if (reqBody) reqParts.push(typeof reqBody === 'string' ? reqBody : JSON.stringify(reqBody, null, 2))
    if (reqParts.length) parts.push(t('page.test.requestContent') + '\n' + reqParts.join('\n'))
    var resParts = []
    if (ri.status_code != null) resParts.push('Status: ' + ri.status_code)
    var resBody = ri.body || data.response_body
    if (resBody) {
      var body = typeof resBody === 'string' ? resBody : JSON.stringify(resBody, null, 2)
      if (body.length > 2000) body = body.substring(0, 2000) + '\n...(truncated)'
      resParts.push(body)
    }
    if (resParts.length) parts.push(t('page.test.responseContent') + '\n' + resParts.join('\n'))
  }
  var logLines = []
  if (data) {
    var detail2 = data._debug_detail || data
    logLines = detail2.log_data || data.log_data || []
  }
  var log = Array.isArray(logLines) ? logLines.map(function (l) { return Array.isArray(l) ? l.join(' ') : String(l) }).join('\n') : (logData?.log_data || '')
  var errMsg = logData?.error_message || ''
  var errorContent = log || errMsg
  if (errorContent) parts.push(t('page.test.assertErrorLog') + '\n' + errorContent)
  return parts.join('\n\n')
}

async function openDefectFromReport(row) {
  defectCaseRunId.value = row.id
  defectDefaultTitle.value = row.case_name || ''
  defectDefaultSteps.value = ''
  try {
    var res = await getCaseRunLog(row.id)
    defectDefaultSteps.value = buildDefectSteps(res.data.data)
  } catch (e) { /* silent */ }
  showDefectDialog.value = true
}

async function submitDefectFromReport(payload) {
  defectSaving.value = true
  try {
    await createDefectFromRun({ ...payload, source_type: 'api_case', source_run_id: reportRunId.value, case_run_id: defectCaseRunId.value })
    ElMessage.success(t('common.saved'))
    showDefectDialog.value = false
    reloadReport()
  } finally { defectSaving.value = false }
}

function goBack() {
  var suiteId = route.params.suiteId
  router.push(suiteId ? `/test/suites/${suiteId}` : '/test/suites')
}

async function loadReport() {
  loading.value = true
  try {
    var res = await getSuiteReport(runId)
    report.value = res.data.data
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  } finally { loading.value = false }
}

onMounted(loadReport)
</script>

<style lang="scss" scoped>
.suite-report-view {
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  overflow: hidden;
}
.report-actions {
  position: absolute;
  top: 87px;
  right: 16px;
  z-index: 2;
}
.suite-report-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;

  :deep(.report-summary) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
}
</style>
