<template>
  <div class="task-list-view app-card">
    <PageHeader :title="t('page.test.tasks.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.q" :placeholder="t('common.keyword')" clearable style="width: 200px" />
        <el-select v-model="filters.type" :placeholder="t('page.test.taskType')" clearable style="width: 140px">
          <el-option v-for="tt in TASK_TYPES" :key="tt" :label="TASK_TYPE_MAP[tt]?.label || tt" :value="tt" />
        </el-select>
        <el-select v-model="filters.status" :placeholder="t('page.test.execStatus')" clearable style="width: 140px">
          <el-option v-for="s in RUN_STATUS" :key="s" :label="RUN_STATUS_MAP[s]?.label || s" :value="s" />
        </el-select>
        <el-select v-model="filters.result" :placeholder="t('page.test.execResult')" clearable style="width: 120px">
          <el-option value="success" :label="t('page.test.resultSuccess')" />
          <el-option value="fail" :label="t('page.test.resultFail')" />
        </el-select>
        <el-input v-model="filters.triggered_by" :placeholder="t('page.test.executor')" clearable style="width: 140px" />
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" row-key="id" @page-change="load" @selection-change="onSelectionChange">
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="task_name" variant="content" :label="t('page.test.tasks.taskName')">
          <template #default="{ row }"><el-button link type="primary" @click="router.push(`/test/tasks/${row.id}`)">{{ row.task_name }}</el-button></template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.test.taskType')" :width="80">
          <template #default="{ row }"><el-tag :type="TASK_TYPE_MAP[row.type]?.type" size="small">{{ TASK_TYPE_MAP[row.type]?.label || row.type }}</el-tag></template>
        </AppTableColumn>
        <AppTableColumn prop="case_count" variant="fixed" :label="t('page.test.caseCount')" :width="80" />
        <AppTableColumn variant="fixed" :label="t('page.test.execStatus')" :width="100">
          <template #default="{ row }"><StatusTag :status="row.last_run?.status" :map="RUN_STATUS_MAP" /></template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.test.execResult')" :width="80">
          <template #default="{ row }">
            <template v-if="getExecResult(row)">
              <el-tag :type="getExecResult(row) === 'success' ? 'success' : 'danger'" size="small">{{ getExecResult(row) === 'success' ? t('page.test.resultSuccess') : t('page.test.resultFail') }}</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.test.successRate')" :width="140">
          <template #default="{ row }">{{ row.last_run?.success_rate || '-' }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.test.executor')" :width="100">
          <template #default="{ row }">{{ row.last_run?.triggered_by_name || '-' }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.test.lastRun')" :width="170">
          <template #default="{ row }">{{ row.last_run?.start_time ? formatTime(row.last_run.start_time) : '-' }}</template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/tasks/${row.id}`)">{{ t('common.view') }}</el-button>
            <el-button v-if="canEdit && isRowRunning(row)" link type="danger" @click="stopTaskRow(row)">{{ t('page.test.stopRun') }}</el-button>
            <el-button v-else-if="canEdit && row.type !== 'manual' && row.type !== 'functional'" link type="primary" @click="runTaskRow(row)">{{ t('page.test.run') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <!-- 新建任务对话框 -->
    <TaskCreateDialog v-model="showCreate" :project-id="projectId" @saved="load" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listTasks, deleteTask, batchDeleteTasks } from '@/api/testManagement'
import { runTask, getTaskProgress, cancelRun } from '@/api/testExecution'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { usePolling } from '@/composables/usePolling'
import { RUN_STATUS, RUN_STATUS_MAP, TASK_TYPES, TASK_TYPE_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import TaskCreateDialog from '@/components/test-management/TaskCreateDialog.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ q: '', type: '', status: '', result: '', triggered_by: '' })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

function openCreate() {
  showCreate.value = true
}

// --- Run/Stop execution (mirrors SuiteListView) ---
const activeRunId = ref(null)
const runningTaskId = ref(null)
let listPolling = null
let listPollDone = false

function isRowRunning(row) {
  return runningTaskId.value === row.id
}

async function stopTaskRow(row) {
  if (!activeRunId.value) return
  try {
    await cancelRun(activeRunId.value)
    ElMessage.success(t('page.test.runStopped'))
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  } finally {
    runningTaskId.value = null
    activeRunId.value = null
    if (listPolling) { listPolling.stop(); listPolling = null }
    load()
  }
}

async function runTaskRow(row) {
  try {
    var res = await runTask(row.id)
    ElMessage.success(t('page.test.runStarted'))
    runningTaskId.value = row.id
    activeRunId.value = res.data.data?.task_run_id ?? res.data.data?.run_id ?? res.data.data?.id ?? null
    load()
    if (activeRunId.value) {
      if (listPolling) listPolling.stop()
      listPollDone = false
      listPolling = usePolling(async () => {
        var pRes = await getTaskProgress(activeRunId.value)
        load(true)
        if (!['running', 'pending'].includes(pRes.data.data?.status)) {
          listPollDone = true
          runningTaskId.value = null
          activeRunId.value = null
        }
      }, { interval: 2500, until: () => listPollDone })
      listPolling.start()
    }
  } catch (e) {
    runningTaskId.value = null
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  }
}

function getExecResult(row) {
  var run = row.last_run
  if (!run || !run.status) return null
  if (run.status === 'failed') return 'fail'
  if (run.status === 'completed') {
    if (run.total_cases > 0 && run.passed_cases < run.total_cases) return 'fail'
    if (run.total_cases > 0 && run.passed_cases === run.total_cases) return 'success'
    return 'success'
  }
  return null
}

// --- Data loading ---
async function load(silent) {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    q: filters.q || undefined,
    type: filters.type || undefined,
    status: filters.status || undefined,
    result: filters.result || undefined,
    triggered_by: filters.triggered_by || undefined,
  })
  if (!params) return
  if (!silent) loading.value = true
  try {
    const res = await listTasks(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
    // Recover running state on page load
    if (!runningTaskId.value) {
      var runningItem = items.value.find(function (item) {
        return item.last_run && ['running', 'pending'].includes(item.last_run.status)
      })
      if (runningItem) {
        runningTaskId.value = runningItem.id
        activeRunId.value = runningItem.last_run.run_id ?? null
        if (activeRunId.value && !listPolling) {
          listPollDone = false
          listPolling = usePolling(async () => {
            var pRes = await getTaskProgress(activeRunId.value)
            load(true)
            if (!['running', 'pending'].includes(pRes.data.data?.status)) {
              listPollDone = true
              runningTaskId.value = null
              activeRunId.value = null
            }
          }, { interval: 2500, until: () => listPollDone })
          listPolling.start()
        }
      }
    }
  } finally {
    if (!silent) loading.value = false
  }
}

function reset() {
  filters.q = ''; filters.type = ''; filters.status = ''; filters.result = ''; filters.triggered_by = ''
  page.value = 1
  load()
}

async function remove(row) {
  await deleteTask(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    var res = await batchDeleteTasks(selectedIds.value)
    var data = res.data.data
    selectedIds.value = []
    if (data && data.failures && data.failures.length) {
      ElMessage.warning(t('common.batchDeletePartial'))
    } else if (data && data.deleted_ids && data.deleted_ids.length) {
      ElMessage.success(t('common.batchDeleteSuccess', { count: data.deleted_ids.length }))
    }
    load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

onMounted(load)
onUnmounted(function () {
  if (listPolling) { listPolling.stop(); listPolling = null }
})
</script>
