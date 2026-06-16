<template>
  <div class="suite-list-view app-card">
    <PageHeader :title="t('page.test.suites.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.keyword" :placeholder="t('common.keyword')" clearable />
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" row-key="id" @page-change="load" @selection-change="onSelectionChange">
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="name" variant="content" :label="t('common.name')" />
        <AppTableColumn variant="fixed" :label="t('page.test.lastRun')" :width="120">
          <template #default="{ row }"><StatusTag :status="row.last_run_status" :map="RUN_STATUS_MAP" /></template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/suites/${row.id}`)">{{ t('common.view') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>
    <el-dialog :close-on-click-modal="false" v-model="showCreate" :title="t('page.test.suites.create')" width="480px">
      <el-form label-width="100px">
        <el-form-item :label="t('common.name')"><el-input v-model="createForm.name" /></el-form-item>
        <el-form-item :label="t('page.apiCases.selectEnv')"><EnvironmentSelect v-model="createForm.environment_id" /></el-form-item>
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
import { batchDeleteSuites, createSuite, deleteSuite, listSuites } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { RUN_STATUS_MAP } from '@/utils/constants'
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
const filters = reactive({ keyword: '' })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const createForm = reactive({ name: '', environment_id: null })
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value, keyword: filters.keyword || undefined })
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

function reset() { filters.keyword = ''; page.value = 1; load() }

async function create() {
  const params = withProjectParams()
  await createSuite({ ...createForm, project_id: params.project_id })
  ElMessage.success(t('common.saved'))
  showCreate.value = false
  load()
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
