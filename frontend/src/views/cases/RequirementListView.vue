<template>
  <div class="requirement-list-view app-card">
    <PageHeader :title="t('page.requirements.title')" />

    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />

    <template v-else>
      <!-- 筛选栏：两个 Tab 共用 -->
      <FilterBar @search="load" @reset="resetFilters">
        <template #primary>
          <el-button v-if="canEdit && activeTab === 'confirmed'" type="primary" @click="showCreate = true">
            {{ t('page.requirements.create') }}
          </el-button>
        </template>
        <el-input v-model="filters.title" :placeholder="t('page.requirements.title')" clearable style="width: 200px" />
        <ModuleSelect v-model="filters.module_id" style="width: 160px" />
        <el-select v-if="activeTab === 'confirmed'" v-model="filters.source_type" :placeholder="t('page.requirements.source')" clearable style="width: 140px">
          <el-option label="知识库学习" value="knowledge" />
          <el-option label="手工录入" value="manual" />
        </el-select>
        <UserFilterSelect v-model="filters.created_by" :placeholder="t('page.requirements.createdBy')" clearable style="width: 150px" />
      </FilterBar>

      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane :label="t('page.requirements.confirmed')" name="confirmed" />
        <el-tab-pane name="pending">
          <template #label>{{ t('page.requirements.pending') }} ({{ pendingCount }})</template>
        </el-tab-pane>
      </el-tabs>

      <PaginatedTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :data="items"
        :loading="loading"
        :total="total"
        @page-change="load"
        @size-change="load"
      >
        <AppTableColumn prop="title" variant="content" :label="t('page.requirements.title')" :min-width="180" show-overflow-tooltip />
        <AppTableColumn prop="module_name" variant="flex" :label="t('page.knowledge.module')" :min-width="100" />
        <AppTableColumn prop="source_type" variant="flex" :label="t('page.requirements.source')" :min-width="110">
          <template #default="{ row }">
            <StatusTag :type="row.source_type === 'knowledge' ? 'primary' : 'info'">
              {{ row.source_type === 'knowledge' ? t('page.requirements.sourceKnowledge') : t('page.requirements.sourceManual') }}
            </StatusTag>
          </template>
        </AppTableColumn>
        <AppTableColumn prop="created_by_username" variant="flex" :label="t('page.requirements.createdBy')" :min-width="90" />
        <AppTableColumn :prop="activeTab === 'confirmed' ? 'updated_at' : 'created_at'" variant="flex" :label="activeTab === 'confirmed' ? t('page.requirements.updatedAt') : t('page.requirements.createdAt')" :min-width="160">
          <template #default="{ row }">{{ formatTime(activeTab === 'confirmed' ? row.updated_at : row.created_at) }}</template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="240">
          <template #default="{ row }">
            <template v-if="activeTab === 'pending'">
              <el-button link type="primary" @click="openEditCandidate(row)">{{ t('page.requirements.edit') }}</el-button>
              <el-button link type="primary" @click="openConfirm(row)">{{ t('page.requirements.confirm') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="cancelCandidate(row)">
                <el-button link type="danger">{{ t('common.cancel') }}</el-button>
              </ConfirmDelete>
            </template>
            <template v-else>
              <el-button link type="primary" @click="router.push(`/cases/requirements/${row.id}/view`)">{{ t('common.view') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="removeRequirement(row)">
                <el-button link type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </template>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <!-- 候选确认对话框 -->
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

    <!-- 手工新增需求（已确认 Tab） -->
    <el-dialog
      v-model="showCreate"
      :title="t('page.requirements.create')"
      :width="dialogWidth"
      :top="dialogTop"
      :class="dialogClass"
    >
      <div class="create-form-project-hint">
        {{ t('page.requirements.currentProject') }}：<strong>{{ currentProjectName || '-' }}</strong>
      </div>
      <el-form label-width="80px">
        <el-form-item :label="t('page.requirements.title')"><el-input v-model="createForm.title" maxlength="255" show-word-limit /></el-form-item>
        <el-form-item :label="t('page.knowledge.module')" required><ModuleSelect v-model="createForm.module_id" /></el-form-item>
        <el-form-item :label="t('page.requirements.description')" required>
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="textareaRows"
            :style="{ maxHeight: `${bodyMaxHeight}px` }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createReq">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑候选需求（待确认 Tab） -->
    <el-dialog
      v-model="showEditCandidate"
      :title="t('page.requirements.editTitle')"
      :width="dialogWidth"
      :top="dialogTop"
      :class="dialogClass"
    >
      <div class="create-form-project-hint">
        {{ t('page.requirements.currentProject') }}：<strong>{{ currentProjectName || '-' }}</strong>
      </div>
      <el-form v-loading="editLoading" label-width="80px">
        <el-form-item :label="t('page.requirements.title')">
          <el-input v-model="editForm.title" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('page.knowledge.module')"><ModuleSelect v-model="editForm.module_id" /></el-form-item>
        <el-form-item :label="t('page.requirements.description')">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="textareaRows"
            :style="{ maxHeight: `${bodyMaxHeight}px` }"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditCandidate = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="editing" @click="saveEditCandidate">{{ t('page.requirements.savePending') }}</el-button>
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
  updateCandidate,
} from '@/api/functional'
import { getVersionTextPreview } from '@/api/knowledge'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import UserFilterSelect from '@/components/picker/UserFilterSelect.vue'
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

function formatTime(val) {
  return val ? formatDateTime(val) : '-'
}

// 项目名称展示
const currentProjectName = ref('')

onMounted(async () => {
  try {
    const mod = await import('@/stores/project')
    const useProjectStore = mod.default || (mod.useProjectStore && (() => mod.useProjectStore()))
    if (useProjectStore) {
      const store = useProjectStore()
      currentProjectName.value = store.currentProject?.name || ''
    }
  } catch { /* ignore */ }
})

const activeTab = ref('confirmed')
const filters = reactive({ title: '', module_id: null, source_type: null, created_by: null })
const items = ref([])
const loading = ref(false)
const pendingCount = ref(0)

// 确认相关
const showConfirm = ref(false)
const selectedCandidate = ref(null)
const confirming = ref(false)

// 新增需求（已确认 Tab）
const showCreate = ref(false)
const createForm = reactive({ title: '', description: '', module_id: null })

// 编辑候选（待确认 Tab）
const showEditCandidate = ref(false)
const editing = ref(false)
const editLoading = ref(false)
const editTargetId = ref(null)
const editForm = reactive({ title: '', description: '', module_id: null })

async function loadPendingCount() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCandidatesCount(params)
  pendingCount.value = res.data.data?.count ?? res.data.data ?? 0
}

async function load() {
  const base = withProjectParams({ page: page.value, page_size: pageSize.value })
  if (!base) return
  loading.value = true
  try {
    if (activeTab.value === 'pending') {
      const res = await listCandidates({
        ...base,
        title: filters.title || undefined,
        module_id: filters.module_id || undefined,
        created_by: filters.created_by || undefined,
      })
      items.value = res.data.data?.items ?? []
      total.value = res.data.data?.total ?? 0
    } else {
      const res = await listRequirements({
        ...base,
        title: filters.title || undefined,
        module_id: filters.module_id || undefined,
        source_type: filters.source_type || undefined,
        created_by: filters.created_by || undefined,
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
  filters.source_type = null
  filters.created_by = null
  page.value = 1
  load()
}

function onTabChange() {
  page.value = 1
  load()
}

// --- 候选确认流程 ---
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

// --- 已确认需求操作 ---
async function removeRequirement(row) {
  const res = await deleteRequirement(row.id)
  const linkedCount = res.data.data?.linked_case_count ?? 0
  if (linkedCount > 0) {
    ElMessage.warning(t('page.requirements.deleteLinkedHint', { count: linkedCount }))
  } else {
    ElMessage.success(t('common.deleted'))
  }
  knowledgeStore.requestRefresh()
  load()
}

async function createReq() {
  if (!createForm.module_id) {
    ElMessage.warning(t('validation.required', { field: t('page.knowledge.module') }))
    return
  }
  const params = withProjectParams()
  await createRequirement({ ...createForm, project_id: params.project_id })
  ElMessage.success(t('common.saved'))
  showCreate.value = false
  createForm.title = ''
  createForm.description = ''
  createForm.module_id = null
  load()
}

// --- 待确认候选编辑 ---
async function openEditCandidate(row) {
  try {
    const res = await getCandidate(row.id)
    const d = res.data.data
    editTargetId.value = row.id
    editForm.title = d.title || ''
    editForm.description = d.description || ''
    editForm.module_id = d.module_id || null
    showEditCandidate.value = true
    // 如果候选 description 为空，尝试从知识库版本预览加载原文
    if (!editForm.description && d.source_document_id && d.source_document_version_id) {
      editLoading.value = true
      try {
        const previewRes = await getVersionTextPreview(d.source_document_id, d.source_document_version_id)
        const text = previewRes.data.data?.text
        if (text) {
          editForm.description = text
        }
      } catch {
        // 保持已有内容或空
      } finally {
        editLoading.value = false
      }
    }
  } catch (e) {
    // fallback 用列表行数据
    editTargetId.value = row.id
    editForm.title = row.title || ''
    editForm.description = ''
    editForm.module_id = row.module_id || null
    showEditCandidate.value = true
  }
}

async function saveEditCandidate() {
  editing.value = true
  try {
    const payload = {}
    if (editForm.title !== undefined && editForm.title !== '') payload.title = editForm.title
    if (editForm.module_id !== null) payload.module_id = editForm.module_id
    if (editForm.description !== undefined) payload.description = editForm.description || ''
    await updateCandidate(editTargetId.value, payload)
    ElMessage.success(t('common.saved'))
    showEditCandidate.value = false
    load()
  } finally {
    editing.value = false
  }
}

onMounted(() => {
  loadPendingCount()
  load()
})
</script>

<style scoped lang="scss">
.requirement-list-view {
  :deep(.el-tabs) {
    flex: none;
    min-height: auto;
  }

  :deep(.paginated-table) {
    flex: none;
    overflow: visible;
  }

  :deep(.el-table) {
    --el-table-row-height: var(--table-row-height, 52px);
  }
}

.create-form-project-hint {
  margin-bottom: 16px;
  padding: 8px 12px;
  background: var(--color-primary-light, #EAF6FC);
  border-radius: var(--radius-sm, 8px);
  color: var(--text-secondary, #6B7280);
  font-size: 13px;
}
</style>
