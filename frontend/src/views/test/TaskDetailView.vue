<template>
  <div v-loading="loading" class="task-detail-view app-card">
    <PageHeader :title="task?.task_name || t('page.test.tasks.title')" />

    <div class="task-actions">
      <el-button @click="router.push('/test/tasks')">{{ t('common.back') }}</el-button>
      <el-button v-if="canEdit" @click="openEdit">{{ t('common.edit') }}</el-button>
      <el-button v-if="canEdit && isRunning" type="danger" @click="stopRun">{{ t('page.test.stopRun') }}</el-button>
      <el-button v-else-if="canEdit && !isManual" type="primary" :loading="running" @click="run(taskId)">{{ t('page.test.run') }}</el-button>
      <el-button v-if="canEdit && isManual" type="warning" @click="startManualRun">{{ t('page.test.manualRun') }}</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane :label="t('page.test.tabBasic')" name="basic">
        <el-descriptions v-if="task" :column="2" border>
          <el-descriptions-item :label="t('page.test.tasks.taskName')">{{ task.task_name }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.taskType')"><el-tag :type="TASK_TYPE_MAP[task.type]?.type" size="small">{{ TASK_TYPE_MAP[task.type]?.label || task.type }}</el-tag></el-descriptions-item>
          <el-descriptions-item :label="t('common.description')">{{ task.description || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="!isManual" :label="t('page.test.runMode')">{{ RUN_MODE_MAP[task.run_mode] || task.run_mode || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="!isManual" :label="t('page.apiCases.selectEnv')">{{ task.environment_name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.caseCount')">{{ task.case_count }}</el-descriptions-item>
          <el-descriptions-item :label="t('common.createdAt')">{{ formatTime(task.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.test.lastRun')">
            <template v-if="task.last_run?.status">
              <StatusTag :status="task.last_run.status" :map="RUN_STATUS_MAP" />
              <span style="margin-left: 8px">{{ task.last_run.success_rate || '' }}</span>
            </template>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- 关联套件 (API/UI任务) -->
      <el-tab-pane v-if="!isManual" :label="t('page.test.tabSuites')" name="suites">
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <el-button type="primary" @click="openSuitePicker">{{ t('page.test.addSuites') }}</el-button>
          <el-button v-if="selectedSuiteIds.length" type="danger" @click="batchRemoveSuites">{{ t('common.batchDelete') }} ({{ selectedSuiteIds.length }})</el-button>
        </div>
        <AppTable :data="taskSuites" @selection-change="onSuiteSelectionChange">
          <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
          <AppTableColumn prop="suite_id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn prop="suite_name" variant="content" :label="t('page.test.suites.suiteName')" />
          <AppTableColumn prop="case_count" variant="fixed" :label="t('page.test.caseCount')" :width="80" />
          <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="160">
            <template #default="{ row, $index }">
              <el-button link :disabled="$index === 0" @click="moveSuite(row, -1)">{{ t('page.test.moveUp') }}</el-button>
              <el-button link :disabled="$index === taskSuites.length - 1" @click="moveSuite(row, 1)">{{ t('page.test.moveDown') }}</el-button>
              <ConfirmDelete @confirm="removeSuite(row)"><el-button link type="danger">{{ t('common.delete') }}</el-button></ConfirmDelete>
            </template>
          </AppTableColumn>
        </AppTable>
      </el-tab-pane>

      <!-- 关联用例 (手工/功能任务) -->
      <el-tab-pane v-if="isManual" :label="t('page.test.tabCases')" name="cases">
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <el-button type="primary" @click="openCasePicker">{{ t('page.test.addCases') }}</el-button>
          <el-button v-if="selectedCaseIds.length" type="danger" @click="batchRemoveCases">{{ t('common.batchDelete') }} ({{ selectedCaseIds.length }})</el-button>
        </div>
        <AppTable :data="taskCases" @selection-change="onCaseSelectionChange">
          <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
          <AppTableColumn prop="case_id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" />
          <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="100">
            <template #default="{ row }">
              <ConfirmDelete @confirm="removeCase(row)"><el-button link type="danger">{{ t('common.delete') }}</el-button></ConfirmDelete>
            </template>
          </AppTableColumn>
        </AppTable>
      </el-tab-pane>

      <!-- 执行历史 -->
      <el-tab-pane :label="t('page.test.tabHistory')" name="history">
        <div style="margin-bottom: 8px">
          <el-button size="small" @click="loadHistory">{{ t('common.refresh') || '刷新' }}</el-button>
        </div>
        <AppTable :data="history">
          <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn variant="fixed" :label="t('page.test.tasks.taskName')" :width="140">
            <template #default>{{ task?.task_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn variant="content" :label="t('page.test.tabSuites')" min-width="160">
            <template #default>{{ suiteNamesDisplay || '-' }}</template>
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

    <!-- 报告跳转由此处 viewReport 处理 -->

    <!-- 编辑任务对话框 -->
    <el-dialog :close-on-click-modal="false" v-model="showEdit" :title="t('page.test.tasks.editTask')" width="560px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.test.tasks.taskName')"><el-input v-model="editForm.task_name" /></el-form-item>
        <el-form-item :label="t('common.description')"><el-input v-model="editForm.description" type="textarea" :rows="2" /></el-form-item>
        <template v-if="!isManual">
          <el-form-item :label="t('page.apiCases.selectEnv')">
            <EnvironmentSelect v-model="editForm.environment_id" />
          </el-form-item>
          <el-form-item :label="t('page.test.runMode')">
            <el-radio-group v-model="editForm.run_mode">
              <el-radio value="serial">{{ t('page.test.serial') }}</el-radio>
              <el-radio value="parallel">{{ t('page.test.parallel') }}</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 套件选择器 -->
    <el-dialog v-model="showSuitePicker" :title="t('page.test.addSuites')" width="700px">
      <el-input v-model="suitePickerSearch" :placeholder="t('common.keyword')" clearable style="width: 240px; margin-bottom: 12px" @change="loadSuitePicker" />
      <PaginatedTable ref="suitePickerTableRef" v-model:page="spPage" v-model:page-size="spPageSize" :data="suitePickerItems" :loading="suitePickerLoading" :total="suitePickerTotal" row-key="id" @page-change="loadSuitePicker" @selection-change="onSuitePickerSelectionChange">
        <AppTableColumn type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
        <AppTableColumn prop="suite_name" variant="content" :label="t('page.test.suites.suiteName')" />
        <AppTableColumn prop="case_count" variant="fixed" :label="t('page.test.caseCount')" :width="80" />
      </PaginatedTable>
      <template #footer>
        <el-button @click="showSuitePicker = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="suitePickerSaving" @click="addSuites">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 用例选择器 (手工任务) -->
    <el-dialog v-model="showCasePicker" :title="t('page.test.addCases')" width="700px">
      <el-input v-model="casePickerSearch" :placeholder="t('common.keyword')" clearable style="width: 240px; margin-bottom: 12px" @change="loadCasePicker" />
      <PaginatedTable v-model:page="cpPage" v-model:page-size="cpPageSize" :data="casePickerItems" :loading="casePickerLoading" :total="casePickerTotal" row-key="id" @page-change="loadCasePicker" @selection-change="onCasePickerSelectionChange">
        <AppTableColumn type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
        <AppTableColumn prop="title" variant="content" :label="t('page.functional.caseName')" />
      </PaginatedTable>
      <template #footer>
        <el-button @click="showCasePicker = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="casePickerSaving" @click="addCases">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 手工执行 Drawer -->
    <ManualRunDrawer v-model="manualDrawerVisible" :task-id="taskId" :run-id="manualRunId" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTask, updateTask, listTaskSuites, replaceTaskSuites, reorderTaskSuites, deleteTaskSuites, listTaskCases, replaceTaskCases, deleteTaskCases, pickSuites, pickFunctionalCases } from '@/api/testManagement'
import { runTask, getTaskProgress, getTaskHistory, openManualRun } from '@/api/testExecution'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useRunExecution } from '@/composables/useRunExecution'
import { RUN_STATUS_MAP, TASK_TYPE_MAP, RUN_MODE_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import ManualRunDrawer from '@/components/execution/ManualRunDrawer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const taskId = computed(() => Number(route.params.taskId))

const loading = ref(false)
const task = ref(null)
const history = ref([])
const activeTab = ref('basic')
const isManual = computed(() => task.value?.type === 'manual' || task.value?.type === 'functional')

// Shared: run execution
const { running, activeRun, progress, isRunning, run, stopRun, resumePolling } = useRunExecution({
  triggerFn: runTask,
  progressFn: getTaskProgress,
  getRunId: (r) => r.task_run_id ?? r.run_id ?? r.id,
  onStarted: () => { activeTab.value = 'history'; load(true); loadHistory() },
  onTick: () => { loadHistory() },
  onComplete: () => { loadHistory(); load(true) },
})

// Navigate to report page
function viewReport(row) {
  router.push(`/test/tasks/${taskId.value}/report/${row.id}`)
}

// Suites
const taskSuites = ref([])
const selectedSuiteIds = ref([])

// Cases (manual/functional)
const taskCases = ref([])
const selectedCaseIds = ref([])

// Edit
const showEdit = ref(false)
const editSaving = ref(false)
const editForm = reactive({ task_name: '', description: '', environment_id: null, run_mode: 'serial' })

// Suite picker
const showSuitePicker = ref(false)
const suitePickerSearch = ref('')
const suitePickerItems = ref([])
const suitePickerLoading = ref(false)
const suitePickerSaving = ref(false)
const suitePickerSelected = ref([])
const suitePickerTableRef = ref(null)
const { page: spPage, pageSize: spPageSize, total: suitePickerTotal } = usePagination()

// Computed: suite names for history display
const suiteNamesDisplay = computed(() => {
  return taskSuites.value.map(s => s.suite_name).join('、') || '-'
})

// Case picker
const showCasePicker = ref(false)
const casePickerSearch = ref('')
const casePickerItems = ref([])
const casePickerLoading = ref(false)
const casePickerSaving = ref(false)
const casePickerSelected = ref([])
const { page: cpPage, pageSize: cpPageSize, total: casePickerTotal } = usePagination()

// Manual run
const manualDrawerVisible = ref(false)
const manualRunId = ref(null)

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
  if (!taskId.value || Number.isNaN(taskId.value)) return
  if (!silent) loading.value = true
  try {
    const [tRes, hRes] = await Promise.all([getTask(taskId.value), getTaskHistory(taskId.value)])
    task.value = tRes.data.data
    history.value = hRes.data.data?.items ?? hRes.data.data ?? []
    recoverRunningState()
    isManual.value ? await loadTaskCases() : await loadTaskSuites()
  } finally { if (!silent) loading.value = false }
}

async function loadHistory() {
  if (!taskId.value || Number.isNaN(taskId.value)) return
  try {
    var res = await getTaskHistory(taskId.value)
    history.value = res.data.data?.items ?? res.data.data ?? []
    recoverRunningState()
  } catch (e) {
    // silent
  }
}

async function loadTaskSuites() { var res = await listTaskSuites(taskId.value); taskSuites.value = res.data.data?.items ?? res.data.data ?? [] }
async function loadTaskCases() { var res = await listTaskCases(taskId.value); taskCases.value = res.data.data?.items ?? res.data.data ?? [] }

// --- Edit ---
function openEdit() {
  Object.assign(editForm, {
    task_name: task.value.task_name,
    description: task.value.description || '',
    environment_id: task.value.environment_id,
    run_mode: task.value.run_mode || 'serial',
  })
  showEdit.value = true
}
async function saveEdit() { editSaving.value = true; try { await updateTask(taskId.value, editForm); ElMessage.success(t('common.saved')); showEdit.value = false; load() } finally { editSaving.value = false } }

// --- Suites ---
function onSuiteSelectionChange(rows) { selectedSuiteIds.value = rows.map((r) => r.suite_id) }
async function removeSuite(row) { await deleteTaskSuites(taskId.value, { suite_ids: [row.suite_id] }); ElMessage.success(t('common.deleted')); loadTaskSuites() }
async function batchRemoveSuites() { try { await ElMessageBox.confirm(t('common.batchDeleteConfirm', { count: selectedSuiteIds.value.length }), t('common.warning'), { type: 'warning' }); await deleteTaskSuites(taskId.value, { suite_ids: selectedSuiteIds.value }); selectedSuiteIds.value = []; loadTaskSuites() } catch (e) { if (e !== 'cancel') ElMessage.error(e.message) } }
async function moveSuite(row, dir) { var ids = taskSuites.value.map((s) => s.suite_id); var idx = ids.indexOf(row.suite_id); var ni = idx + dir; if (ni < 0 || ni >= ids.length) return; [ids[idx], ids[ni]] = [ids[ni], ids[idx]]; await reorderTaskSuites(taskId.value, { ordered_suite_ids: ids }); loadTaskSuites() }

// --- Cases ---
function onCaseSelectionChange(rows) { selectedCaseIds.value = rows.map((r) => r.case_id) }
async function removeCase(row) { await deleteTaskCases(taskId.value, { case_ids: [row.case_id] }); ElMessage.success(t('common.deleted')); loadTaskCases() }
async function batchRemoveCases() { try { await ElMessageBox.confirm(t('common.batchDeleteConfirm', { count: selectedCaseIds.value.length }), t('common.warning'), { type: 'warning' }); await deleteTaskCases(taskId.value, { case_ids: selectedCaseIds.value }); selectedCaseIds.value = []; loadTaskCases() } catch (e) { if (e !== 'cancel') ElMessage.error(e.message) } }

// --- Suite picker ---
const existingSuiteIds = computed(() => new Set(taskSuites.value.map(s => s.suite_id)))

function openSuitePicker() { showSuitePicker.value = true; loadSuitePicker() }
async function loadSuitePicker() {
  if (!task.value?.project_id) return
  suitePickerLoading.value = true
  try {
    var res = await pickSuites({ project_id: task.value.project_id, q: suitePickerSearch.value || undefined, page: spPage.value, page_size: spPageSize.value })
    suitePickerItems.value = res.data.data?.items ?? []
    suitePickerTotal.value = res.data.data?.total ?? 0
    // Pre-select already-associated suites
    await nextTick()
    var tableRef = suitePickerTableRef.value?.tableRef
    if (tableRef) {
      suitePickerItems.value.forEach(row => {
        tableRef.toggleRowSelection(row, existingSuiteIds.value.has(row.id))
      })
    }
  } finally { suitePickerLoading.value = false }
}
function onSuitePickerSelectionChange(rows) { suitePickerSelected.value = rows.map((r) => r.id) }
async function addSuites() {
  if (!suitePickerSelected.value.length) return
  suitePickerSaving.value = true
  try {
    var all = taskSuites.value.map((s) => s.suite_id).concat(suitePickerSelected.value.filter(id => !existingSuiteIds.value.has(id)))
    await replaceTaskSuites(taskId.value, { suite_ids: all })
    ElMessage.success(t('common.saved'))
    showSuitePicker.value = false
    suitePickerSelected.value = []
    loadTaskSuites()
  } finally { suitePickerSaving.value = false }
}

// --- Case picker ---
function openCasePicker() { showCasePicker.value = true; loadCasePicker() }
async function loadCasePicker() { if (!task.value?.project_id) return; casePickerLoading.value = true; try { var res = await pickFunctionalCases({ project_id: task.value.project_id, q: casePickerSearch.value || undefined, page: cpPage.value, page_size: cpPageSize.value }); casePickerItems.value = res.data.data?.items ?? []; casePickerTotal.value = res.data.data?.total ?? 0 } finally { casePickerLoading.value = false } }
function onCasePickerSelectionChange(rows) { casePickerSelected.value = rows.map((r) => r.id) }
async function addCases() { if (!casePickerSelected.value.length) return; casePickerSaving.value = true; try { var all = taskCases.value.map((c) => c.case_id).concat(casePickerSelected.value); await replaceTaskCases(taskId.value, { case_ids: all }); ElMessage.success(t('common.saved')); showCasePicker.value = false; casePickerSelected.value = []; loadTaskCases() } finally { casePickerSaving.value = false } }

// --- Manual run ---
async function startManualRun() { try { var res = await openManualRun(taskId.value); manualRunId.value = res.data.data?.task_run_id ?? res.data.data?.id; manualDrawerVisible.value = true } catch (e) { ElMessage.error(e.message) } }

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
    await run(taskId.value)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  }
}

onMounted(load)
</script>

<style lang="scss" scoped>
.task-detail-view {
  position: relative;
}
.task-actions {
  position: absolute;
  top: 87px;
  right: 16px;
  z-index: 2;
}
</style>
