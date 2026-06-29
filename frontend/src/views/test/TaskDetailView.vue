<template>
  <div v-loading="loading" class="task-detail-view app-card">
    <PageHeader :title="task?.task_name || t('page.test.tasks.title')" />

    <div class="task-actions">
      <el-button @click="router.push('/test/tasks')">{{ t('common.back') }}</el-button>
      <el-button v-if="canEdit" @click="openEdit">{{ t('common.edit') }}</el-button>
      <el-button v-if="canEdit && isRunning && !isManual" type="danger" @click="stopRun">{{ t('page.test.stopRun') }}</el-button>
      <el-button v-else-if="canEdit && !isManual" type="primary" :loading="running" @click="run(taskId)">{{ t('page.test.run') }}</el-button>
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
          <AppTableColumn prop="case_no" variant="fixed" :label="t('page.functional.caseNo')" :width="130" />
          <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" />
          <AppTableColumn variant="fixed" :label="t('page.functional.priority')" :width="80">
            <template #default="{ row }">
              <PriorityTag v-if="row.priority" :value="row.priority" />
              <span v-else>-</span>
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.functional.caseCategory')" :width="100">
            <template #default="{ row }">
              {{ row.case_category ? t('page.functional.cat' + row.case_category.charAt(0).toUpperCase() + row.case_category.slice(1)) : '-' }}
            </template>
          </AppTableColumn>
          <AppTableColumn prop="module_name" variant="fixed" :label="t('page.knowledge.module')" :width="120">
            <template #default="{ row }">{{ row.module_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="100">
            <template #default="{ row }">
              <ConfirmDelete @confirm="removeCase(row)"><el-button link type="danger">{{ t('common.delete') }}</el-button></ConfirmDelete>
            </template>
          </AppTableColumn>
        </AppTable>
      </el-tab-pane>

      <!-- 执行记录 (手工任务) -->
      <el-tab-pane v-if="isManual" :label="t('page.test.execRecords')" name="records">
        <!-- Inline execution layout (auto-shown when manual run is active) -->
        <div v-if="manualRunId && execTree.length" class="exec-layout">
          <div class="exec-left">
            <el-tree :data="execTree" node-key="id" :props="{ label: 'name', children: 'children' }" highlight-current @node-click="onCatalogNodeClick" />
          </div>
          <div class="exec-right">
            <el-table :data="filteredExecCases" size="small" border>
              <el-table-column prop="case_no" variant="fixed" :label="t('page.functional.caseNo')" :width="130" show-overflow-tooltip />
              <el-table-column prop="case_name" variant="content" :label="t('page.functional.caseName')" min-width="150" show-overflow-tooltip />
              <el-table-column variant="fixed" :label="t('page.functional.priority')" :width="70">
                <template #default="{ row }">
                  <PriorityTag v-if="row.priority" :value="row.priority" />
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('page.functional.caseCategory')" :width="80">
                <template #default="{ row }">
                  {{ row.case_category ? t('page.functional.cat' + row.case_category.charAt(0).toUpperCase() + row.case_category.slice(1)) : '-' }}
                </template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('page.knowledge.module')" :width="100">
                <template #default="{ row }">{{ execModuleMap[row.module_id] || '-' }}</template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('page.test.execResult')" :width="90">
                <template #default="{ row }">
                  <el-tag v-if="row.exec_result && row.exec_result !== 'pending'" :type="execResultType(row.exec_result)" size="small">{{ execResultLabel(row.exec_result) }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('execution.linkDefect')" :width="110">
                <template #default="{ row }">{{ row.defect_code || '-' }}</template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('page.test.executor')" :width="90">
                <template #default="{ row }">{{ row.triggered_by_name || '-' }}</template>
              </el-table-column>
              <el-table-column variant="fixed" :label="t('page.test.execTime')" :width="150">
                <template #default="{ row }">{{ row.exec_time ? formatTime(row.exec_time) : '-' }}</template>
              </el-table-column>
              <el-table-column actions variant="fixed" :label="t('common.actions')" :width="150">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openMarkDrawer(row)">{{ t('page.test.markResult') }}</el-button>
                  <el-button v-if="row.exec_result === 'failed'" link type="danger" @click="openDefectDialog(row)">{{ t('execution.linkDefect') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
        <el-empty v-else-if="manualRunId" :description="t('page.test.tabCases') + ' - ' + t('page.defects.noComments')" :image-size="60" />
        <el-skeleton v-else :rows="6" animated />
      </el-tab-pane>

      <!-- 执行历史 (API任务) -->
      <el-tab-pane v-else :label="t('page.test.tabHistory')" name="history">
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

    <!-- 用例选择器 (手工任务 - 目录树+列表) -->
    <FunctionalCasePickerDialog
      v-model="showCasePicker"
      :project-id="task?.project_id"
      :pre-selected-ids="[...existingCaseIds]"
      :pre-selected-case-map="existingCaseMap"
      @confirmed="onCasePickerConfirmed"
    />

    <!-- 手工执行 Drawer (保留用于兼容性) -->
    <ManualRunDrawer v-model="manualDrawerVisible" :task-id="taskId" :run-id="manualRunId" />

    <!-- 用例标记 Drawer -->
    <el-drawer v-model="markDrawerVisible" :title="markCase?.case_name || t('page.test.markResult')" size="55%">
      <div v-if="markCaseDetail" class="mark-drawer-body">
        <!-- 用例基本信息 (from full case detail) -->
        <section v-if="markCaseFullDetail" class="mark-section">
          <h4 class="mark-section-title">{{ t('page.functional.basicInfo') }}</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="t('page.functional.caseNo')">{{ markCaseFullDetail.case_no || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.functional.caseName')">{{ markCaseFullDetail.case_name }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.functional.priority')">
              <PriorityTag :value="markCaseFullDetail.priority" />
            </el-descriptions-item>
            <el-descriptions-item :label="t('page.functional.caseCategory')">
              {{ markCaseFullDetail.case_category ? t('page.functional.cat' + markCaseFullDetail.case_category.charAt(0).toUpperCase() + markCaseFullDetail.case_category.slice(1)) : '-' }}
            </el-descriptions-item>
            <el-descriptions-item v-if="markCaseFullDetail.dimension" :label="t('page.functional.dimension')">{{ markCaseFullDetail.dimension }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.knowledge.module')">{{ markCaseFullDetail.module_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.functional.source')">
              {{ markCaseFullDetail.source === 'ai' ? t('page.functional.sourceAI') : markCaseFullDetail.source === 'manual' ? t('page.functional.sourceManual') : (markCaseFullDetail.source || '-') }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <!-- 测试步骤与预期结果 -->
        <section class="mark-section">
          <h4 class="mark-section-title">{{ t('page.functional.stepsAndExpected') }}</h4>
          <div class="mark-field-block" v-if="markCaseDetail.preconditions">
            <label>{{ t('page.functional.precondition') }}</label>
            <pre class="mark-field-content">{{ markCaseDetail.preconditions }}</pre>
          </div>
          <div class="mark-field-block">
            <label>{{ t('page.functional.testSteps') }}</label>
            <pre class="mark-field-content">{{ markCaseDetail.test_steps || '-' }}</pre>
          </div>
          <div class="mark-field-block" v-if="markCaseFullDetail && markCaseFullDetail.test_data">
            <label>{{ t('page.functional.testData') }}</label>
            <pre class="mark-field-content">{{ markCaseFullDetail.test_data }}</pre>
          </div>
          <div class="mark-field-block">
            <label>{{ t('page.functional.expectedResult') }}</label>
            <pre class="mark-field-content">{{ markCaseDetail.expected_result || '-' }}</pre>
          </div>
        </section>

        <!-- 已保存的执行结果记录 (read-only, only show if previously saved) -->
        <section v-if="markSavedRecord.exec_result" class="mark-section">
          <h4 class="mark-section-title">{{ t('page.test.execResultRecord') }}</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="t('page.test.execResult')">
              <el-tag :type="execResultType(markSavedRecord.exec_result)" size="small">{{ execResultLabel(markSavedRecord.exec_result) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="markSavedRecord.remark" :label="t('page.defects.comment')">{{ markSavedRecord.remark }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.executor')">{{ markSavedRecord.triggered_by_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.execTime')">{{ markSavedRecord.exec_time ? formatTime(markSavedRecord.exec_time) : '-' }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <!-- 执行结果与备注 (editable, at bottom) -->
        <section class="mark-section">
          <h4 class="mark-section-title">{{ t('page.test.execResult') }}</h4>
          <el-form label-width="100px">
            <el-form-item :label="t('page.test.execResult')">
              <el-radio-group v-model="markForm.exec_result">
                <el-radio value="passed">{{ t('page.test.execResultPassed') }}</el-radio>
                <el-radio value="failed">{{ t('page.test.execResultFailed') }}</el-radio>
                <el-radio value="blocked">{{ t('page.test.execResultBlocked') }}</el-radio>
                <el-radio value="skipped">{{ t('page.test.execResultSkipped') }}</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="t('page.defects.comment')">
              <el-input v-model="markForm.remark" type="textarea" :rows="3" />
            </el-form-item>
          </el-form>
        </section>
      </div>
      <el-skeleton v-else :rows="4" animated />
      <template #footer>
        <el-button @click="markDrawerVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="markSaving" @click="saveMarkResult">{{ t('common.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 缺陷创建对话框 (复用 DefectCreateDialog 组件) -->
    <DefectCreateDialog
      v-model="defectDialogVisible"
      :default-title="defectDefaultTitle"
      :default-steps="defectDefaultSteps"
      :loading="defectSaving"
      @submit="saveDefect"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTask, updateTask, listTaskSuites, replaceTaskSuites, reorderTaskSuites, deleteTaskSuites, listTaskCases, replaceTaskCases, deleteTaskCases, pickSuites } from '@/api/testManagement'
import { runTask, getTaskProgress, getTaskHistory, openManualRun, getManualContext, getManualCase, patchManualCase, createDefectFromRun } from '@/api/testExecution'
import { getCase as getFunctionalCase } from '@/api/functional'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useRunExecution } from '@/composables/useRunExecution'
import { RUN_STATUS_MAP, TASK_TYPE_MAP, RUN_MODE_MAP, DEFECT_SEVERITY_MAP, DEFECT_PRIORITY_MAP, DEFECT_CATEGORY_MAP, CASE_RESULT_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import ManualRunDrawer from '@/components/execution/ManualRunDrawer.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import DefectCreateDialog from '@/components/execution/DefectCreateDialog.vue'
import FunctionalCasePickerDialog from '@/components/functional/FunctionalCasePickerDialog.vue'

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

// Case picker (uses FunctionalCasePickerDialog)
const showCasePicker = ref(false)
const casePickerSaving = ref(false)

// Manual run
const manualDrawerVisible = ref(false)
const manualRunId = ref(null)

// Inline execution state (manual tasks)
const execTree = ref([])
const execModuleMap = ref({})
const execAllCases = ref([])
const selectedCatalogId = ref(null)

const filteredExecCases = computed(() => {
  if (!selectedCatalogId.value) return execAllCases.value
  return execAllCases.value.filter(c => c.catalog_id === selectedCatalogId.value)
})

function onCatalogNodeClick(node) {
  selectedCatalogId.value = node.id || null
}

function execResultLabel(r) {
  var map = { passed: t('page.test.execResultPassed'), failed: t('page.test.execResultFailed'), blocked: t('page.test.execResultBlocked'), skipped: t('page.test.execResultSkipped') }
  return map[r] || r
}
function execResultType(r) {
  var map = { passed: 'success', failed: 'danger', blocked: 'warning', skipped: 'info' }
  return map[r] || 'info'
}

async function startManualRun() {
  try {
    var res = await openManualRun(taskId.value)
    manualRunId.value = res.data.data?.task_run_id ?? res.data.data?.id
    activeTab.value = 'records'
    await loadExecContext()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

async function loadExecContext() {
  if (!manualRunId.value) return
  try {
    var res = await getManualContext(manualRunId.value)
    var data = res.data.data
    execTree.value = data.tree || []
    execModuleMap.value = data.module_map || {}
    // Flatten cases from tree, preserving exec_result and defect_code from API
    var cases = []
    function collectCases(nodes) {
      for (var node of nodes) {
        for (var c of (node.cases || [])) {
          cases.push(Object.assign({}, c, { catalog_id: node.id }))
        }
        if (node.children) collectCases(node.children)
      }
    }
    collectCases(execTree.value)
    execAllCases.value = cases
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

// Mark result drawer
const markDrawerVisible = ref(false)
const markCase = ref(null)
const markCaseDetail = ref(null)
const markCaseFullDetail = ref(null)
const markForm = reactive({ exec_result: '', remark: '' })
const markSavedRecord = reactive({ exec_result: null, remark: null, triggered_by_name: null, exec_time: null })
const markSaving = ref(false)

async function openMarkDrawer(row) {
  markCase.value = row
  markCaseDetail.value = null
  markCaseFullDetail.value = null
  markSavedRecord.exec_result = null
  markSavedRecord.remark = null
  markSavedRecord.triggered_by_name = null
  markSavedRecord.exec_time = null
  markForm.exec_result = row.exec_result || ''
  markForm.remark = ''
  markDrawerVisible.value = true
  try {
    var res = await getManualCase(manualRunId.value, row.case_id)
    markCaseDetail.value = res.data.data
    // Store previously saved record for read-only display
    if (markCaseDetail.value.exec_result) {
      markSavedRecord.exec_result = markCaseDetail.value.exec_result
      markSavedRecord.remark = markCaseDetail.value.remark || null
      markSavedRecord.triggered_by_name = markCaseDetail.value.triggered_by_name || null
      markSavedRecord.exec_time = markCaseDetail.value.exec_time || null
    }
    // Pre-fill the editable form
    if (markCaseDetail.value.exec_result) markForm.exec_result = markCaseDetail.value.exec_result
    if (markCaseDetail.value.remark) markForm.remark = markCaseDetail.value.remark
  } catch (e) { /* case may not have detail yet */ }
  // Fetch full case detail for display (reuse FunctionalCaseDetailDrawer data)
  try {
    var fullRes = await getFunctionalCase(row.case_id)
    markCaseFullDetail.value = fullRes.data.data
  } catch (e) { /* non-critical, basic info section will be hidden */ }
}

async function saveMarkResult() {
  if (!markForm.exec_result) { ElMessage.warning(t('page.test.execResult')); return }
  markSaving.value = true
  try {
    await patchManualCase(manualRunId.value, markCase.value.case_id, { exec_result: markForm.exec_result, remark: markForm.remark || undefined })
    ElMessage.success(t('common.saved'))
    markDrawerVisible.value = false
    await loadExecContext()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  } finally {
    markSaving.value = false
  }
}

// Defect creation dialog (uses DefectCreateDialog component)
const defectDialogVisible = ref(false)
const defectDefaultTitle = ref('')
const defectDefaultSteps = ref('')
const defectSourceCaseId = ref(null)
const defectRecordId = ref(null)
const defectSaving = ref(false)

async function openDefectDialog(row) {
  defectDefaultTitle.value = row.case_name || ''
  defectSourceCaseId.value = row.case_id
  defectRecordId.value = null
  defectDefaultSteps.value = ''
  // Build steps from case detail if available
  if (markCaseDetail.value && markCase.value?.case_id === row.case_id) {
    var parts = []
    if (markCaseDetail.value.preconditions) parts.push('前置条件:\n' + markCaseDetail.value.preconditions)
    if (markCaseDetail.value.test_steps) parts.push('测试步骤:\n' + markCaseDetail.value.test_steps)
    if (markCaseDetail.value.expected_result) parts.push('预期结果:\n' + markCaseDetail.value.expected_result)
    defectDefaultSteps.value = parts.join('\n\n')
    defectRecordId.value = markCaseDetail.value.record_id || null
  } else {
    // Fetch case detail to get record_id and build steps
    try {
      var res = await getManualCase(manualRunId.value, row.case_id)
      var detail = res.data.data
      if (detail) {
        defectRecordId.value = detail.record_id || null
        var parts2 = []
        if (detail.preconditions) parts2.push('前置条件:\n' + detail.preconditions)
        if (detail.test_steps) parts2.push('测试步骤:\n' + detail.test_steps)
        if (detail.expected_result) parts2.push('预期结果:\n' + detail.expected_result)
        defectDefaultSteps.value = parts2.join('\n\n')
      }
    } catch (e) { /* non-critical */ }
  }
  defectDialogVisible.value = true
}

async function saveDefect(formData) {
  defectSaving.value = true
  try {
    await createDefectFromRun({
      title: formData.title,
      steps: formData.steps || undefined,
      severity: formData.severity,
      priority: formData.priority,
      defect_category: formData.defect_category || undefined,
      root_cause: formData.root_cause || undefined,
      assignee_id: formData.assignee_id || undefined,
      comment: formData.comment || undefined,
      project_id: task.value?.project_id,
      source_type: 'functional_case',
      source_run_id: manualRunId.value,
      source_case_id: defectSourceCaseId.value,
      functional_run_id: defectRecordId.value || undefined,
    })
    ElMessage.success(t('common.saved'))
    defectDialogVisible.value = false
    await loadExecContext()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  } finally {
    defectSaving.value = false
  }
}

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
const existingCaseIds = computed(() => new Set(taskCases.value.map(c => c.case_id)))
const existingCaseMap = computed(() => {
  var map = {}
  taskCases.value.forEach(function (c) { if (c.catalog_id) map[c.case_id] = c.catalog_id })
  return map
})

function openCasePicker() { showCasePicker.value = true }
async function onCasePickerConfirmed(selectedIds) {
  casePickerSaving.value = true
  try {
    await replaceTaskCases(taskId.value, { case_ids: selectedIds })
    ElMessage.success(t('common.saved'))
    showCasePicker.value = false
    loadTaskCases()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  } finally { casePickerSaving.value = false }
}

// --- Manual run ---
// startManualRun is defined above in the inline execution section

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

// Auto-start manual run when records tab is activated
watch(activeTab, async (tab) => {
  if (tab === 'records' && isManual.value && !manualRunId.value) {
    await startManualRun()
  }
})

onMounted(async () => {
  await load()
  // Handle query params: ?tab=records&execute=1
  if (route.query.tab) activeTab.value = route.query.tab
  // Auto-start manual run when entering a manual task's detail page
  if (isManual.value && !manualRunId.value) {
    activeTab.value = route.query.tab || 'records'
    if (activeTab.value === 'records') {
      await startManualRun()
    }
  }
})
</script>

<style lang="scss" scoped>
.task-detail-view {
  position: relative;
}
.exec-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.exec-layout {
  display: flex;
  gap: 16px;
  min-height: 400px;
}
.exec-left {
  width: 240px;
  flex-shrink: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 8px;
  overflow-y: auto;
  max-height: 600px;
}
.exec-right {
  flex: 1;
  min-width: 0;
}
.mark-drawer-body {
  padding: 0 4px;
}
.mark-section {
  margin-bottom: 20px;
}
.mark-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary, #409eff);
}
.mark-field-block {
  margin-bottom: 12px;

  label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    color: var(--el-text-color-secondary);
    margin-bottom: 4px;
  }

  .mark-field-content {
    white-space: pre-wrap;
    word-break: break-word;
    padding: 10px 12px;
    background: var(--el-fill-color-lighter, #f5f7fa);
    border-radius: 4px;
    line-height: 1.6;
    font-size: 14px;
    color: var(--el-text-color-primary);
    max-height: none;
    margin: 0;
  }
}
.task-actions {
  position: absolute;
  top: 87px;
  right: 16px;
  z-index: 2;
}
</style>
