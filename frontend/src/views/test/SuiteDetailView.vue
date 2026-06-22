<template>
  <div v-loading="loading" class="suite-detail-view app-card">
    <PageHeader :title="suite?.suite_name || t('page.test.suites.title')">
      <template #actions>
        <el-button @click="router.push('/test/suites')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" @click="openEdit">{{ t('common.edit') }}</el-button>
        <el-button v-if="canEdit && activeRun && isRunning" type="danger" @click="stopRun">{{ t('page.test.stopRun') }}</el-button>
        <el-button v-if="canEdit" type="primary" :loading="running" @click="run(suiteId)">{{ t('page.test.run') }}</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane :label="t('page.test.tabBasic')" name="basic">
        <el-descriptions v-if="suite" :column="2" border>
          <el-descriptions-item :label="t('page.test.suites.suiteName')">{{ suite.suite_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.suiteType')"><el-tag :type="SUITE_TYPE_MAP[suite.type]?.type" size="small">{{ SUITE_TYPE_MAP[suite.type]?.label || suite.type }}</el-tag></el-descriptions-item>
          <el-descriptions-item :label="t('common.description')">{{ suite.description || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.runMode')">{{ RUN_MODE_MAP[suite.run_mode] || suite.run_mode }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.apiCases.selectEnv')">{{ suite.environment_name || suite.environment_id || '-' }}</el-descriptions-item>
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

      <!-- 绑定任务 -->
      <el-tab-pane :label="t('page.test.tabTasks')" name="tasks">
        <template v-if="suite?.bound_tasks?.length">
          <AppTable :data="suite.bound_tasks">
            <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
            <AppTableColumn prop="task_name" variant="content" :label="t('common.name')" />
            <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="100">
              <template #default="{ row }">
                <el-button link type="primary" @click="router.push(`/test/tasks/${row.id}`)">{{ t('common.view') }}</el-button>
              </template>
            </AppTableColumn>
          </AppTable>
        </template>
        <el-empty v-else :description="t('page.test.noBoundTasks')" />
      </el-tab-pane>

      <!-- 执行历史 -->
      <el-tab-pane :label="t('page.test.tabHistory')" name="history">
        <ExecutionHistoryTab :history="history" :active-run="activeRun" :progress="progress" @view-report="viewReport" />
      </el-tab-pane>
    </el-tabs>

    <!-- 报告 Drawer -->
    <el-drawer v-model="reportVisible" :title="t('page.test.report')" size="70%">
      <ReportSummary v-if="report" :report="report" :can-edit="canEdit" @view-log="openLog" @linked="reloadReport" @create-defect="openDefectFromReport" />
    </el-drawer>

    <!-- 用例执行日志 Drawer -->
    <CaseRunLogDrawer v-model="logVisible" :case-run-id="logCaseRunId" />

    <!-- 从报告创建缺陷对话框 -->
    <DefectCreateDialog v-model="showDefectDialog" :case-run-id="defectCaseRunId" :default-title="defectDefaultTitle" :loading="defectSaving" @submit="submitDefectFromReport" />

    <!-- 编辑套件对话框 -->
    <el-dialog :close-on-click-modal="false" v-model="showEdit" :title="t('page.test.suites.editSuite')" width="560px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.test.suites.suiteName')"><el-input v-model="editForm.suite_name" /></el-form-item>
        <el-form-item :label="t('common.description')"><el-input v-model="editForm.description" type="textarea" :rows="2" /></el-form-item>
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

    <!-- 用例选择器对话框 -->
    <el-dialog v-model="showCasePicker" :title="t('page.test.addCases')" width="800px">
      <el-input v-model="pickerSearch" :placeholder="t('common.keyword')" clearable style="width: 240px; margin-bottom: 12px" @change="loadPickerCases" />
      <PaginatedTable v-model:page="pickerPage" v-model:page-size="pickerPageSize" :data="pickerCases" :loading="pickerLoading" :total="pickerTotal" row-key="id" @page-change="loadPickerCases" @selection-change="onPickerSelectionChange">
        <AppTableColumn type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
        <AppTableColumn prop="title" variant="content" :label="t('page.functional.caseName')" />
        <AppTableColumn prop="interface_name" variant="content" :label="t('page.defects.interfaceName')" />
        <AppTableColumn prop="interface_path" variant="content" label="Path" />
      </PaginatedTable>
      <template #footer>
        <el-button @click="showCasePicker = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="pickerSaving" @click="addCases">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSuite, listSuiteCases, updateSuite, appendSuiteCases, deleteSuiteCases, reorderSuiteCases, patchSuiteCaseFlags, pickApiCases } from '@/api/testManagement'
import { runSuite, getSuiteProgress, getSuiteReport, getSuiteHistory, createDefectFromRun } from '@/api/testExecution'
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
import ExecutionHistoryTab from '@/components/execution/ExecutionHistoryTab.vue'
import CaseRunLogDrawer from '@/components/execution/CaseRunLogDrawer.vue'
import DefectCreateDialog from '@/components/execution/DefectCreateDialog.vue'

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
const history = ref([])
const activeTab = ref('basic')

// Shared: run execution
const { running, activeRun, progress, isRunning, run, stopRun } = useRunExecution({
  triggerFn: runSuite,
  progressFn: getSuiteProgress,
  getRunId: (r) => r.suite_run_id ?? r.run_id ?? r.id,
  onStarted: () => { activeTab.value = 'history'; load() },
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
const defectSaving = ref(false)

function openDefectFromReport(row) {
  defectCaseRunId.value = row.id
  defectDefaultTitle.value = (row.case_name || '') + ' - ' + t('execution.defectSuffix')
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
const editForm = reactive({ suite_name: '', description: '', run_mode: 'serial' })

// Case picker
const showCasePicker = ref(false)
const pickerSearch = ref('')
const pickerCases = ref([])
const pickerLoading = ref(false)
const pickerSaving = ref(false)
const pickerPage = ref(1)
const pickerPageSize = ref(20)
const pickerTotal = ref(0)
const pickerSelected = ref([])

// --- Load ---
async function load() {
  loading.value = true
  try {
    const [sRes, hRes] = await Promise.all([getSuite(suiteId.value), getSuiteHistory(suiteId.value)])
    suite.value = sRes.data.data
    history.value = hRes.data.data?.items ?? hRes.data.data ?? []
    await loadCases()
  } finally {
    loading.value = false
  }
}

async function loadCases() {
  casesLoading.value = true
  try {
    const res = await listSuiteCases(suiteId.value, { page: casePage.value, page_size: casePageSize.value, q: caseSearch.value || undefined })
    cases.value = res.data.data?.items ?? res.data.data ?? []
    caseTotal.value = res.data.data?.total ?? 0
  } finally {
    casesLoading.value = false
  }
}

function onCaseSelectionChange(rows) { selectedCaseIds.value = rows.map((r) => r.case_id) }

// --- Edit ---
function openEdit() { Object.assign(editForm, { suite_name: suite.value.suite_name, description: suite.value.description || '', run_mode: suite.value.run_mode }); showEdit.value = true }

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

// --- Case picker ---
async function loadPickerCases() {
  pickerLoading.value = true
  try { var res = await pickApiCases({ project_id: suite.value.project_id, q: pickerSearch.value || undefined, page: pickerPage.value, page_size: pickerPageSize.value }); pickerCases.value = res.data.data?.items ?? []; pickerTotal.value = res.data.data?.total ?? 0 }
  finally { pickerLoading.value = false }
}
function onPickerSelectionChange(rows) { pickerSelected.value = rows.map((r) => r.id) }
async function addCases() {
  if (!pickerSelected.value.length) return; pickerSaving.value = true
  try { await appendSuiteCases(suiteId.value, { cases: pickerSelected.value.map((id) => ({ case_id: id, use_dependency: true })) }); ElMessage.success(t('common.saved')); showCasePicker.value = false; pickerSelected.value = []; loadCases() }
  finally { pickerSaving.value = false }
}

onMounted(load)
</script>
