<template>
  <div class="functional-workspace app-card">
    <PageHeader :title="t('page.functional.title')">
      <template #actions>
        <el-button v-if="canEdit && projectId" type="primary" @click="showCreate = true">{{ t('page.functional.create') }}</el-button>
        <el-button v-if="canEdit && selectedIds.length" @click="showBatchEdit = true">{{ t('page.functional.batchEdit') }}</el-button>
        <el-button v-if="projectId" @click="exportCases">{{ t('common.export') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else>
      <template #left>
        <CatalogTree v-model="selectedCatalogId" :nodes="catalogTree" />
      </template>
      <template #right>
        <SplitView :initial-width="360">
          <template #left>
            <PaginatedTable
              :data="cases"
              :loading="loading"
              :show-pagination="false"
              row-key="id"
              @row-click="selectCase"
              @selection-change="onSelectionChange"
            >
              <el-table-column v-if="canEdit" type="selection" width="48" />
              <el-table-column prop="name" :label="t('page.functional.caseName')">
                <template #default="{ row, $index }">
                  <span
                    draggable="true"
                    class="drag-handle"
                    @dragstart="onDragStart($index)"
                    @dragover.prevent
                    @drop="onDrop($index)"
                  >⋮⋮</span>
                  {{ row.name }}
                </template>
              </el-table-column>
            </PaginatedTable>
          </template>
          <template #right>
            <el-form v-if="selectedCase" :model="caseForm" label-width="80px">
              <el-form-item :label="t('page.functional.caseName')"><el-input v-model="caseForm.name" /></el-form-item>
              <el-form-item :label="t('page.functional.steps')"><el-input v-model="caseForm.steps" type="textarea" :rows="6" /></el-form-item>
              <el-button v-if="canEdit" type="primary" @click="saveCase">{{ t('common.save') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="removeCase">
                <el-button type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </el-form>
            <EmptyState v-else :title="t('page.functional.selectCase')" />
          </template>
        </SplitView>
      </template>
    </SplitView>

    <FunctionalCaseCreateDialog
      v-model="showCreate"
      :catalogs="catalogTree"
      :default-catalog-id="selectedCatalogId"
      :loading="creating"
      @submit="createCaseItem"
    />
    <FunctionalBatchEditDialog
      v-model="showBatchEdit"
      :case-ids="selectedIds"
      :loading="batchUpdating"
      @submit="batchUpdate"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  batchUpdateCases,
  createCase,
  deleteCase,
  exportCases as exportCasesApi,
  getCase,
  getCaseCatalogTree,
  listCases,
  reorderCases,
  updateCase,
} from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import CatalogTree from '@/components/tree/CatalogTree.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import FunctionalCaseCreateDialog from '@/components/functional/FunctionalCaseCreateDialog.vue'
import FunctionalBatchEditDialog from '@/components/functional/FunctionalBatchEditDialog.vue'

const { t } = useI18n()
const route = useRoute()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { downloadFromResponse } = useDownload()

const catalogTree = ref([])
const selectedCatalogId = ref(null)
const cases = ref([])
const loading = ref(false)
const selectedCase = ref(null)
const caseForm = reactive({ name: '', steps: '' })
const showCreate = ref(false)
const showBatchEdit = ref(false)
const selectedIds = ref([])
const creating = ref(false)
const batchUpdating = ref(false)
const dragFromIndex = ref(null)

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCaseCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadCases() {
  const params = withProjectParams({ catalog_id: selectedCatalogId.value || undefined })
  if (!params) return
  loading.value = true
  try {
    const res = await listCases(params)
    cases.value = res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

async function selectCase(row) {
  const res = await getCase(row.id)
  selectedCase.value = res.data.data
  caseForm.name = selectedCase.value.name
  caseForm.steps = selectedCase.value.steps ?? ''
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

async function saveCase() {
  await updateCase(selectedCase.value.id, { name: caseForm.name, steps: caseForm.steps })
  ElMessage.success(t('common.saved'))
  loadCases()
}

async function removeCase() {
  await deleteCase(selectedCase.value.id)
  ElMessage.success(t('common.deleted'))
  selectedCase.value = null
  loadCases()
}

async function createCaseItem(form) {
  creating.value = true
  try {
    const params = withProjectParams()
    await createCase({ ...form, project_id: params.project_id })
    ElMessage.success(t('common.saved'))
    showCreate.value = false
    loadCases()
  } finally {
    creating.value = false
  }
}

async function batchUpdate(payload) {
  batchUpdating.value = true
  try {
    await batchUpdateCases(payload)
    ElMessage.success(t('common.saved'))
    showBatchEdit.value = false
    loadCases()
  } finally {
    batchUpdating.value = false
  }
}

function onDragStart(index) {
  dragFromIndex.value = index
}

async function onDrop(toIndex) {
  const from = dragFromIndex.value
  if (from == null || from === toIndex) return
  const reordered = [...cases.value]
  const [item] = reordered.splice(from, 1)
  reordered.splice(toIndex, 0, item)
  cases.value = reordered
  await reorderCases({
    catalog_id: selectedCatalogId.value,
    ordered_ids: reordered.map((c) => c.id),
  })
  dragFromIndex.value = null
}

async function exportCases() {
  const params = withProjectParams({ catalog_id: selectedCatalogId.value || undefined })
  const res = await exportCasesApi(params)
  downloadFromResponse(res, 'cases.csv')
}

watch(selectedCatalogId, loadCases)
onMounted(async () => {
  await loadTree()
  await loadCases()
  if (route.query.caseId) {
    const row = cases.value.find((c) => String(c.id) === route.query.caseId)
    if (row) selectCase(row)
  }
})
</script>

<style scoped lang="scss">
.drag-handle {
  cursor: grab;
  margin-right: 6px;
  color: var(--el-text-color-secondary);
  user-select: none;
}
</style>
