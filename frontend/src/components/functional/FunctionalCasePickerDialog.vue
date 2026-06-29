<template>
  <el-dialog
    :model-value="modelValue"
    :title="t('page.test.addCases')"
    width="85vw"
    :destroy-on-close="true"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <div class="picker-dialog-body">
      <!-- 左侧：用例目录树 -->
      <div class="picker-left">
        <el-input
          v-model="treeSearchKey"
          :placeholder="t('common.keyword')"
          clearable
          size="default"
          class="tree-search"
        />
        <div class="tree-container" v-loading="treeLoading">
          <el-tree
            ref="treeRef"
            :data="filteredTree"
            node-key="nodeKey"
            :props="treeProps"
            show-checkbox
            :check-strictly="true"
            :default-expand-all="false"
            @check="onTreeCheck"
          >
            <template #default="{ node, data }">
              <span class="tree-node-label" @click.stop="onLabelClick(data)">
                <el-icon v-if="!data.isCatalog" style="margin-right: 4px"><FolderOpened /></el-icon>
                <el-icon v-else style="margin-right: 4px"><Folder /></el-icon>
                {{ data.label }}
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧：用例列表 -->
      <div class="picker-right">
        <el-input
          v-model="caseSearchKey"
          :placeholder="t('page.functional.caseNamePlaceholder')"
          clearable
          size="default"
          class="case-search"
          @change="loadCases"
        />
        <div class="case-list-header" v-if="currentCatalogName">
          <span>{{ currentCatalogName }}</span>
        </div>
        <el-table
          ref="caseTableRef"
          :data="filteredCases"
          v-loading="casesLoading"
          size="small"
          border
          row-key="id"
          :empty-text="t('page.functional.selectCatalogFirst')"
          @selection-change="onCaseSelectionChange"
          style="flex: 1"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="case_no" :label="t('page.functional.caseNo')" width="130" show-overflow-tooltip />
          <el-table-column prop="case_name" :label="t('page.functional.caseName')" min-width="180" show-overflow-tooltip />
          <el-table-column :label="t('page.functional.priority')" width="80">
            <template #default="{ row }">
              <PriorityTag v-if="row.priority" :value="row.priority" />
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('page.functional.caseCategory')" width="100">
            <template #default="{ row }">
              {{ row.case_category ? t('page.functional.cat' + row.case_category.charAt(0).toUpperCase() + row.case_category.slice(1)) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="module_name" :label="t('page.knowledge.module')" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.module_name || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <div class="picker-footer">
        <span class="picker-count">{{ t('page.test.selectedCount', { count: selectedCaseIds.size }) }}</span>
        <div>
          <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="onConfirm">{{ t('common.confirm') }}</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Folder, FolderOpened } from '@element-plus/icons-vue'
import { getCaseCatalogTree, listCases } from '@/api/functional'
import PriorityTag from '@/components/tags/PriorityTag.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: Number, required: true },
  /** IDs of already-associated cases — pre-checked in tree and table */
  preSelectedIds: { type: Array, default: () => [] },
  /** Map of caseId → catalogId for pre-selected cases, used to pre-check tree nodes */
  preSelectedCaseMap: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'confirmed'])
const { t } = useI18n()

const treeRef = ref(null)
const caseTableRef = ref(null)
const treeLoading = ref(false)
const casesLoading = ref(false)
const saving = ref(false)
const treeSearchKey = ref('')
const caseSearchKey = ref('')

const catalogTree = ref([])
const currentCases = ref([])
const currentCatalogName = ref('')
const currentCatalogId = ref(null)
const selectedCaseIds = ref(new Set())
const caseCache = ref({})
const casesByCatalog = ref({})
let isSyncingTable = false

const treeProps = { children: 'children', label: 'label' }

const treeData = computed(function () {
  return buildTreeNodes(catalogTree.value)
})

const filteredTree = computed(function () {
  if (!treeSearchKey.value) return treeData.value
  return filterTree(treeData.value, treeSearchKey.value.toLowerCase())
})

const filteredCases = computed(function () {
  if (!caseSearchKey.value) return currentCases.value
  var kw = caseSearchKey.value.toLowerCase()
  return currentCases.value.filter(function (c) {
    return (c.case_name || '').toLowerCase().indexOf(kw) >= 0
  })
})

function buildTreeNodes(nodes) {
  var result = []
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i]
    var treeNode = {
      nodeKey: 'cat-' + node.id,
      label: node.name || '未分类',
      isCatalog: true,
      catalogId: node.id,
      children: [],
    }
    if (node.children && node.children.length) {
      treeNode.children = buildTreeNodes(node.children)
    }
    result.push(treeNode)
  }
  return result
}

function filterTree(nodes, keyword) {
  var result = []
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i]
    var childMatch = node.children ? filterTree(node.children, keyword) : []
    if (node.label.toLowerCase().indexOf(keyword) >= 0 || childMatch.length) {
      result.push(Object.assign({}, node, { children: childMatch.length ? childMatch : node.children }))
    }
  }
  return result
}

async function onOpen() {
  selectedCaseIds.value = new Set(props.preSelectedIds || [])
  currentCases.value = []
  currentCatalogName.value = ''
  currentCatalogId.value = null
  caseCache.value = {}
  casesByCatalog.value = {}
  treeSearchKey.value = ''
  caseSearchKey.value = ''
  await loadTree()
  await preSelectCases()
}

