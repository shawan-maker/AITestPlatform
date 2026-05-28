<template>
  <div class="defect-list-view app-card">
    <PageHeader :title="t('page.defects.title')">
      <template #actions>
        <el-button v-if="canEdit && projectId" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <el-input v-model="filters.q" :placeholder="t('common.keyword')" clearable style="width: 160px" />
        <el-select v-model="filters.status" :placeholder="t('common.status')" clearable style="width: 140px">
          <el-option v-for="s in DEFECT_STATUS" :key="s" :label="t(`defect.status.${s}`)" :value="s" />
        </el-select>
        <el-select v-model="filters.severity" :placeholder="t('page.defects.severity')" clearable style="width: 120px">
          <el-option v-for="s in DEFECT_SEVERITY" :key="s" :label="s" :value="s" />
        </el-select>
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" @page-change="load">
        <el-table-column prop="title" :label="t('page.defects.title')" />
        <el-table-column :label="t('common.status')" width="120">
          <template #default="{ row }"><DefectStatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column prop="severity" :label="t('page.defects.severity')" width="100" />
        <el-table-column :label="t('common.actions')" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/defects/${row.id}`)">{{ t('common.view') }}</el-button>
          </template>
        </el-table-column>
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
import { ElMessage } from 'element-plus'
import { createDefect, listDefects } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { DEFECT_SEVERITY, DEFECT_STATUS } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
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
const createForm = reactive({ title: '', severity: DEFECT_SEVERITY[0], priority: '中' })

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
