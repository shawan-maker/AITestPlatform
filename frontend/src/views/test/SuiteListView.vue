<template>
  <div class="suite-list-view app-card">
    <PageHeader :title="t('page.test.suites.title')">
      <template #actions>
        <el-button v-if="canEdit && projectId" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <el-input v-model="filters.keyword" :placeholder="t('common.keyword')" clearable style="width: 180px" />
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" @page-change="load">
        <el-table-column prop="name" :label="t('common.name')" />
        <el-table-column prop="last_run_status" :label="t('page.test.lastRun')" width="120">
          <template #default="{ row }"><StatusTag :status="row.last_run_status" :map="RUN_STATUS_MAP" /></template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="160">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/suites/${row.id}`)">{{ t('common.view') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </el-table-column>
      </PaginatedTable>
    </template>
    <el-dialog v-model="showCreate" :title="t('page.test.suites.create')" width="480px">
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
import { ElMessage } from 'element-plus'
import { createSuite, deleteSuite, listSuites } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { RUN_STATUS_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
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

onMounted(load)
</script>
