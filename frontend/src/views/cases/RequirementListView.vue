<template>
  <div class="requirement-list-view app-card">
    <PageHeader :title="t('page.requirements.title')" />

    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />

    <template v-else>
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane :label="t('page.requirements.confirmed')" name="confirmed" />
        <el-tab-pane name="pending">
          <template #label>{{ t('page.requirements.pending') }} ({{ pendingCount }})</template>
        </el-tab-pane>
      </el-tabs>

      <FilterBar @search="load" @reset="resetFilters">
        <template #primary>
          <el-button v-if="canEdit && activeTab === 'confirmed'" type="primary" @click="showCreate = true">
            {{ t('page.requirements.create') }}
          </el-button>
        </template>
        <template v-if="activeTab === 'confirmed'">
          <el-input v-model="filters.title" :placeholder="t('page.requirements.title')" clearable />
          <ModuleSelect v-model="filters.module_id" />
        </template>
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
        <AppTableColumn prop="title" variant="content" :label="t('page.requirements.title')" />
        <AppTableColumn v-if="activeTab === 'confirmed'" prop="module_name" variant="flex" :label="t('page.knowledge.module')" :min-width="100" />
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="200">
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
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <CandidateConfirmDialog
      v-model="showConfirm"
      :candidate="selectedCandidate"
      :document-id="selectedCandidate?.source_document_id"
      :version-id="selectedCandidate?.source_document_version_id"
      :document-title="selectedCandidate?.title"
      :loading="confirming"
      @confirm="doConfirm"
      @cancel="onCancelCandidate"
    />

    <el-dialog
      v-model="showCreate"
      :title="t('page.requirements.create')"
      :width="dialogWidth"
      :top="dialogTop"
      :class="dialogClass"
    >
      <el-form label-width="80px">
        <el-form-item :label="t('page.requirements.title')"><el-input v-model="createForm.title" /></el-form-item>
        <el-form-item :label="t('page.requirements.description')">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="textareaRows"
            :style="{ maxHeight: `${bodyMaxHeight}px` }"
          />
        </el-form-item>
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
import { computed, onMounted, reactive, ref } from 'vue'
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
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import CandidateConfirmDialog from '@/components/knowledge/CandidateConfirmDialog.vue'
import { useContentDialog } from '@/composables/useContentDialog'
import { useKnowledgeStore } from '@/stores/knowledge'

const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(220)
const textareaRows = computed(() => Math.max(8, Math.floor(bodyMaxHeight.value / 24)))
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const knowledgeStore = useKnowledgeStore()
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
    knowledgeStore.requestRefresh()
    loadPendingCount()
    load()
  } finally {
    confirming.value = false
  }
}

async function onCancelCandidate() {
  if (!selectedCandidate.value) return
  await deleteCandidate(selectedCandidate.value.id)
  ElMessage.success(t('common.deleted'))
  showConfirm.value = false
  loadPendingCount()
  load()
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
  knowledgeStore.requestRefresh()
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
