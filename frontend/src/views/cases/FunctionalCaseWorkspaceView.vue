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
    <SplitView v-else :initial-width="380" :min-width="300" :max-width="560" :drawer-title="t('page.functional.allCases')">
      <template #left>
        <FunctionalCatalogSidebar
          :catalog-nodes="catalogTree"
          :selected-catalog-id="selectedCatalogId"
          :expanded-catalog-ids="expandedCatalogIds"
          :can-edit="canEdit"
          @select-root="selectRoot"
          @select-catalog="selectCatalog"
          @toggle-expand="onToggleExpand"
          @section-command="onSectionCommand"
          @catalog-command="onCatalogCommand"
          @catalog-drop="onCatalogDrop"
        />
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
              <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="48" />
              <AppTableColumn prop="name" variant="content" :label="t('page.functional.caseName')">
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
              </AppTableColumn>
            </PaginatedTable>
          </template>
          <template #right>
            <SectionPanel v-if="selectedCase" :title="t('page.functional.caseName')">
              <el-form :model="caseForm" label-width="80px" class="detail-form">
                <el-form-item :label="t('page.functional.caseName')"><el-input v-model="caseForm.name" /></el-form-item>
                <el-form-item :label="t('page.functional.steps')"><el-input v-model="caseForm.steps" type="textarea" :rows="6" /></el-form-item>
              </el-form>
              <FormActionBar v-if="canEdit" :saving="caseSaving" @save="saveCase" @cancel="cancelCaseEdit" />
              <div v-if="canEdit" class="case-delete">
                <ConfirmDelete @confirm="removeCase">
                  <el-button type="danger">{{ t('common.delete') }}</el-button>
                </ConfirmDelete>
              </div>
            </SectionPanel>
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
    <CatalogMoveDialog
      v-model="showMoveDialog"
      :catalog-nodes="catalogTree"
      :exclude-catalog-id="moveCatalogId"
      :dialog-title="t('page.functional.moveCatalog')"
      :hint="t('page.functional.moveCatalogPrompt')"
      :loading="moveLoading"
      @confirm="confirmMoveCatalog"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchUpdateCases,
  createCase,
  createCaseCatalog,
  deleteCase,
  deleteCaseCatalog,
  exportCases as exportCasesApi,
  getCase,
  getCaseCatalogTree,
  listCases,
  moveCaseCatalog,
  reorderCases,
  updateCase,
  updateCaseCatalog,
} from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import SectionPanel from '@/components/common/SectionPanel.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import FunctionalCaseCreateDialog from '@/components/functional/FunctionalCaseCreateDialog.vue'
import FunctionalBatchEditDialog from '@/components/functional/FunctionalBatchEditDialog.vue'
import FunctionalCatalogSidebar from '@/components/tree/FunctionalCatalogSidebar.vue'
import CatalogMoveDialog from '@/components/tree/CatalogMoveDialog.vue'

const { t } = useI18n()
const route = useRoute()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { downloadFromResponse } = useDownload()

const catalogTree = ref([])
const selectedCatalogId = ref(null)
const expandedCatalogIds = ref([])
const cases = ref([])
const loading = ref(false)
const selectedCase = ref(null)
const caseForm = reactive({ name: '', steps: '' })
const caseSnapshot = ref(null)
const caseSaving = ref(false)
const showCreate = ref(false)
const showBatchEdit = ref(false)
const selectedIds = ref([])
const creating = ref(false)
const batchUpdating = ref(false)
const dragFromIndex = ref(null)

const showMoveDialog = ref(false)
const moveCatalogId = ref(null)
const moveLoading = ref(false)

function findCatalogNode(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node
    if (node.children?.length) {
      const found = findCatalogNode(node.children, id)
      if (found) return found
    }
  }
  return null
}

