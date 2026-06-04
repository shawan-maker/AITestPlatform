<template>
  <div class="api-workspace app-card">
    <PageHeader :title="t('page.apiCases.title')">
      <template #actions>
        <el-button v-if="projectId && selectedCatalogId" @click="showImport = true">{{ t('page.apiCases.importInterfaces') }}</el-button>
        <el-button v-if="canEdit && selectedCatalogId" type="primary" @click="openCreateInterface">{{ t('page.apiCases.createInterface') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <SplitView v-else :initial-width="380" :min-width="300" :max-width="560" :drawer-title="t('page.apiCases.allInterfaces')">
      <template #left>
        <ApiCatalogSidebar
          v-model:keyword="sidebarKeyword"
          :catalog-nodes="catalogTree"
          :selected-catalog-id="selectedCatalogId"
          :selected-interface-id="selectedInterfaceId"
          :expanded-catalog-ids="expandedCatalogIds"
          :interfaces-by-catalog="interfacesByCatalog"
          :can-edit="canEdit"
          @select-root="selectRoot"
          @select-catalog="selectCatalog"
          @select-interface="selectInterfaceFromTree"
          @toggle-expand="onToggleExpand"
          @section-command="onSectionCommand"
          @catalog-command="onCatalogCommand"
          @interface-command="onInterfaceCommand"
          @load-more-interfaces="loadMoreCatalogInterfaces"
          @interface-reorder="onSidebarInterfaceReorder"
          @catalog-drop="onCatalogDrop"
        />
      </template>
      <template #right>
        <InterfaceListPanel
          v-model:search-query="listSearch"
          :interfaces="interfaceList"
          :loading="listLoading"
          :total="listTotal"
          :page="listPage"
          :page-size="listPageSize"
          :selected-interface-id="selectedInterfaceId"
          :can-edit="canEdit"
          @search="onListSearch"
          @select="selectInterfaceFromList"
          @edit="openEditInterface"
          @copy="copyInterfaceItem"
          @delete="removeInterfaceItem"
          @page-change="onListPageChange"
          @size-change="onListSizeChange"
          @reorder="onListInterfaceReorder"
        />
        <el-tabs v-if="selectedInterfaceId" v-model="activeTab" class="interface-tabs">
          <el-tab-pane :label="t('page.apiCases.tabDebug')" name="debug">
            <el-form inline>
              <EnvironmentSelect v-model="environmentId" />
              <el-button type="primary" :loading="debugging" @click="runDebug">{{ t('page.apiCases.debugRun') }}</el-button>
              <el-button @click="saveTemplate">{{ t('common.save') }}</el-button>
              <el-button @click="fillFromDoc">{{ t('page.apiCases.fillFromDoc') }}</el-button>
            </el-form>
            <div class="editor-row">
              <div class="editor-col">
                <div class="editor-label">{{ t('page.apiCases.request') }}</div>
                <MonacoJsonEditor v-model="requestJson" :height="280" />
              </div>
              <div class="editor-col">
                <div class="editor-label">{{ t('page.apiCases.response') }}</div>
                <MonacoJsonEditor v-model="responseJson" read-only :height="220" />
              </div>
            </div>
            <div class="editor-label">{{ t('page.apiCases.assertions') }}</div>
            <MonacoJsonEditor v-model="assertionsJson" :height="160" />
          </el-tab-pane>
          <el-tab-pane :label="t('page.apiCases.tabDocDep')" name="doc-dep">
            <div class="doc-dep-toolbar">
              <el-button :loading="reanalyzing" @click="reanalyze">{{ t('page.apiCases.reanalyze') }}</el-button>
              <el-button @click="loadDocPreview">{{ t('page.apiCases.refreshDoc') }}</el-button>
            </div>
            <div class="editor-label">{{ t('page.apiCases.docPreview') }}</div>
            <MonacoJsonEditor v-if="docPreviewJson" :model-value="docPreviewJson" read-only :height="200" />
            <div class="editor-label">{{ t('page.apiCases.dependencies') }}</div>
            <MonacoJsonEditor v-if="dependencies" :model-value="depJson" read-only :height="240" />
          </el-tab-pane>
          <el-tab-pane :label="t('page.apiCases.tabCases')" name="case">
            <div class="case-toolbar">
              <el-button v-if="canEdit" type="primary" @click="showGenerate = true">{{ t('page.apiCases.generateCases') }}</el-button>
              <el-button link type="primary" @click="goAgentCenter">{{ t('page.apiCases.agentGenerate') }}</el-button>
            </div>
            <h4>{{ t('page.apiCases.preconditionCases') }}</h4>
            <PaginatedTable :data="preconditionCases" :loading="casesLoading" :show-pagination="false">
              <AppTableColumn prop="title" variant="content" :label="t('common.name')">
                <template #default="{ row }">{{ row.title || row.name }}</template>
              </AppTableColumn>
              <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="router.push(`/cases/api/cases/${row.id}`)">{{ t('common.view') }}</el-button>
                </template>
              </AppTableColumn>
            </PaginatedTable>
            <h4 style="margin-top: 16px">{{ t('page.apiCases.mainCases') }}</h4>
            <PaginatedTable :data="mainCases" :loading="casesLoading" :show-pagination="false">
              <AppTableColumn prop="title" variant="content" :label="t('common.name')">
                <template #default="{ row }">{{ row.title || row.name }}</template>
              </AppTableColumn>
              <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="router.push(`/cases/api/cases/${row.id}`)">{{ t('common.view') }}</el-button>
                </template>
              </AppTableColumn>
            </PaginatedTable>
          </el-tab-pane>
        </el-tabs>
      </template>
    </SplitView>

    <ImportInterfacesWizard v-model="showImport" :catalog-id="selectedCatalogId" @imported="onImported" />
    <InterfaceFormDrawer
      v-model="showInterfaceForm"
      :catalog-id="interfaceFormCatalogId"
      :interface-data="editingInterface"
      @saved="onInterfaceSaved"
    />
    <InterfaceCaseGenerateDialog
      v-if="selectedInterfaceId"
      v-model="showGenerate"
      :interface-id="selectedInterfaceId"
      @confirmed="loadCases"
    />
    <CatalogMoveDialog
      v-model="showMoveDialog"
      :catalog-nodes="catalogTree"
      :exclude-catalog-id="moveCatalogId"
      :loading="moveLoading"
      @confirm="confirmMoveCatalog"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  copyInterface,
  createApiCatalog,
  debugRunInterface,
  deleteApiCatalog,
  deleteInterface,
  fillDebugFromDoc,
  getApiCatalogTree,
  getDebugTemplate,
  getDocPreview,
  listApiCases,
  listDependencies,
  listInterfaces as fetchInterfaces,
  listInterfacesByCatalog,
  moveApiCatalog,
  reanalyzeDependencies,
  reorderInterfaces,
  saveDebugTemplate,
  updateApiCatalog,
} from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'
import ImportInterfacesWizard from '@/components/api-test/ImportInterfacesWizard.vue'
import InterfaceFormDrawer from '@/components/api-test/InterfaceFormDrawer.vue'
import InterfaceCaseGenerateDialog from '@/components/agent/InterfaceCaseGenerateDialog.vue'
import ApiCatalogSidebar from '@/components/tree/ApiCatalogSidebar.vue'
import InterfaceListPanel from '@/components/api-test/InterfaceListPanel.vue'
import CatalogMoveDialog from '@/components/tree/CatalogMoveDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()

const catalogTree = ref([])
const selectedCatalogId = ref(route.query.catalogId ? Number(route.query.catalogId) : null)
const selectedInterfaceId = ref(route.query.interfaceId ? Number(route.query.interfaceId) : null)
const sidebarKeyword = ref('')
const expandedCatalogIds = ref([])
const interfacesByCatalog = ref({})

const interfaceList = ref([])
const listLoading = ref(false)
const listTotal = ref(0)
const listPage = ref(1)
const listPageSize = ref(20)
const listSearch = ref('')

const activeTab = ref(route.query.tab || 'debug')
const environmentId = ref(null)
const requestJson = ref('{}')
const responseJson = ref('')
const assertionsJson = ref('[]')
const debugging = ref(false)
const reanalyzing = ref(false)
const dependencies = ref(null)
const docPreview = ref(null)
const preconditionCases = ref([])
const mainCases = ref([])
const casesLoading = ref(false)
const showImport = ref(false)
const showInterfaceForm = ref(false)
const showGenerate = ref(false)
const editingInterface = ref(null)
const interfaceFormCatalogId = ref(null)

const showMoveDialog = ref(false)
const moveCatalogId = ref(null)
const moveLoading = ref(false)

const depJson = computed(() => JSON.stringify(dependencies.value ?? {}, null, 2))
const docPreviewJson = computed(() => (docPreview.value ? JSON.stringify(docPreview.value, null, 2) : ''))

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

function findCatalogName(nodes, catalogId) {
  return findCatalogNode(nodes, catalogId)?.name ?? String(catalogId)
}

function getSiblingList(nodes, parentId) {
  if (parentId == null) return nodes
  return findCatalogNode(nodes, parentId)?.children ?? []
}

async function loadTree() {
  const params = withProjectParams()
  if (!params) return
  const res = await getApiCatalogTree(params)
  catalogTree.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadInterfaceList() {
  const params = withProjectParams()
  if (!params) return
  listLoading.value = true
  try {
    const query = {
      page: listPage.value,
      page_size: listPageSize.value,
      q: listSearch.value.trim() || undefined,
    }
    let res
    if (selectedCatalogId.value == null) {
      res = await fetchInterfaces({ ...params, ...query })
    } else {
      res = await listInterfacesByCatalog(selectedCatalogId.value, query)
    }
    const data = res.data.data
    interfaceList.value = data?.items ?? []
    listTotal.value = data?.total ?? interfaceList.value.length
  } finally {
    listLoading.value = false
  }
}

async function loadCatalogInterfaces(catalogId, append = false) {
  const prev = interfacesByCatalog.value[catalogId] || { items: [], page: 0, total: 0 }
  const page = append ? prev.page + 1 : 1
  if (append) {
    interfacesByCatalog.value = {
      ...interfacesByCatalog.value,
      [catalogId]: { ...prev, loadingMore: true },
    }
  }
  try {
    const res = await listInterfacesByCatalog(catalogId, { page, page_size: 20 })
    const items = res.data.data?.items ?? []
    const total = res.data.data?.total ?? items.length
    interfacesByCatalog.value = {
      ...interfacesByCatalog.value,
      [catalogId]: {
        items: append ? [...prev.items, ...items] : items,
        page,
        total,
        hasMore: page * 20 < total,
        loadingMore: false,
      },
    }
  } catch {
    if (append) {
      interfacesByCatalog.value = {
        ...interfacesByCatalog.value,
        [catalogId]: { ...prev, loadingMore: false },
      }
    }
  }
}

function selectRoot() {
  selectedCatalogId.value = null
  selectedInterfaceId.value = null
  listPage.value = 1
  loadInterfaceList()
}

function selectCatalog(catalogId) {
  selectedCatalogId.value = catalogId
  selectedInterfaceId.value = null
  listPage.value = 1
  loadInterfaceList()
}

function selectInterfaceFromTree(iface, catalogId) {
  selectedCatalogId.value = catalogId
  selectedInterfaceId.value = iface.id
}

function selectInterfaceFromList(row) {
  selectedInterfaceId.value = row.id
  if (row.catalog_id != null) selectedCatalogId.value = row.catalog_id
}

function onToggleExpand(catalogId) {
  const idx = expandedCatalogIds.value.indexOf(catalogId)
  if (idx >= 0) {
    expandedCatalogIds.value = expandedCatalogIds.value.filter((id) => id !== catalogId)
  } else {
    expandedCatalogIds.value = [...expandedCatalogIds.value, catalogId]
    if (!interfacesByCatalog.value[catalogId]?.items?.length) {
      loadCatalogInterfaces(catalogId)
    }
  }
}

function loadMoreCatalogInterfaces(catalogId) {
  loadCatalogInterfaces(catalogId, true)
}

async function loadTemplate() {
  if (!selectedInterfaceId.value) return
  const res = await getDebugTemplate(selectedInterfaceId.value).catch(() => null)
  const tpl = res?.data?.data ?? {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions ?? [], null, 2)
}

async function loadCases() {
  if (!selectedInterfaceId.value) return
  casesLoading.value = true
  try {
    const [preRes, mainRes] = await Promise.all([
      listApiCases(selectedInterfaceId.value, { case_kind: 'precondition' }),
      listApiCases(selectedInterfaceId.value, { case_kind: 'main' }),
    ])
    preconditionCases.value = preRes.data.data?.items ?? preRes.data.data ?? []
    mainCases.value = mainRes.data.data?.items ?? mainRes.data.data ?? []
  } finally {
    casesLoading.value = false
  }
}

async function loadDeps() {
  if (!selectedInterfaceId.value) return
  const res = await listDependencies(selectedInterfaceId.value)
  dependencies.value = res.data.data
}

async function loadDocPreview() {
  if (!selectedInterfaceId.value) return
  const res = await getDocPreview(selectedInterfaceId.value)
  docPreview.value = res.data.data
}

async function runDebug() {
  debugging.value = true
  try {
    const res = await debugRunInterface(selectedInterfaceId.value, { environment_id: environmentId.value })
    responseJson.value = JSON.stringify(res.data.data, null, 2)
  } finally {
    debugging.value = false
  }
}

async function saveTemplate() {
  let payload
  try {
    payload = JSON.parse(requestJson.value)
    payload.assertions = JSON.parse(assertionsJson.value)
  } catch {
    ElMessage.error(t('page.apiCases.invalidJson'))
    return
  }
  await saveDebugTemplate(selectedInterfaceId.value, payload)
  ElMessage.success(t('common.saved'))
}

async function fillFromDoc() {
  const res = await fillDebugFromDoc(selectedInterfaceId.value)
  const tpl = res.data.data ?? {}
  requestJson.value = JSON.stringify(tpl, null, 2)
  assertionsJson.value = JSON.stringify(tpl.assertions ?? [], null, 2)
  ElMessage.success(t('page.apiCases.filledFromDoc'))
}

async function reanalyze() {
  reanalyzing.value = true
  try {
    await reanalyzeDependencies(selectedInterfaceId.value)
    await loadDeps()
    ElMessage.success(t('common.saved'))
  } finally {
    reanalyzing.value = false
  }
}

function openCreateInterface() {
  editingInterface.value = null
  interfaceFormCatalogId.value = selectedCatalogId.value
  showInterfaceForm.value = true
}

function openEditInterface(row) {
  editingInterface.value = row
  interfaceFormCatalogId.value = row.catalog_id ?? selectedCatalogId.value
  showInterfaceForm.value = true
}

async function removeInterfaceItem(row) {
  const id = row?.id ?? selectedInterfaceId.value
  await ElMessageBox.confirm(t('common.deleteConfirm'), { type: 'warning' })
  await deleteInterface(id)
  if (selectedInterfaceId.value === id) selectedInterfaceId.value = null
  await refreshAfterInterfaceChange()
  ElMessage.success(t('common.deleted'))
}

async function copyInterfaceItem(row) {
  const id = row?.id ?? selectedInterfaceId.value
  const res = await copyInterface(id)
  const copied = res.data.data
  ElMessage.success(copied?.path ? `${t('common.copy')}: ${copied.path}` : t('common.saved'))
  await refreshAfterInterfaceChange()
  if (copied?.id) selectedInterfaceId.value = copied.id
}

function onInterfaceCommand(cmd, iface) {
  if (cmd === 'edit') openEditInterface(iface)
  else if (cmd === 'copy') copyInterfaceItem(iface)
  else if (cmd === 'delete') removeInterfaceItem(iface)
}

async function refreshAfterInterfaceChange() {
  await loadTree()
  await loadInterfaceList()
  for (const catalogId of expandedCatalogIds.value) {
    await loadCatalogInterfaces(catalogId)
  }
}

function onImported() {
  refreshAfterInterfaceChange()
}

function onInterfaceSaved() {
  refreshAfterInterfaceChange()
}

function onListSearch() {
  listPage.value = 1
  loadInterfaceList()
}

function onListPageChange(page) {
  listPage.value = page
  loadInterfaceList()
}

function onListSizeChange(size) {
  listPageSize.value = size
  listPage.value = 1
  loadInterfaceList()
}

async function applyInterfaceReorder(catalogId, orderedIds, targetCatalogId) {
  await reorderInterfaces({
    catalog_id: catalogId,
    ordered_ids: orderedIds,
    target_catalog_id: targetCatalogId,
  })
  await refreshAfterInterfaceChange()
}

async function onListInterfaceReorder({ fromIndex, toIndex }) {
  const reordered = [...interfaceList.value]
  const [item] = reordered.splice(fromIndex, 1)
  reordered.splice(toIndex, 0, item)
  interfaceList.value = reordered
  const catalogId = selectedCatalogId.value ?? item.catalog_id
  if (!catalogId) return
  await applyInterfaceReorder(catalogId, reordered.map((i) => i.id))
}

async function onSidebarInterfaceReorder({ catalogId, fromIndex, toIndex }) {
  const state = interfacesByCatalog.value[catalogId]
  if (!state) return
  const reordered = [...state.items]
  const [item] = reordered.splice(fromIndex, 1)
  reordered.splice(toIndex, 0, item)
  interfacesByCatalog.value = {
    ...interfacesByCatalog.value,
    [catalogId]: { ...state, items: reordered },
  }
  await applyInterfaceReorder(catalogId, reordered.map((i) => i.id))
}

async function createCat(parentId = null) {
  const params = withProjectParams()
  if (!params) return
  const { value } = await ElMessageBox.prompt(t('page.apiCases.catalogName'), t('page.apiCases.addCatalog'))
  if (!value?.trim()) return
  await createApiCatalog({ name: value.trim(), parent_id: parentId ?? undefined }, params)
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function renameCat(catalog) {
  const { value } = await ElMessageBox.prompt(t('page.apiCases.catalogName'), t('page.apiCases.renameCatalog'), {
    inputValue: catalog.name,
  })
  if (!value?.trim() || value.trim() === catalog.name) return
  await updateApiCatalog(catalog.id, { name: value.trim() })
  ElMessage.success(t('common.saved'))
  await loadTree()
}

async function deleteCat(catalog) {
  await ElMessageBox.confirm(
    t('page.apiCases.catalogDeleteConfirm', { name: catalog.name }),
    t('common.warning'),
    { type: 'warning' },
  )
  await deleteApiCatalog(catalog.id)
  if (selectedCatalogId.value === catalog.id) selectRoot()
  ElMessage.success(t('common.deleted'))
  await loadTree()
  await loadInterfaceList()
}

async function moveCat(catalogId, parentId, sortOrder) {
  await moveApiCatalog(catalogId, {
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
  await moveApiCatalog(catalog.id, { parent_id: catalog.parent_id ?? 0, sort_order: other.sort_order })
  await moveApiCatalog(other.id, { parent_id: other.parent_id ?? 0, sort_order: catalog.sort_order })
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

function goAgentCenter() {
  router.push({
    path: '/agent',
    query: {
      tab: 'api',
      new: '1',
      interface_id: selectedInterfaceId.value || undefined,
    },
  })
}

watch(projectId, () => {
  loadTree()
  loadInterfaceList()
})

watch(selectedCatalogId, () => {
  loadInterfaceList()
})

watch(selectedInterfaceId, () => {
  if (selectedInterfaceId.value) {
    loadTemplate()
    loadCases()
    loadDeps()
    loadDocPreview()
  }
})

onMounted(async () => {
  await loadTree()
  await loadInterfaceList()
  if (selectedInterfaceId.value) {
    await loadTemplate()
    await loadCases()
    await loadDeps()
    await loadDocPreview()
  }
})
</script>

<style scoped lang="scss">
.interface-tabs {
  margin-top: 16px;
}

.editor-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}

.editor-label {
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--el-text-color-secondary);
}

.doc-dep-toolbar,
.case-toolbar {
  margin-bottom: 12px;
}

h4 {
  font-size: 14px;
  margin: 0 0 8px;
}
</style>
