<template>
  <div class="requirement-list-view app-card">
    <PageHeader :title="t('page.requirements.title')">
      <template #actions>
        <el-button v-if="canEdit && projectId && activeTab === 'confirmed'" type="primary" @click="showCreate = true">
          {{ t('page.requirements.create') }}
        </el-button>
      </template>
    </PageHeader>

    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />

    <template v-else>
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane :label="t('page.requirements.confirmed')" name="confirmed" />
        <el-tab-pane name="pending">
          <template #label>{{ t('page.requirements.pending') }} ({{ pendingCount }})</template>
        </el-tab-pane>
      </el-tabs>

      <FilterBar v-if="activeTab === 'confirmed'" @search="load" @reset="resetFilters">
        <el-input v-model="filters.title" :placeholder="t('page.requirements.title')" clearable style="width: 180px" />
        <ModuleSelect v-model="filters.module_id" style="width: 160px" />
      </FilterBar>

      <PaginatedTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :data="items"
        :loading="loading"
        :total="total"
        @page-change="load"
        @size-change="load"
      >
        <el-table-column prop="title" :label="t('page.requirements.title')" />
        <el-table-column v-if="activeTab === 'confirmed'" prop="module_name" :label="t('page.knowledge.module')" width="120" />
        <el-table-column :label="t('common.actions')" width="220">
          <template #default="{ row }">
            <template v-if="activeTab === 'pending'">
              <el-button v-if="canEdit" link type="primary" @click="openConfirm(row)">{{ t('page.requirements.confirm') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="cancelCandidate(row)">
                <el-button link type="danger">{{ t('common.cancel') }}</el-button>
              </ConfirmDelete>
            </template>
            <template v-else>
              <el-button link type="primary" @click="router.push(`/cases/requirements/${row.id}`)">{{ t('common.view') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="removeRequirement(row)">
                <el-button link type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </template>
          </template>
        </el-table-column>
      </PaginatedTable>
    </template>

    <CandidateConfirmDialog
      v-model="showConfirm"
      :candidate="selectedCandidate"
      :loading="confirming"
      @confirm="doConfirm"
    />

    <el-dialog v-model="showCreate" :title="t('page.requirements.create')" width="480px">
      <el-form label-width="80px">
        <el-form-item :label="t('page.requirements.title')"><el-input v-model="createForm.title" /></el-form-item>
        <el-form-item :label="t('page.requirements.description')"><el-input v-model="createForm.description" type="textarea" /></el-form-item>
        <el-form-item :label="t('page.knowledge.module')"><ModuleSelect v-model="createForm.module_id" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createReq">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  confirmCandidate,
  createRequirement,
  deleteCandidate,
  deleteRequirement,
  getCandidate,
  getCandidatesCount,
  listCandidates,
  listRequirements,
} from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import CandidateConfirmDialog from '@/components/knowledge/CandidateConfirmDialog.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()

const activeTab = ref('confirmed')
const filters = reactive({ title: '', module_id: null })
const items = ref([])
const loading = ref(false)
const pendingCount = ref(0)
const showConfirm = ref(false)
const selectedCandidate = ref(null)
const confirming = ref(false)
const showCreate = ref(false)
const createForm = reactive({ title: '', description: '', module_id: null })

async function loadPendingCount() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCandidatesCount(params)
  pendingCount.value = res.data.data?.count ?? res.data.data ?? 0
}

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value })
  if (!params) return
  loading.value = true
  try {
    if (activeTab.value === 'pending') {
      const res = await listCandidates(params)
      items.value = res.data.data?.items ?? []
      total.value = res.data.data?.total ?? 0
    } else {
      const res = await listRequirements({
        ...params,
        title: filters.title || undefined,
        module_id: filters.module_id || undefined,
      })
      items.value = res.data.data?.items ?? []
      total.value = res.data.data?.total ?? 0
    }
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.title = ''
  filters.module_id = null
  page.value = 1
  load()
}

function onTabChange() {
  page.value = 1
  load()
}

async function openConfirm(row) {
  const res = await getCandidate(row.id)
  selectedCandidate.value = res.data.data
  showConfirm.value = true
}

async function doConfirm(data) {
  confirming.value = true
  try {
    await confirmCandidate(selectedCandidate.value.id, data)
    ElMessage.success(t('page.requirements.confirmed'))
    showConfirm.value = false
    loadPendingCount()
    load()
  } finally {
    confirming.value = false
  }
}

async function cancelCandidate(row) {
  await deleteCandidate(row.id)
  ElMessage.success(t('common.deleted'))
  loadPendingCount()
  load()
}

async function removeRequirement(row) {
  await deleteRequirement(row.id)
  ElMessage.success(t('common.deleted'))
  load()
}

async function createReq() {
  const params = withProjectParams()
  await createRequirement({ ...createForm, project_id: params.project_id })
  ElMessage.success(t('common.saved'))
  showCreate.value = false
  load()
}

onMounted(() => {
  loadPendingCount()
  load()
})
</script>