function getSiblingList(nodes, parentId) {
  if (parentId == null) return nodes
  return findCatalogNode(nodes, parentId)?.children ?? []
}

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getCaseCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadCases() {
  const params = withProjectParams({
    catalog_id: selectedCatalogId.value || undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listCases(params)
    cases.value = res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

function selectRoot() {
  selectedCatalogId.value = null
  selectedCase.value = null
  loadCases()
}

function selectCatalog(catalogId) {
  selectedCatalogId.value = catalogId
  selectedCase.value = null
  loadCases()
}

function onToggleExpand(catalogId) {
  const idx = expandedCatalogIds.value.indexOf(catalogId)
  if (idx >= 0) {
    expandedCatalogIds.value = expandedCatalogIds.value.filter((id) => id !== catalogId)
  } else {
    expandedCatalogIds.value = [...expandedCatalogIds.value, catalogId]
  }
}

async function selectCase(row) {
  const res = await getCase(row.id)
  selectedCase.value = res.data.data
  caseForm.name = selectedCase.value.name
  caseForm.steps = selectedCase.value.steps ?? ''
  caseSnapshot.value = { name: caseForm.name, steps: caseForm.steps }
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

function cancelCaseEdit() {
  if (!caseSnapshot.value) return
  caseForm.name = caseSnapshot.value.name
  caseForm.steps = caseSnapshot.value.steps
}

async function saveCase() {
  caseSaving.value = true
  try {
    await updateCase(selectedCase.value.id, { name: caseForm.name, steps: caseForm.steps })
    ElMessage.success(t('common.saved'))
    caseSnapshot.value = { name: caseForm.name, steps: caseForm.steps }
    loadCases()
  } finally {
    caseSaving.value = false
  }
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
    loadTree()
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

async function createCat(parentId = null) {
  const params = withProjectParams()
  if (!params) return
  const { value } = await ElMessageBox.prompt(t('page.functional.catalogName'), t('page.functional.addCatalog'))
  if (!value?.trim()) return
  await createCaseCatalog({ name: value.trim(), parent_id: parentId ?? undefined }, params)
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function renameCat(catalog) {
  const { value } = await ElMessageBox.prompt(t('page.functional.catalogName'), t('page.functional.renameCatalog'), {
    inputValue: catalog.name,
  })
  if (!value?.trim() || value.trim() === catalog.name) return
  await updateCaseCatalog(catalog.id, { name: value.trim() })
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function deleteCat(catalog) {
  try {
    await ElMessageBox.confirm(
      t('page.functional.catalogDeleteConfirm', { name: catalog.name }),
      t('common.warning'),
      { type: 'warning' },
    )
    await deleteCaseCatalog(catalog.id)
    if (selectedCatalogId.value === catalog.id) selectRoot()
    ElMessage.success(t('common.deleted'))
    await loadTree()
  } catch (e) {
    if (e !== 'cancel' && e?.response?.data?.message) {
      ElMessage.error(e.response.data.message)
    }
  }
}

async function moveCat(catalogId, parentId, sortOrder) {
  await moveCaseCatalog(catalogId, {
    parent_id: parentId ?? 0,
    sort_order: sortOrder,
  })
  await loadTree()
}

async function moveCatSibling(catalog, direction) {
  const siblings = getSiblingList(catalogTree.value, catalog.parent_id)
  const idx = siblings.findIndex((s) => s.id === catalog.id)
  const targetIdx = direction === 'up' ? idx - 1 : idx + 1
  if (targetIdx < 0 || targetIdx >= siblings.length) return
  const other = siblings[targetIdx]
  await moveCaseCatalog(catalog.id, { parent_id: catalog.parent_id ?? 0, sort_order: other.sort_order })
  await moveCaseCatalog(other.id, { parent_id: other.parent_id ?? 0, sort_order: catalog.sort_order })
  await loadTree()
}

function openMoveDialog(catalog) {
  moveCatalogId.value = catalog.id
  showMoveDialog.value = true
}

async function confirmMoveCatalog(parentId) {
  if (!moveCatalogId.value) return
  moveLoading.value = true
  try {
    await moveCat(moveCatalogId.value, parentId)
    showMoveDialog.value = false
    ElMessage.success(t('common.saved'))
  } finally {
    moveLoading.value = false
  }
}

async function onCatalogDrop({ catalogId, targetParentId }) {
  try {
    await moveCat(catalogId, targetParentId)
    ElMessage.success(t('common.saved'))
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

function onSectionCommand(cmd) {
  if (cmd === 'catalog') createCat(null)
}

function onCatalogCommand(cmd, catalog) {
  if (cmd === 'child') createCat(catalog.id)
  else if (cmd === 'rename') renameCat(catalog)
  else if (cmd === 'move') openMoveDialog(catalog)
  else if (cmd === 'up') moveCatSibling(catalog, 'up')
  else if (cmd === 'down') moveCatSibling(catalog, 'down')
  else if (cmd === 'root') moveCat(catalog.id, 0)
  else if (cmd === 'delete') deleteCat(catalog)
}

watch(projectId, () => {
  loadTree()
  loadCases()
})

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

.case-delete {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}
</style>
