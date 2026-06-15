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
        <el-input v-model="filters.q" :placeholder="t('common.keyword')" clearable />
        <el-select v-model="filters.status" :placeholder="t('common.status')" clearable>
          <el-option v-for="s in DEFECT_STATUS" :key="s" :label="t(`defect.status.${s}`)" :value="s" />
        </el-select>
        <el-select v-model="filters.severity" :placeholder="t('page.defects.severity')" clearable>
          <el-option v-for="s in DEFECT_SEVERITY" :key="s" :label="s" :value="s" />
        </el-select>
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" row-key="id" @page-change="load" @selection-change="onSelectionChange">
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="title" variant="content" :label="t('page.defects.title')" />
        <AppTableColumn variant="fixed" :label="t('common.status')" :width="120">
          <template #default="{ row }"><DefectStatusTag :status="row.status" /></template>
        </AppTableColumn>
        <AppTableColumn prop="severity" variant="fixed" :label="t('page.defects.severity')" :width="100" />
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/defects/${row.id}`)">{{ t('common.view') }}</el-button>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <el-dialog v-model="showCreate" :title="t('page.defects.create')" width="480px">
      <el-form label-width="100px">
        <el-form-item :label="t('page.defects.title')"><el-input v-model="createForm.title" /></el-form-item>
        <el-form-item :label="t('page.defects.severity')">
          <el-select v-model="createForm.severity"><el-option v-for="s in DEFECT_SEVERITY" :key="s" :label="s" :value="s" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="create">{{ t('common.save') }}</el-button>
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
import { DEFECT_SEVERITY, DEFECT_STATUS } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ q: '', status: '', severity: '' })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const createForm = reactive({ title: '', severity: DEFECT_SEVERITY[0], priority: '?' })
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    var res = await batchDeleteDefects(selectedIds.value)
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

async function load() {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    q: filters.q || undefined,
    status: filters.status || undefined,
    severity: filters.severity || undefined,
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
  Object.assign(filters, { q: '', status: '', severity: '' })
  page.value = 1
  load()
}

async function create() {
  const params = withProjectParams()
  await createDefect({ ...createForm, project_id: params.project_id })
  ElMessage.success(t('common.saved'))
  showCreate.value = false
  load()
}

onMounted(load)
</script>
