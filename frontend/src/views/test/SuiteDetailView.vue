<template>
  <div v-loading="loading" class="suite-detail-view app-card">
    <PageHeader :title="suite?.suite_name || t('page.test.suites.title')" />

    <div class="suite-actions">
      <el-button @click="router.push('/test/suites')">{{ t('common.back') }}</el-button>
      <el-button v-if="canEdit" @click="openEdit">{{ t('common.edit') }}</el-button>
      <el-button v-if="canEdit && isRunning" type="danger" @click="stopRun">{{ t('page.test.stopRun') }}</el-button>
      <el-button v-else-if="canEdit" type="primary" :loading="running" @click="run(suiteId)">{{ t('page.test.run') }}</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane :label="t('page.test.tabBasic')" name="basic">
        <el-descriptions v-if="suite" :column="2" border>
          <el-descriptions-item :label="t('page.test.suites.suiteName')">{{ suite.suite_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.suiteType')"><el-tag :type="SUITE_TYPE_MAP[suite.type]?.type" size="small">{{ SUITE_TYPE_MAP[suite.type]?.label || suite.type }}</el-tag></el-descriptions-item>
          <el-descriptions-item :label="t('common.description')">{{ suite.description || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.runMode')">{{ RUN_MODE_MAP[suite.run_mode] || suite.run_mode }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.apiCases.selectEnv')">{{ suite.environment_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.caseCount')">{{ suite.case_count }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.createdAt')">{{ formatTime(suite.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.lastRun')">
            <template v-if="suite.last_run?.status">
              <StatusTag :status="suite.last_run.status" :map="RUN_STATUS_MAP" />
              <span style="margin-left: 8px">{{ suite.last_run.success_rate || '' }}</span>
            </template>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- 关联用例 -->
      <el-tab-pane :label="t('page.test.tabCases')" name="cases">
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <el-input v-model="caseSearch" :placeholder="t('common.keyword')" clearable style="width: 240px" @change="loadCases" />
          <el-button type="primary" @click="showCasePicker = true">{{ t('page.test.addCases') }}</el-button>
          <el-button v-if="selectedCaseIds.length" type="danger" @click="batchRemoveCases">{{ t('common.batchDelete') }} ({{ selectedCaseIds.length }})</el-button>
          <el-button v-if="selectedCaseIds.length" @click="batchToggleDep(true)">{{ t('page.test.enableDep') }}</el-button>
          <el-button v-if="selectedCaseIds.length" @click="batchToggleDep(false)">{{ t('page.test.disableDep') }}</el-button>
        </div>
        <PaginatedTable v-model:page="casePage" v-model:page-size="casePageSize" :data="cases" :loading="casesLoading" :total="caseTotal" row-key="id" @page-change="loadCases" @selection-change="onCaseSelectionChange">
          <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
          <AppTableColumn prop="case_id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" />
          <AppTableColumn prop="interface_name" variant="content" :label="t('page.defects.interfaceName')" />
          <AppTableColumn variant="fixed" label="Path" :width="200">
            <template #default="{ row }"><el-tag size="small" style="margin-right: 4px">{{ row.interface_method }}</el-tag>{{ row.interface_path }}</template>
          </AppTableColumn>
          <AppTableColumn variant="content" :label="t('page.apiCases.preconditionCases')">
            <template #default="{ row }">
              <template v-if="preconditionNamesMap[row.case_id] && preconditionNamesMap[row.case_id].length">
                <el-tag v-for="name in preconditionNamesMap[row.case_id]" :key="name" size="small" type="info" style="margin: 2px">{{ name }}</el-tag>
              </template>
              <span v-else>-</span>
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.useDependency')" :width="100">
            <template #default="{ row }"><el-switch :model-value="row.use_dependency" @change="toggleDep(row)" /></template>
          </AppTableColumn>
          <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="160">
            <template #default="{ row, $index }">
              <el-button link :disabled="$index === 0" @click="moveCase(row, -1)">{{ t('page.test.moveUp') }}</el-button>
              <el-button link :disabled="$index === cases.length - 1" @click="moveCase(row, 1)">{{ t('page.test.moveDown') }}</el-button>
              <ConfirmDelete @confirm="removeCase(row)"><el-button link type="danger">{{ t('common.delete') }}</el-button></ConfirmDelete>
            </template>
          </AppTableColumn>
        </PaginatedTable>
      </el-tab-pane>

      <!-- 执行历史 -->
      <el-tab-pane :label="t('page.test.tabHistory')" name="history">
        <div style="margin-bottom: 8px">
          <el-button size="small" @click="loadHistory">{{ t('common.refresh') || '刷新' }}</el-button>
        </div>
        <AppTable :data="history">
          <AppTableColumn prop="suite_name" variant="content" :label="t('page.test.suites.suiteName')" min-width="120">
            <template #default>{{ suite?.suite_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn variant="fixed" :label="t('page.test.relatedTask')" :width="120">
            <template #default="{ row }">{{ row.task_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.caseCount')" :width="90">
            <template #default="{ row }">{{ row.total_cases ?? '-' }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.execProgress')" :width="160">
            <template #default="{ row }">
              <el-progress :percentage="calcProgress(row)" :status="progressStatus(row)" :stroke-width="14" :text-inside="true" />
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.execResult')" :width="80">
            <template #default="{ row }">
              <el-tag v-if="getRunResult(row)" :type="getRunResult(row) === 'success' ? 'success' : getRunResult(row) === 'error' ? 'warning' : 'danger'" size="small">{{ getRunResultLabel(row) }}</el-tag>
              <StatusTag v-else :status="row.status" :map="RUN_STATUS_MAP" />
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.successRate')" :width="120">
            <template #default="{ row }">{{ calcSuccessRate(row) }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('execution.duration')" :width="90">
            <template #default="{ row }">{{ row.duration_ms ? (row.duration_ms / 1000).toFixed(1) + 's' : '-' }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.executor')" :width="100">
            <template #default="{ row }">{{ row.triggered_by_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.startedAt')" :width="170">
            <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
          </AppTableColumn>
          <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="140">
            <template #default="{ row }">
              <el-button link type="primary" @click="rerunHistory(row)">{{ t('page.test.rerun') || '重新执行' }}</el-button>
              <el-button link type="primary" @click="viewReport(row)">{{ t('page.test.report') }}</el-button>
            </template>
          </AppTableColumn>
        </AppTable>
      </el-tab-pane>
    </el-tabs>

    <!-- 报告 Drawer -->
    <el-drawer v-model="reportVisible" :title="t('page.test.report')" size="70%">
      <ReportSummary v-if="report" :report="report" :can-edit="canEdit" @view-log="openLog" @linked="reloadReport" @create-defect="openDefectFromReport" />
    </el-drawer>

    <!-- 用例执行日志 Drawer -->
    <CaseRunLogDrawer v-model="logVisible" :case-run-id="logCaseRunId" />

    <!-- 从报告创建缺陷对话框 -->
    <DefectCreateDialog v-model="showDefectDialog" :case-run-id="defectCaseRunId" :default-title="defectDefaultTitle" :default-steps="defectDefaultSteps" :loading="defectSaving" @submit="submitDefectFromReport" />

    <!-- 编辑套件对话框 -->
    <el-dialog :close-on-click-modal="false" v-model="showEdit" :title="t('page.test.suites.editSuite')" width="560px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.test.suites.suiteName')"><el-input v-model="editForm.suite_name" /></el-form-item>
        <el-form-item :label="t('common.description')"><el-input v-model="editForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item :label="t('page.apiCases.selectEnv')">
          <EnvironmentSelect v-model="editForm.environment_id" />
        </el-form-item>
        <el-form-item :label="t('page.test.runMode')">
          <el-radio-group v-model="editForm.run_mode">
            <el-radio value="serial">{{ t('page.test.serial') }}</el-radio>
            <el-radio value="parallel">{{ t('page.test.parallel') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 用例选择器（复用接口用例目录树组件） -->
    <ReuseCaseDialog v-model="showCasePicker" mode="select" :pre-selected-ids="existingCaseIds" @confirmed="addCasesConfirmed" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSuite, listSuiteCases, updateSuite, appendSuiteCases, deleteSuiteCases, reorderSuiteCases, patchSuiteCaseFlags } from '@/api/testManagement'
import { batchGetApiCases } from '@/api/apiTest'
import { runSuite, getSuiteProgress, getSuiteReport, getSuiteHistory, createDefectFromRun, getCaseRunLog } from '@/api/testExecution'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useRunExecution } from '@/composables/useRunExecution'
import { useReportViewer } from '@/composables/useReportViewer'
import { RUN_STATUS_MAP, SUITE_TYPE_MAP, RUN_MODE_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import ReportSummary from '@/components/execution/ReportSummary.vue'
import CaseRunLogDrawer from '@/components/execution/CaseRunLogDrawer.vue'
import DefectCreateDialog from '@/components/execution/DefectCreateDialog.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import ReuseCaseDialog from '@/components/api-test/ReuseCaseDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const { page: casePage, pageSize: casePageSize, total: caseTotal } = usePagination()
const suiteId = computed(() => Number(route.params.suiteId))

const loading = ref(false)
const suite = ref(null)
const cases = ref([])
const casesLoading = ref(false)
const preconditionNamesMap = ref({})

async function loadPreconditionNames(caseIds) {
  if (!caseIds.length) return
  try {
    var res = await batchGetApiCases(caseIds)
    var fullCases = res.data.data || []
    var allPreIds = []
    var casePreMap = {}
    fullCases.forEach(function (c) {
      var preIds = (c.case_payload || {}).precondition_ids || []
      if (preIds.length) {
        casePreMap[c.id] = preIds
        preIds.forEach(function (pid) { if (!allPreIds.includes(pid)) allPreIds.push(pid) })
      }
    })
    if (!allPreIds.length) return
    var preRes = await batchGetApiCases(allPreIds)
    var preCases = preRes.data.data || []
    var preNameMap = {}
    preCases.forEach(function (pc) { preNameMap[pc.id] = pc.title || pc.name || '' })
    for (var cid in casePreMap) {
      preconditionNamesMap.value[cid] = casePreMap[cid].map(function (pid) { return preNameMap[pid] || '' }).filter(Boolean)
    }
  } catch (e) {
    console.error('[SuiteDetailView] loadPreconditionNames failed:', e)
  }
}
const history = ref([])
const activeTab = ref('basic')

// Shared: run execution
const { running, activeRun, progress, isRunning, run, stopRun, resumePolling } = useRunExecution({
  triggerFn: runSuite,
  progressFn: getSuiteProgress,
  getRunId: (r) => r.suite_run_id ?? r.run_id ?? r.id,
  onStarted: () => { activeTab.value = 'history'; load(true); loadHistory() },
  onTick: () => { loadHistory() },
  onComplete: () => { loadHistory(); load(true) },
})

// Shared: report viewer
const { reportVisible, report, reportRunId, viewReport, reloadReport } = useReportViewer(getSuiteReport)

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
    // 1. Request content
    var reqParts = []
    var method = reqInfo.method || data.method || ''
    var url = reqInfo.url || data.url || ''
    if (method || url) reqParts.push(method.toUpperCase() + ' ' + url)
    var reqHeaders = reqInfo.headers || data.request_headers || {}
    var ct = reqHeaders['Content-Type'] || reqHeaders['content-type'] || ''
    if (ct) reqParts.push('Content-Type: ' + ct)
    var reqBody = reqInfo.body || data.request_body
    if (reqBody) reqParts.push(typeof reqBody === 'string' ? reqBody : JSON.stringify(reqBody, null, 2))
    if (reqParts.length) parts.push('1、请求内容\n' + reqParts.join('\n'))
    // 2. Response content
    var resParts = []
    if (ri.status_code != null) resParts.push('Status: ' + ri.status_code)
    var resBody = ri.body || data.response_body
    if (resBody) {
      var body = typeof resBody === 'string' ? resBody : JSON.stringify(resBody, null, 2)
      if (body.length > 2000) body = body.substring(0, 2000) + '\n...(truncated)'
      resParts.push(body)
    }
    if (resParts.length) parts.push('2、响应内容\n' + resParts.join('\n'))
  }
  // 3. Assertion error log
  var logLines = []
  if (data) {
    var detail2 = data._debug_detail || data
    logLines = detail2.log_data || data.log_data || []
  }
  var log = Array.isArray(logLines) ? logLines.map(function (l) { return Array.isArray(l) ? l.join(' ') : String(l) }).join('\n') : (logData?.log_data || '')
  var errMsg = logData?.error_message || ''
  var errorContent = log || errMsg
  if (errorContent) parts.push('3、断言错误日志\n' + errorContent)
  return parts.join('\n\n')
}

async function openDefectFromReport(row) {
  defectCaseRunId.value = row.id
  defectDefaultTitle.value = row.case_name || ''
  defectDefaultSteps.value = ''
  // Fetch run log BEFORE opening dialog so steps are pre-filled
  try {
    var res = await getCaseRunLog(row.id)
    defectDefaultSteps.value = buildDefectSteps(res.data.data)
  } catch (e) {
    // silent — steps will just be empty
  }
  showDefectDialog.value = true
}

async function submitDefectFromReport(payload) {
  defectSaving.value = true
  try {
    await createDefectFromRun({ ...payload, source_type: 'api_case', source_run_id: reportRunId.value, case_run_id: defectCaseRunId.value })
    ElMessage.success(t('common.saved'))
    showDefectDialog.value = false
    reloadReport()
  } finally {
    defectSaving.value = false
  }
}

// Case search
const caseSearch = ref('')
const selectedCaseIds = ref([])

// Edit
const showEdit = ref(false)
const editSaving = ref(false)
const editForm = reactive({ suite_name: '', description: '', environment_id: null, run_mode: 'serial' })

// Case picker
const showCasePicker = ref(false)
const existingCaseIds = computed(() => cases.value.map((c) => c.case_id))

// --- Load ---
function recoverRunningState() {
  if (!activeRun.value && history.value.length) {
    var runningItem = history.value.find(function (h) { return h.status === 'running' || h.status === 'pending' })
    if (runningItem) {
      resumePolling(runningItem.id)
    }
  }
}

async function load(silent) {
  if (!suiteId.value || Number.isNaN(suiteId.value)) return
  if (!silent) loading.value = true
  try {
    const [sRes, hRes] = await Promise.all([getSuite(suiteId.value), getSuiteHistory(suiteId.value)])
    suite.value = sRes.data.data
    history.value = hRes.data.data?.items ?? hRes.data.data ?? []
    recoverRunningState()
    await loadCases()
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadHistory() {
  if (!suiteId.value || Number.isNaN(suiteId.value)) return
  try {
    var res = await getSuiteHistory(suiteId.value)
    history.value = res.data.data?.items ?? res.data.data ?? []
    recoverRunningState()
  } catch (e) {
    // silent
  }
}

async function loadCases() {
  casesLoading.value = true
  try {
    const res = await listSuiteCases(suiteId.value, { page: casePage.value, page_size: casePageSize.value, q: caseSearch.value || undefined })
    cases.value = res.data.data?.items ?? res.data.data ?? []
    caseTotal.value = res.data.data?.total ?? 0
    // Load precondition names for displayed cases
    var ids = cases.value.map(function (c) { return c.case_id }).filter(Boolean)
    if (ids.length) loadPreconditionNames(ids)
  } finally {
    casesLoading.value = false
  }
}

function onCaseSelectionChange(rows) { selectedCaseIds.value = rows.map((r) => r.case_id) }

// --- Edit ---
function openEdit() {
  Object.assign(editForm, {
    suite_name: suite.value.suite_name,
    description: suite.value.description || '',
    environment_id: suite.value.environment_id,
    run_mode: suite.value.run_mode,
  })
  showEdit.value = true
}

async function saveEdit() {
  editSaving.value = true
  try { await updateSuite(suiteId.value, editForm); ElMessage.success(t('common.saved')); showEdit.value = false; load() }
  finally { editSaving.value = false }
}

// --- Cases management ---
async function removeCase(row) { await deleteSuiteCases(suiteId.value, { case_ids: [row.case_id] }); ElMessage.success(t('common.deleted')); loadCases() }

async function batchRemoveCases() {
  try { await ElMessageBox.confirm(t('common.batchDeleteConfirm', { count: selectedCaseIds.value.length }), t('common.warning'), { type: 'warning' }); await deleteSuiteCases(suiteId.value, { case_ids: selectedCaseIds.value }); selectedCaseIds.value = []; loadCases() }
  catch (e) { if (e !== 'cancel') ElMessage.error(e.message) }
}

async function moveCase(row, dir) {
  var ids = cases.value.map((c) => c.case_id); var idx = ids.indexOf(row.case_id); var ni = idx + dir
  if (ni < 0 || ni >= ids.length) return; [ids[idx], ids[ni]] = [ids[ni], ids[idx]]
  await reorderSuiteCases(suiteId.value, { ordered_case_ids: ids }); loadCases()
}

async function toggleDep(row) { await patchSuiteCaseFlags(suiteId.value, { case_ids: [row.case_id], use_dependency: !row.use_dependency }); loadCases() }

async function batchToggleDep(enable) { await patchSuiteCaseFlags(suiteId.value, { case_ids: selectedCaseIds.value, use_dependency: enable }); ElMessage.success(t('common.saved')); loadCases() }

// --- Case picker (ReuseCaseDialog in select mode) ---
async function addCasesConfirmed(selectedCases) {
  if (!selectedCases || !selectedCases.length) return
  // Filter out cases already associated with this suite
  var existingSet = new Set(existingCaseIds.value)
  var newCases = selectedCases.filter(function (c) { return !existingSet.has(c.id) })
  if (!newCases.length) return
  try {
    await appendSuiteCases(suiteId.value, {
      cases: newCases.map((c) => ({ case_id: c.id, use_dependency: true })),
    })
    ElMessage.success(t('common.saved'))
    loadCases()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  }
}

// --- History helpers ---
function calcProgress(row) {
  if (!row.total_cases) return 0
  var done = (row.passed_cases || 0) + (row.failed_cases || 0) + (row.error_cases || 0)
  return Math.round(done / row.total_cases * 100)
}

function progressStatus(row) {
  if (row.status === 'running') return undefined
  if (row.status === 'completed' && row.failed_cases === 0 && row.error_cases === 0) return 'success'
  if (row.status === 'failed' || (row.status === 'completed' && ((row.failed_cases || 0) + (row.error_cases || 0) > 0))) return 'exception'
  return undefined
}

function getRunResult(row) {
  if (row.status === 'completed') {
    if ((row.failed_cases || 0) + (row.error_cases || 0) > 0) return 'fail'
    return 'success'
  }
  if (row.status === 'failed') {
    if ((row.error_cases || 0) > 0 && (row.failed_cases || 0) === 0) return 'error'
    return 'fail'
  }
  return null
}

function getRunResultLabel(row) {
  var r = getRunResult(row)
  if (r === 'success') return t('page.test.resultSuccess')
  if (r === 'fail') return t('page.test.resultFail')
  if (r === 'error') return t('common.error')
  return ''
}

function calcSuccessRate(row) {
  if (!row.total_cases) return '-'
  var done = (row.passed_cases || 0) + (row.failed_cases || 0) + (row.error_cases || 0)
  if (!done) return '-'
  var pct = (row.passed_cases || 0) / row.total_cases * 100
  return pct.toFixed(1) + '% (' + (row.passed_cases || 0) + '/' + row.total_cases + ')'
}

async function rerunHistory() {
  try {
    await run(suiteId.value)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
.suite-detail-view {
  position: relative;
}
.suite-actions {
  position: absolute;
  top: 87px;
  right: 16px;
  z-index: 2;
}
</style>
