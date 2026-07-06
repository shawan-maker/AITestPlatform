<template>
  <div class="functional-workspace app-card">
    <PageHeader :title="t('page.functional.title')" />
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
        <!-- 筛选栏 - 始终显示 -->
        <div class="case-filter-bar">
          <FilterBar @search="loadCases" @reset="resetCaseFilters">
            <!-- 创建按钮（放在搜索框左边） -->
            <template #primary>
              <el-dropdown v-if="canEdit && projectId" @command="onCreateCommand">
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
              <!-- 批量操作下拉菜单（放在新建用例按钮右边） -->
              <el-dropdown v-if="canEdit && selectedIds.length" @command="onBatchCommand" trigger="click">
                <el-button>
                  {{ t('page.functional.batchOperation') }} ({{ selectedIds.length }})
                  <el-icon class="el-icon--right"><arrow-down /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">{{ t('page.functional.batchEdit') }}</el-dropdown-item>
                    <el-dropdown-item command="move">{{ t('page.functional.batchMove') }}</el-dropdown-item>
                    <el-dropdown-item command="copy">{{ t('page.functional.batchCopy') }}</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>{{ t('page.functional.batchDelete') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            <el-input v-model="caseFilters.case_name" :placeholder="t('page.functional.caseNamePlaceholder', { default: '用例名称' })" clearable style="width: 180px" />
            <el-select v-model="caseFilters.priority" :placeholder="t('page.functional.priority')" clearable style="width: 100px">
              <el-option label="P0" :value="1" />
              <el-option label="P1" :value="2" />
              <el-option label="P2" :value="3" />
              <el-option label="P3" :value="4" />
            </el-select>
            <el-select v-model="caseFilters.case_category" :placeholder="t('page.functional.caseCategory')" clearable style="width: 130px">
              <el-option :label="t('page.functional.catFunctional')" value="functional" />
              <el-option :label="t('page.functional.catPerformance')" value="performance" />
              <el-option :label="t('page.functional.catSecurity')" value="security" />
              <el-option :label="t('page.functional.catCompatibility')" value="compatibility" />
              <el-option :label="t('page.functional.catUsability')" value="usability" />
              <el-option :label="t('page.functional.catOther')" value="other" />
            </el-select>
          </FilterBar>
        </div>

        <PaginatedTable
          ref="tableRef"
          :data="cases"
          :loading="loading"
          :total="totalCases"
          v-model:page="currentPage"
          v-model:page-size="pageSize"
          row-key="id"
          @row-click="openDetailDrawer"
          @selection-change="onSelectionChange"
          @page-change="onPageChange"
          @size-change="onSizeChange"
        >
          <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
          <AppTableColumn type="index" variant="fixed" :width="50" :index="(i) => (currentPage - 1) * pageSize + i + 1" />
          <!-- 用例编号列 -->
          <AppTableColumn prop="case_no" variant="content" :label="t('page.functional.caseNo')" width="120" />
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
          <AppTableColumn prop="priority" variant="flex" :label="t('page.functional.priority')" width="90" sortable @sort-change="onSortChange">
            <template #default="{ row }">
              <PriorityTag :value="row.priority" />
            </template>
          </AppTableColumn>
          <AppTableColumn prop="case_category" variant="flex" :label="t('page.functional.caseCategory')" width="100">
            <template #default="{ row }">
              {{ t(`page.functional.cat${row.case_category.charAt(0).toUpperCase() + row.case_category.slice(1)}`) }}
            </template>
          </AppTableColumn>
          <AppTableColumn prop="module_name" variant="flex" :label="t('page.knowledge.module')" :min-width="100">
            <template #default="{ row }">{{ row.module_name || '-' }}</template>
          </AppTableColumn>
          <AppTableColumn prop="created_at" variant="flex" :label="t('page.functional.createdAt')" :min-width="155">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </AppTableColumn>
          <AppTableColumn prop="created_by_username" variant="flex" :label="t('page.functional.createdBy')" :min-width="85" />
          <AppTableColumn prop="updated_by_username" variant="flex" :label="t('page.functional.updatedBy')" :min-width="85" />
          <AppTableColumn prop="updated_at" variant="flex" :label="t('page.functional.updatedAt')" :min-width="155" sortable @sort-change="onSortChange">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </AppTableColumn>
          <!-- 操作列 - 字体与知识库一致，不使用 size="small" -->
          <AppTableColumn v-if="canEdit" actions :label="t('common.actions')" variant="fixed" :button-labels="[t('common.edit'), t('page.functional.copy'), t('common.delete')]" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="editCase(row)">{{ t('common.edit') }}</el-button>
              <el-button link type="primary" @click.stop="handleCopyCase(row)">{{ t('page.functional.copy') }}</el-button>
              <el-button link type="danger" @click.stop="handleDeleteCase(row)">{{ t('common.delete') }}</el-button>
            </template>
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
    <FunctionalCaseEditDialog
      v-model="showEdit"
      :case-id="editCaseId"
      :catalogs="catalogTree"
      :loading="editing"
      @submit="editCaseItem"
    />
    <FunctionalBatchEditDialog
      v-model="showBatchEdit"
      :case-ids="selectedIds"
      :loading="batchUpdating"
      @submit="batchUpdate"
    />
    <FunctionalBatchMoveDialog
      v-model="showBatchMove"
      :catalogs="catalogTree"
      :case-ids="selectedIds"
      :loading="batchMoving"
      @confirm="batchMove"
    />
    <FunctionalBatchCopyDialog
      v-model="showBatchCopy"
      :catalogs="catalogTree"
      :case-ids="selectedIds"
      :loading="batchCopying"
      @confirm="batchCopy"
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
import { ArrowDown } from '@element-plus/icons-vue'
import {
  batchUpdateCases,
  batchMoveCases,
  batchCopyCases,
  batchDeleteCases,
  createCase,
  createCaseCatalog,
  copyCase,
  deleteCase,
  deleteCaseCatalog,
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
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import FunctionalCaseCreateDialog from '@/components/functional/FunctionalCaseCreateDialog.vue'
import FunctionalCaseEditDialog from '@/components/functional/FunctionalCaseEditDialog.vue'
import FunctionalBatchEditDialog from '@/components/functional/FunctionalBatchEditDialog.vue'
import FunctionalBatchMoveDialog from '@/components/functional/FunctionalBatchMoveDialog.vue'
import FunctionalBatchCopyDialog from '@/components/functional/FunctionalBatchCopyDialog.vue'
import FunctionalCaseDetailDrawer from '@/components/functional/FunctionalCaseDetailDrawer.vue'
import FunctionalCatalogSidebar from '@/components/tree/FunctionalCatalogSidebar.vue'
import CatalogMoveDialog from '@/components/tree/CatalogMoveDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

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
const showEdit = ref(false)
const editCaseId = ref(null)
const showBatchEdit = ref(false)
const showBatchMove = ref(false)
const showBatchCopy = ref(false)
const selectedIds = ref([])
const creating = ref(false)
const editing = ref(false)
const batchUpdating = ref(false)
const batchMoving = ref(false)
const batchCopying = ref(false)
const dragFromIndex = ref(null)
const caseFilters = reactive({ case_name: '', priority: null, case_category: null })

// 排序状态
const sortField = ref('')  // 'priority' | 'updated_at' | ''
const sortOrder = ref('')  // 'ascending' | 'descending' | ''

// 筛选分页
const tableRef = ref(null)
const totalCases = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

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
    const filterParams = {
      ...baseParams,
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (caseFilters.case_name) filterParams.case_name = caseFilters.case_name.trim()
    if (caseFilters.priority != null) filterParams.priority = caseFilters.priority
    if (caseFilters.case_category) filterParams.case_category = caseFilters.case_category
    // 添加排序参数
    if (sortField.value) {
      filterParams.sort_field = sortField.value
      filterParams.sort_order = sortOrder.value === 'descending' ? 'desc' : 'asc'
    }
    const res = await listCases(filterParams)
    const data = res.data.data
    cases.value = data?.items ?? []
    totalCases.value = data?.total ?? 0
  } finally {
    loading.value = false
  }

function onPageChange(p) {
  currentPage.value = p
  loadCases()
}

function onSizeChange(s) {
  pageSize.value = s
  currentPage.value = 1
  loadCases()
}
}

function resetCaseFilters() {
  caseFilters.case_name = ''
  caseFilters.priority = null
  caseFilters.case_category = null
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

function onSortChange({ column, prop, order }) {
  if (!order) {
    sortField.value = ''
    sortOrder.value = ''
  } else {
    sortField.value = prop
    sortOrder.value = order
  }
  loadCases()
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

// 批量操作下拉命令处理
function onBatchCommand(cmd) {
  if (selectedIds.value.length === 0) {
    ElMessage.warning(t('page.functional.selectCasesFirst'))
    return
  }
  if (cmd === 'edit') {
    showBatchEdit.value = true
  } else if (cmd === 'move') {
    showBatchMove.value = true
  } else if (cmd === 'copy') {
    showBatchCopy.value = true
  } else if (cmd === 'delete') {
    batchDelete()
  }
}

// Drawer 回调
function onEditFromDrawer() {
  // 关闭详情抽屉，打开编辑对话框
  detailDrawerVisible.value = false
  if (selectedCaseId.value) {
    editCaseId.value = selectedCaseId.value
    showEdit.value = true
  }
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

async function editCaseItem(form) {
  editing.value = true
  try {
    await updateCase(editCaseId.value, form)
    ElMessage.success(t('common.saved'))
    showEdit.value = false
    loadCases()
  } finally {
    editing.value = false
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

async function batchMove(targetCatalogId) {
  batchMoving.value = true
  try {
    const payload = { case_ids: selectedIds.value, target_catalog_id: targetCatalogId }
    const res = await batchMoveCases(payload)
    if (res.data.data.warning?.suite_names?.length) {
      ElMessage.warning(t('page.functional.deleteSuiteWarning', { suites: res.data.data.warning.suite_names.join(', ') }))
    } else {
      ElMessage.success(t('common.moved'))
    }
    showBatchMove.value = false
    loadCases()
  } finally {
    batchMoving.value = false
  }
}

async function batchCopy(targetCatalogId) {
  batchCopying.value = true
  try {
    const payload = { case_ids: selectedIds.value, target_catalog_id: targetCatalogId }
    const res = await batchCopyCases(payload)
    if (res.data.data.warning?.suite_names?.length) {
      ElMessage.warning(t('page.functional.deleteSuiteWarning', { suites: res.data.data.warning.suite_names.join(', ') }))
    } else {
      ElMessage.success(t('common.copied'))
    }
    showBatchCopy.value = false
    loadCases()
  } finally {
    batchCopying.value = false
  }
}

async function batchDelete() {
  try {
    await ElMessageBox.confirm(
      t('page.functional.confirmDelete', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    const res = await batchDeleteCases({ case_ids: selectedIds.value })
    if (res.data.data?.warning?.suite_names?.length) {
      ElMessage.warning(t('page.functional.deleteSuiteWarning', { suites: res.data.data.warning.suite_names.join(', ') }))
    } else {
      ElMessage.success(t('page.functional.deleteSuccess'))
    }
    loadCases()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

function editCase(row) {
  editCaseId.value = row.id
  showEdit.value = true
}

async function handleCopyCase(row) {
  try {
    await copyCase(row.id)
    ElMessage.success(t('page.functional.copied'))
    loadCases()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message)
  }
}

async function handleDeleteCase(row) {
  try {
    await ElMessageBox.confirm(
      t('page.functional.confirmDelete', { count: 1 }),
      t('common.warning'),
      { type: 'warning' }
    )
    await deleteCase(row.id)
    ElMessage.success(t('common.deleted'))
    loadCases()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

function onDragStart(index) {
  dragFromIndex.value = index
}

async function onDrop(toIndex) {
  const from = dragFromIndex.value
  if (from == null || from === toIndex) return
  // 全部用例视图不允许拖拽排序
  if (!selectedCatalogId.value) {
    dragFromIndex.value = null
    return
  }
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
  else if (cmd === 'root') moveCat(catalog.id, 0)
  else if (cmd === 'delete') deleteCat(catalog)
}

watch(projectId, () => {
  loadTree()
  loadCases()
})

watch(selectedCatalogId, loadCases)

// 分页变化时自动刷新数据（兜底：确保 v-model 事件未触发时也能刷新）
watch(currentPage, () => { loadCases() })
watch(pageSize, () => { currentPage.value = 1; loadCases() })

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