async function loadTree() {
  treeLoading.value = true
  try {
    var res = await getCaseCatalogTree({ project_id: props.projectId })
    catalogTree.value = res.data.data?.items ?? res.data.data ?? []
  } catch (e) {
    catalogTree.value = []
  } finally {
    treeLoading.value = false
  }
}

async function preSelectCases() {
  if (!props.preSelectedIds?.length) return
  await nextTick()
  if (!treeRef.value) return
  // Build set of catalog IDs that contain pre-selected cases
  var catalogIds = new Set()
  var map = props.preSelectedCaseMap || {}
  for (var caseId in map) {
    catalogIds.add(map[caseId])
  }
  // Walk tree and check matching catalog nodes + their parents
  preCheckTreeNodesRecursive(treeData.value, catalogIds)
}

function preCheckTreeNodesRecursive(nodes, catalogIds) {
  if (!nodes || !treeRef.value) return false
  var anyChecked = false
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i]
    var nodeChecked = false
    if (catalogIds.has(node.catalogId)) {
      treeRef.value.setChecked(node.nodeKey, true, false)
      nodeChecked = true
    }
    if (node.children && node.children.length) {
      var childChecked = preCheckTreeNodesRecursive(node.children, catalogIds)
      if (childChecked) {
        treeRef.value.setChecked(node.nodeKey, true, false)
        nodeChecked = true
      }
    }
    if (nodeChecked) anyChecked = true
  }
  return anyChecked
}

// ========== 点击标签：加载目录下的用例 ==========
async function onLabelClick(data) {
  isSyncingTable = true
  currentCatalogId.value = data.catalogId
  currentCatalogName.value = data.label
  await loadCases()
  scheduleSyncSelection()
}

async function loadCases() {
  if (!currentCatalogId.value) return
  casesLoading.value = true
  try {
    var params = { project_id: props.projectId, catalog_id: currentCatalogId.value, page: 1, page_size: 100 }
    if (caseSearchKey.value) params.case_name = caseSearchKey.value
    var res = await listCases(params)
    var cases = res.data.data?.items ?? res.data.data ?? []
    casesByCatalog.value[currentCatalogId.value] = cases
    currentCases.value = cases
    // Cache each case by id
    cases.forEach(function (c) { caseCache.value[c.id] = c })
  } catch (e) {
    currentCases.value = []
  } finally {
    casesLoading.value = false
  }
}

// ========== 勾选同步 ==========
function scheduleSyncSelection() {
  nextTick(function () {
    nextTick(function () {
      doSyncSelection()
    })
  })
}

function doSyncSelection() {
  if (!caseTableRef.value) { isSyncingTable = false; return }
  caseTableRef.value.clearSelection()
  setTimeout(function () {
    if (!caseTableRef.value) { isSyncingTable = false; return }
    var tableData = caseTableRef.value.data || []
    for (var i = 0; i < tableData.length; i++) {
      if (selectedCaseIds.value.has(tableData[i].id)) {
        caseTableRef.value.toggleRowSelection(tableData[i], true)
      }
    }
    setTimeout(function () { isSyncingTable = false }, 100)
  }, 100)
}

// ========== 右侧表格手动勾选 ==========
function onCaseSelectionChange(rows) {
  if (isSyncingTable) return
  var pageIds = currentCases.value.map(function (c) { return c.id })
  pageIds.forEach(function (id) { selectedCaseIds.value.delete(id) })
  rows.forEach(function (r) { selectedCaseIds.value.add(r.id) })
  selectedCaseIds.value = new Set(selectedCaseIds.value)
}

// ========== 左侧树勾选 ==========
async function onTreeCheck(data, checkInfo) {
  var checked = (checkInfo.checkedKeys || []).includes(data.nodeKey)
  isSyncingTable = true

  currentCatalogId.value = data.catalogId
  currentCatalogName.value = data.label
  await loadCases()

  var cases = currentCases.value
  cases.forEach(function (c) {
    if (checked) selectedCaseIds.value.add(c.id)
    else selectedCaseIds.value.delete(c.id)
  })

  // Also check/uncheck child catalog nodes
  if (treeRef.value && data.children?.length) {
    setChildNodesChecked(data, checked)
  }

  selectedCaseIds.value = new Set(selectedCaseIds.value)
  scheduleSyncSelection()
}

function setChildNodesChecked(node, checked) {
  if (!treeRef.value) return
  if (node.children && node.children.length) {
    for (var i = 0; i < node.children.length; i++) {
      treeRef.value.setChecked(node.children[i].nodeKey, checked, false)
      setChildNodesChecked(node.children[i], checked)
    }
  }
}

// ========== 确定 ==========
async function onConfirm() {
  // Emit both IDs and full case objects (from cache) for consumers that need them
  var selectedCases = []
  selectedCaseIds.value.forEach(function (id) {
    if (caseCache.value[id]) selectedCases.push(caseCache.value[id])
  })
  emit('confirmed', [...selectedCaseIds.value], selectedCases)
  emit('update:modelValue', false)
}
</script>

<style scoped lang="scss">
.picker-dialog-body {
  display: flex;
  gap: 16px;
  height: 60vh;
  min-height: 400px;
}

.picker-left {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  padding-right: 16px;
}

.picker-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.tree-search, .case-search {
  margin-bottom: 8px;
  flex-shrink: 0;
}

.tree-container {
  flex: 1;
  overflow: auto;
}

.tree-node-label {
  display: inline-flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  font-size: 13px;
  cursor: pointer;
}

.case-list-header {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
  flex-shrink: 0;
}

.picker-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.picker-count {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
</style>
