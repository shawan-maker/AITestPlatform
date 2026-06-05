<template>
  <div class="functional-workspace app-card">
    <PageHeader :title="t('page.functional.title')">
      <template #actions>
        <!-- 创建按钮拆分为下拉菜单 -->
        <el-dropdown v-if="canEdit && projectId" @command="onCreateCommand" :disabled="!selectedCatalogId">
          <el-button type="primary">
            {{ t('page.functional.create') }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="ai">{{ t('page.functional.createByAI') }}</el-dropdown-item>
              <el-dropdown-item command="manual">{{ t('page.functional.createManual') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-tooltip v-if="canEdit && !selectedCatalogId && projectId" :content="t('page.functional.selectCatalogFirst')" placement="top">
          <el-icon style="margin-left: 4px"><info-filled /></el-icon>
        </el-tooltip>
        <el-button v-if="canEdit && selectedIds.length" @click="showBatchEdit = true">{{ t('page.functional.batchEdit') }}</el-button>
        <el-button v-if="projectId" @click="exportCases">{{ t('common.export') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />

    <SplitView v-else :initial-width="300" :min-width="240" :max-width="420" :drawer-title="t('page.functional.allCases')">
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
        <!-- 筛选栏 O2 -->
        <FilterBar v-if="selectedCatalogId !== null || selectedCatalogId === undefined" class="case-filter-bar" @search="loadCases" @reset="resetCaseFilters">
          <el-input v-model="caseFilters.case_name" :placeholder="t('page.functional.caseNamePlaceholder', { default: '用例名称' })" clearable style="width: 180px" />
          <el-select v-model="caseFilters.priority" :placeholder="t('page.functional.priority')" clearable style="width: 100px">
            <el-option label="P0" :value="1" />
            <el-option label="P1" :value="2" />
            <el-option label="P2" :value="3" />
            <el-option label="P3" :value="4" />
          </el-select>
          <el-select v-model="caseFilters.type" :placeholder="t('page.functional.type')" clearable style="width: 110px">
            <el-option label="功能测试" value="functional" />
            <el-option label="UI 测试" value="ui" />
          </el-select>
          <el-select v-model="caseFilters.exec_result" :placeholder="t('page.functional.execResult')" clearable style="width: 110px">
            <el-option :label="t('status.exec.pending')" value="pending" />
            <el-option :label="t('status.exec.passed')" value="passed" />
            <el-option :label="t('status.exec.failed')" value="failed" />
            <el-option :label="t('status.exec.blocked')" value="blocked" />
            <el-option :label="t('status.exec.skipped')" value="skipped" />
          </el-select>
        </FilterBar>

        <PaginatedTable
          ref="tableRef"
          :data="cases"
          :loading="loading"
          row-key="id"
          @row-click="openDetailDrawer"
          @selection-change="onSelectionChange"
        >
          <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="48" />
          <AppTableColumn type="index" variant="fixed" :width="50" :index="(i) => i + 1" />
          <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" min-width="160">
            <template #default="{ row, $index }">
              <span
                draggable="true"
                class="drag-handle"
                @dragstart="onDragStart($index)"
                @dragover.prevent
                @drop="onDrop($index)"
              >⋮⋮</span>
              {{ row.case_name }}
            </template>
          </AppTableColumn>
          <AppTableColumn prop="priority" variant="flex" :label="t('page.functional.priority')" width="70">
            <template #default="{ row }">
              <PriorityTag :value="row.priority" />
            </template>
          </AppTableColumn>
          <AppTableColumn prop="type" variant="flex" :label="t('page.functional.type')" width="90">
            <template #default="{ row }">
              {{ row.type === 'ui' ? 'UI' : t('page.functional.typeFunctional') }}
            </template>
          </AppTableColumn>
          <AppTableColumn prop="module_name" variant="flex" :label="t('page.knowledge.module')" :min-width="100">
            <template #default="{ row }">{{ row.module_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn prop="exec_result" variant="flex" :label="t('page.functional.execResult')" width="95">
            <template #default="{ row }">
              <ExecResultTag :value="row.exec_result" />
            </template>
          </AppTableColumn>
          <AppTableColumn prop="jira_issue_key" variant="flex" :label="t('page.functional.jiraKey')" :min-width="100">
            <template #default="{ row }">{{ row.jira_issue_key || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn prop="created_by_username" variant="flex" :label="t('page.functional.createdBy')" :min-width="85" />
          <AppTableColumn prop="updated_at" variant="flex" :label="t('page.functional.updatedAt')" :min-width="155">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </AppTableColumn>
        </PaginatedTable>
      </template>
    </SplitView>

    <!-- 用例详情 Drawer (3/4 宽) -->
    <FunctionalCaseDetailDrawer
      v-model:visible="detailDrawerVisible"
      :case-id="selectedCaseId"
      :catalogs="catalogTree"
      @edit="onEditFromDrawer"
      @copied="onCopiedFromDrawer"
      @deleted="onDeletedFromDrawer"
    />

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
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, InfoFilled } from '@element-plus/icons-vue'
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
  updateCaseCatalog,
} from '@/api/functional'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import ExecResultTag from '@/components/tags/ExecResultTag.vue'
import FunctionalCaseCreateDialog from '@/components/functional/FunctionalCaseCreateDialog.vue'
import FunctionalBatchEditDialog from '@/components/functional/FunctionalBatchEditDialog.vue'
import FunctionalCaseDetailDrawer from '@/components/functional/FunctionalCaseDetailDrawer.vue'
import FunctionalCatalogSidebar from '@/components/tree/FunctionalCatalogSidebar.vue'
import CatalogMoveDialog from '@/components/tree/CatalogMoveDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { downloadFromResponse } = useDownload()

function formatTime(val) {
  return val ? formatDateTime(val) : '-'
}

const catalogTree = ref([])
const selectedCatalogId = ref(null)
const expandedCatalogIds = ref([])
const cases = ref([])
const loading = ref(false)
const selectedCaseId = ref(null)
const detailDrawerVisible = ref(false)
const showCreate = ref(false)
const showBatchEdit = ref(false)
const selectedIds = ref([])
const creating = ref(false)
const batchUpdating = ref(false)
const dragFromIndex = ref(null)
const caseFilters = reactive({ case_name: '', priority: null, type: null, exec_result: null })

// 筛选分页
const tableRef = ref(null)

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
  const baseParams = withProjectParams({
    catalog_id: selectedCatalogId.value || undefined,
  })
  if (!baseParams) return
  loading.value = true
  try {
    const filterParams = { ...baseParams }
    if (caseFilters.case_name) filterParams.case_name = caseFilters.case_name.trim()
    if (caseFilters.priority != null) filterParams.priority = caseFilters.priority
    if (caseFilters.type) filterParams.type = caseFilters.type
    if (caseFilters.exec_result) filterParams.exec_result = caseFilters.exec_result
    const res = await listCases(filterParams)
    cases.value = res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

function resetCaseFilters() {
  caseFilters.case_name = ''
  caseFilters.priority = null
  caseFilters.type = null
  caseFilters.exec_result = null
  loadCases()
}

function selectRoot() {
  selectedCatalogId.value = null
  selectedCaseId.value = null
  detailDrawerVisible.value = false
  loadCases()
}

function selectCatalog(catalogId) {
  selectedCatalogId.value = catalogId
  selectedCaseId.value = null
  detailDrawerVisible.value = false
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

// 打开详情 Drawer
function openDetailDrawer(row) {
  selectedCaseId.value = row.id
  detailDrawerVisible.value = true
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map((r) => r.id)
}

// 创建按钮下拉命令处理
function onCreateCommand(cmd) {
  if (cmd === 'ai') {
    // 跳转智能体中心，携带项目信息
    router.push({ path: '/agent', query: { gen: 'functional', projectId: projectId.value, catalogId: selectedCatalogId.value } })
  } else if (cmd === 'manual') {
    showCreate.value = true
  }
}

// Drawer 回调
function onEditFromDrawer() {
  // 编辑后刷新列表
  loadCases()
}
function onCopiedFromDrawer() {
  loadCases()
}
function onDeletedFromDrawer() {
  selectedCaseId.value = null
  detailDrawerVisible.value = false
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
    const res = await batchUpdateCases(payload)
    if (res.data.data.warning?.suite_names?.length) {
      ElMessage.warning(t('page.functional.deleteSuiteWarning', { suites: res.data.data.warning.suite_names.join(', ') }))
    } else {
      ElMessage.success(t('common.saved'))
    }
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
    if (row) openDetailDrawer(row)
  }
})
</script>

<style scoped lang="scss">
.drag-handle {
  cursor: grab;
  margin-right: 6px;
  color: var(--el-text-color-secondary);
  user-select: none;
  font-size: 14px;
}

.case-filter-bar {
  margin-bottom: 12px;
}
</style>
