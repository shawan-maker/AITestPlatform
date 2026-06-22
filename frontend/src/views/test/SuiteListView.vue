<template>
  <div class="suite-list-view app-card">
    <PageHeader :title="t('page.test.suites.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.q" :placeholder="t('common.keyword')" clearable style="width: 200px" />
        <el-select v-model="filters.status" :placeholder="t('page.test.execStatus')" clearable style="width: 140px">
          <el-option v-for="s in RUN_STATUS" :key="s" :label="RUN_STATUS_MAP[s]?.label || s" :value="s" />
        </el-select>
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" row-key="id" @page-change="load" @selection-change="onSelectionChange">
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="suite_name" variant="content" :label="t('page.test.suites.suiteName')" />
        <AppTableColumn variant="fixed" :label="t('page.test.suiteType')" :width="80">
          <template #default="{ row }"><el-tag :type="SUITE_TYPE_MAP[row.type]?.type" size="small">{{ SUITE_TYPE_MAP[row.type]?.label || row.type }}</el-tag></template>
        </AppTableColumn>
        <AppTableColumn prop="case_count" variant="fixed" :label="t('page.test.caseCount')" :width="80" />
        <AppTableColumn variant="fixed" :label="t('page.test.execStatus')" :width="100">
          <template #default="{ row }"><StatusTag :status="row.last_run?.status" :map="RUN_STATUS_MAP" /></template>
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
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="140">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/suites/${row.id}`)">{{ t('common.view') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <!-- 新建/编辑套件对话框 -->
    <el-dialog :close-on-click-modal="false" v-model="showForm" :title="isEdit ? t('page.test.suites.editSuite') : t('page.test.suites.create')" width="560px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.test.suites.suiteName')" required>
          <el-input v-model="form.suite_name" />
        </el-form-item>
        <el-form-item :label="t('page.test.suiteType')">
          <el-radio-group v-model="form.type" :disabled="isEdit">
            <el-radio value="api">API</el-radio>
            <el-radio value="functional">{{ t('page.test.functionalType') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('common.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('page.apiCases.selectEnv')">
          <EnvironmentSelect v-model="form.environment_id" :disabled="isEdit" />
        </el-form-item>
        <el-form-item :label="t('page.test.runMode')">
          <el-radio-group v-model="form.run_mode">
            <el-radio value="serial">{{ t('page.test.serial') }}</el-radio>
            <el-radio value="parallel">{{ t('page.test.parallel') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeleteSuites, createSuite, deleteSuite, listSuites, updateSuite } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { RUN_STATUS, RUN_STATUS_MAP, SUITE_TYPE_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ q: '', status: '' })
const items = ref([])
const loading = ref(false)
const showForm = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = reactive({ suite_name: '', type: 'api', description: '', environment_id: null, run_mode: 'serial' })
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, { suite_name: '', type: 'api', description: '', environment_id: null, run_mode: 'serial' })
  showForm.value = true
}

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value, q: filters.q || undefined, status: filters.status || undefined })
  if (!params) return
  loading.value = true
  try {
    const res = await listSuites(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() { filters.q = ''; filters.status = ''; page.value = 1; load() }

async function save() {
  if (!form.suite_name?.trim()) {
    ElMessage.warning(t('page.test.suites.suiteNameRequired'))
    return
  }
  saving.value = true
  try {
    const params = withProjectParams()
    if (isEdit.value && editId.value) {
      await updateSuite(editId.value, { ...form, project_id: params.project_id })
    } else {
      await createSuite({ ...form, project_id: params.project_id })
    }
    ElMessage.success(t('common.saved'))
    showForm.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await deleteSuite(row.id)
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
    var res = await batchDeleteSuites(selectedIds.value)
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
</script>
