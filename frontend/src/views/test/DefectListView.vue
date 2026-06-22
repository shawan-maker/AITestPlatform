<template>
  <div class="defect-list-view app-card">
    <PageHeader :title="t('page.defects.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.q" :placeholder="t('page.defects.searchTitle')" clearable style="width: 160px" />
        <el-input v-model="filters.id" placeholder="ID" clearable style="width: 80px" />
        <el-select v-model="filters.status" :placeholder="t('common.status')" clearable style="width: 120px">
          <el-option v-for="(cfg, val) in DEFECT_STATUS_MAP" :key="val" :label="cfg.label" :value="val" />
        </el-select>
        <el-select v-model="filters.severity" :placeholder="t('page.defects.severity')" clearable style="width: 120px">
          <el-option v-for="(label, val) in DEFECT_SEVERITY_MAP" :key="val" :label="label" :value="val" />
        </el-select>
        <el-select v-model="filters.priority" :placeholder="t('page.defects.priority')" clearable style="width: 120px">
          <el-option v-for="(label, val) in DEFECT_PRIORITY_MAP" :key="val" :label="label" :value="val" />
        </el-select>
        <el-select v-model="filters.defect_category" :placeholder="t('page.defects.category')" clearable style="width: 120px">
          <el-option v-for="(label, val) in DEFECT_CATEGORY_MAP" :key="val" :label="label" :value="val" />
        </el-select>
        <el-date-picker v-model="filters.dateRange" type="daterange" :start-placeholder="t('page.defects.submitTime')" :end-placeholder="t('page.defects.submitTime')" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 240px" />
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" row-key="id" @page-change="load" @selection-change="onSelectionChange">
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
        <AppTableColumn prop="title" variant="content" :label="t('page.defects.title')" />
        <AppTableColumn variant="fixed" :label="t('page.defects.severity')" :width="90">
          <template #default="{ row }"><el-tag :type="severityType(row.severity)" size="small">{{ DEFECT_SEVERITY_MAP[row.severity] || row.severity }}</el-tag></template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.defects.priority')" :width="80">
          <template #default="{ row }">{{ DEFECT_PRIORITY_MAP[row.priority] || row.priority }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('common.status')" :width="100">
          <template #default="{ row }"><DefectStatusTag :status="row.status" /></template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.defects.category')" :width="80">
          <template #default="{ row }">{{ DEFECT_CATEGORY_MAP[row.defect_category] || row.defect_category }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.defects.assignee')" :width="100">
          <template #default="{ row }">{{ row.assignee_name || '-' }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.defects.submitter')" :width="100">
          <template #default="{ row }">{{ row.created_by_name || '-' }}</template>
        </AppTableColumn>
        <AppTableColumn variant="fixed" :label="t('page.defects.submitTime')" :width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/defects/${row.id}`)">{{ t('common.view') }}</el-button>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <!-- 创建缺陷对话框 -->
    <el-dialog :close-on-click-modal="false" v-model="showCreate" :title="t('page.defects.create')" width="640px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.defects.title')" required>
          <el-input v-model="createForm.title" />
        </el-form-item>
        <el-form-item :label="t('page.defects.category')">
          <el-select v-model="createForm.defect_category" style="width: 100%">
            <el-option v-for="(label, val) in DEFECT_CATEGORY_MAP" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.defects.severity')">
          <el-select v-model="createForm.severity" style="width: 100%">
            <el-option v-for="(label, val) in DEFECT_SEVERITY_MAP" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.defects.priority')">
          <el-select v-model="createForm.priority" style="width: 100%">
            <el-option v-for="(label, val) in DEFECT_PRIORITY_MAP" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.defects.steps')">
          <el-input v-model="createForm.steps" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item :label="t('page.defects.rootCause')">
          <el-input v-model="createForm.root_cause" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('page.defects.assignee')">
          <UserSearchPicker v-model="createForm.assignee_id" />
        </el-form-item>
        <el-form-item :label="t('page.defects.comment')">
          <el-input v-model="createForm.comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="create">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeleteDefects, createDefect, listDefects } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { DEFECT_STATUS_MAP, DEFECT_SEVERITY_MAP, DEFECT_PRIORITY_MAP, DEFECT_CATEGORY_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ q: '', id: '', status: '', severity: '', priority: '', defect_category: '', dateRange: null })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const saving = ref(false)
const createForm = reactive({ title: '', defect_category: 'other', severity: 'normal', priority: 'medium', steps: '', root_cause: '', assignee_id: null, comment: '' })
const selectedIds = ref([])

function severityType(s) {
  if (s === 'critical') return 'danger'
  if (s === 'serious') return 'warning'
  return 'info'
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function load() {
  const params = withProjectParams({
    page: page.value, page_size: pageSize.value,
    q: filters.q || undefined,
    id: filters.id ? Number(filters.id) : undefined,
    status: filters.status || undefined,
    severity: filters.severity || undefined,
    priority: filters.priority || undefined,
    defect_category: filters.defect_category || undefined,
    created_from: filters.dateRange?.[0] || undefined,
    created_to: filters.dateRange?.[1] || undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listDefects(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() {
  Object.assign(filters, { q: '', id: '', status: '', severity: '', priority: '', defect_category: '', dateRange: null })
  page.value = 1
  load()
}

async function create() {
  if (!createForm.title?.trim()) { ElMessage.warning(t('page.defects.titleRequired')); return }
  saving.value = true
  try {
    const params = withProjectParams()
    await createDefect({ ...createForm, project_id: params.project_id })
    ElMessage.success(t('common.saved'))
    showCreate.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'), { type: 'warning' }
    )
    var res = await batchDeleteDefects(selectedIds.value)
    var data = res.data.data
    selectedIds.value = []
    if (data?.failures?.length) ElMessage.warning(t('common.batchDeletePartial'))
    else if (data?.deleted_ids?.length) ElMessage.success(t('common.batchDeleteSuccess', { count: data.deleted_ids.length }))
    load()
  } catch (e) { if (e !== 'cancel') ElMessage.error(e?.response?.data?.message || e.message) }
}

onMounted(load)
</script>
