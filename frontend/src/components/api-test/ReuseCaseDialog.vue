<template>
  <el-dialog
    :model-value="modelValue"
    title="复用用例"
    width="80vw"
    :destroy-on-close="true"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <div class="reuse-dialog-body">
      <!-- 左侧：接口目录树 -->
      <div class="reuse-left">
        <el-input
          v-model="treeSearchKey"
          placeholder="搜索目录/接口"
          clearable
          size="default"
          :prefix-icon="Search"
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
                <el-icon v-if="data.isInterface" style="margin-right: 4px"><Document /></el-icon>
                <el-icon v-else style="margin-right: 4px"><Folder /></el-icon>
                {{ data.label }}
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 右侧：用例列表 -->
      <div class="reuse-right">
        <el-input
          v-model="caseSearchKey"
          placeholder="搜索用例名称"
          clearable
          size="default"
          :prefix-icon="Search"
          class="case-search"
        />
        <div class="case-list-header" v-if="currentInterfaceName">
          <span>{{ currentInterfaceName }} 的用例</span>
        </div>
        <el-table
          ref="caseTableRef"
          :data="filteredCases"
          v-loading="casesLoading"
          size="small"
          border
          row-key="id"
          empty-text="请点击左侧接口查看用例"
          @selection-change="onCaseSelectionChange"
          style="flex: 1"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="title" label="用例名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="请求URL" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <template v-if="getCaseUrl(row)">
                <el-tag size="small" :type="getMethodType(row)" style="margin-right: 4px">{{ getCaseMethod(row) }}</el-tag>
                {{ getCaseUrl(row) }}
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <div class="reuse-footer">
        <span class="reuse-count">已选择 {{ selectedCaseIds.size }} 条用例</span>
        <div>
          <el-button @click="$emit('update:modelValue', false)">取消</el-button>
          <el-button type="primary" :disabled="!selectedCaseIds.size" :loading="saving" @click="onConfirm">确定</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Document, Folder } from '@element-plus/icons-vue'
import { getApiCatalogTree, listInterfacesByCatalog, listApiCases, reuseApiCases } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseKind: { type: String, default: 'main' },
  currentInterfaceId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'confirmed'])
const { withProjectParams } = useProjectScope()

const treeRef = ref(null)
const caseTableRef = ref(null)
const treeLoading = ref(false)
const casesLoading = ref(false)
const saving = ref(false)
const treeSearchKey = ref('')
const caseSearchKey = ref('')

const catalogTree = ref([])
const interfacesByCatalog = ref({})
const currentCases = ref([])
const currentInterfaceName = ref('')
const currentInterfaceId = ref(null)
const selectedCaseIds = ref(new Set())
const caseCache = ref({})
var isSyncingTable = false

const treeProps = { children: 'children', label: 'label' }

function getCaseUrl(row) {
  var p = row.case_payload
  if (!p) return ''
  return p.path || (p.interface && p.interface.url) || p.url || ''
}
function getCaseMethod(row) {
  var p = row.case_payload
  if (!p) return ''
  return (p.method || (p.interface && p.interface.method) || 'GET').toUpperCase()
}
function getMethodType(row) {
  var m = getCaseMethod(row)
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

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
    return (c.title || '').toLowerCase().indexOf(kw) >= 0
  })
})

function buildTreeNodes(nodes) {
  var result = []
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i]
    var treeNode = {
      nodeKey: 'cat-' + node.id,
      label: node.name || '未命名目录',
      isInterface: false,
      catalogId: node.id,
      children: [],
    }
    var ifaces = interfacesByCatalog.value[node.id] || []
    for (var j = 0; j < ifaces.length; j++) {
      treeNode.children.push({
        nodeKey: 'iface-' + ifaces[j].id,
        label: ifaces[j].summary || ifaces[j].name || ifaces[j].path,
        isInterface: true,
        interfaceId: ifaces[j].id,
        children: [],
      })
    }
    if (node.children && node.children.length) {
      treeNode.children = treeNode.children.concat(buildTreeNodes(node.children))
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
  selectedCaseIds.value = new Set()
  currentCases.value = []
  currentInterfaceName.value = ''
  currentInterfaceId.value = null
  caseCache.value = {}
  treeSearchKey.value = ''
  caseSearchKey.value = ''
  await loadTree()
}

async function loadTree() {
  treeLoading.value = true
  try {
    var params = withProjectParams()
    if (!params) return
    var res = await getApiCatalogTree(params)
    catalogTree.value = res.data.data?.items ?? res.data.data ?? []
    await loadAllCatalogInterfaces(catalogTree.value)
  } catch (e) {
    console.error('加载目录树失败:', e)
  } finally {
    treeLoading.value = false
  }
}

async function loadAllCatalogInterfaces(nodes) {
  for (var i = 0; i < nodes.length; i++) {
    var node = nodes[i]
    if (!interfacesByCatalog.value[node.id]) {
      try {
        var res = await listInterfacesByCatalog(node.id, { page: 1, page_size: 200 })
        interfacesByCatalog.value[node.id] = res.data.data?.items ?? []
      } catch (e) {
        interfacesByCatalog.value[node.id] = []
      }
    }
    if (node.children && node.children.length) {
      await loadAllCatalogInterfaces(node.children)
    }
  }
}

// ========== 点击标签：显示用例，不影响勾选 ==========
async function onLabelClick(data) {
  // 先设守卫，防止 table 数据变更触发的 @selection-change 清空 selectedCaseIds
  isSyncingTable = true
  if (data.isInterface) {
    currentInterfaceId.value = data.interfaceId
    currentInterfaceName.value = data.label
    await loadInterfaceCases(data.interfaceId)
  } else {
    currentInterfaceId.value = null
    currentInterfaceName.value = data.label + '（全部用例）'
    await loadCatalogAllCases(data)
  }
  // 切换接口后，同步已有选择状态到表格
  scheduleSyncSelection()
}

async function loadCatalogAllCases(catalogNode) {
  casesLoading.value = true
  try {
    var allCases = []
    await collectCasesRecursive(catalogNode, allCases)
    currentCases.value = allCases
  } catch (e) {
    console.error('加载目录用例失败:', e)
    currentCases.value = []
  } finally {
    casesLoading.value = false
  }
}

async function collectCasesRecursive(node, result) {
  if (node.isInterface) {
    await loadInterfaceCases(node.interfaceId)
    var cases = caseCache.value[node.interfaceId] || []
    for (var i = 0; i < cases.length; i++) {
      result.push(cases[i])
    }
  }
  if (node.children) {
    for (var i = 0; i < node.children.length; i++) {
      await collectCasesRecursive(node.children[i], result)
    }
  }
}

async function loadInterfaceCases(interfaceId) {
  if (caseCache.value[interfaceId]) {
    currentCases.value = caseCache.value[interfaceId]
    return
  }
  casesLoading.value = true
  try {
    var res = await listApiCases(interfaceId, { page: 1, page_size: 200 })
    var cases = res.data.data?.items ?? res.data.data ?? []
    caseCache.value[interfaceId] = cases
    currentCases.value = cases
  } catch (e) {
    console.error('加载用例失败:', e)
    currentCases.value = []
  } finally {
    casesLoading.value = false
  }
}

// ========== 勾选同步 ==========
function scheduleSyncSelection() {
  console.log('[DEBUG] scheduleSyncSelection called, will wait 2x nextTick')
  // 等两次 nextTick：第一次等 Vue 更新 DOM，第二次等 el-table 内部渲染行
  nextTick(function () {
    console.log('[DEBUG] nextTick 1 done')
    nextTick(function () {
      console.log('[DEBUG] nextTick 2 done, calling doSyncSelection')
      doSyncSelection()
    })
  })
}

function doSyncSelection() {
  console.log('[DEBUG] doSyncSelection start, tableRef:', !!caseTableRef.value)
  if (!caseTableRef.value) { isSyncingTable = false; return }
  // 清除所有勾选
  caseTableRef.value.clearSelection()
  console.log('[DEBUG] clearSelection called')
  // 等 clearSelection 的 @selection-change 事件处理完
  setTimeout(function () {
    if (!caseTableRef.value) { isSyncingTable = false; return }
    // 从表格当前数据中逐行勾选
    var tableData = caseTableRef.value.data || []
    console.log('[DEBUG] tableData length:', tableData.length, 'selectedCaseIds:', [...selectedCaseIds.value])
    var checked = 0
    for (var i = 0; i < tableData.length; i++) {
      if (selectedCaseIds.value.has(tableData[i].id)) {
        caseTableRef.value.toggleRowSelection(tableData[i], true)
        checked++
      }
    }
    console.log('[DEBUG] toggleRowSelection checked', checked, 'rows')
    // 等所有 toggleRowSelection 的 @selection-change 事件处理完
    setTimeout(function () {
      isSyncingTable = false
      console.log('[DEBUG] isSyncingTable = false, sync complete')
    }, 100)
  }, 100)
}

// ========== 右侧表格手动勾选 ==========
function onCaseSelectionChange(rows) {
  console.log('[DEBUG] onCaseSelectionChange called, rows:', rows.length, 'isSyncingTable:', isSyncingTable)
  if (isSyncingTable) {
    console.log('[DEBUG] onCaseSelectionChange SKIPPED (isSyncingTable=true)')
    return
  }
  var pageIds = currentCases.value.map(function (c) { return c.id })
  console.log('[DEBUG] onCaseSelectionChange processing, pageIds:', pageIds, 'row ids:', rows.map(r => r.id))
  pageIds.forEach(function (id) { selectedCaseIds.value.delete(id) })
  rows.forEach(function (r) { selectedCaseIds.value.add(r.id) })
  selectedCaseIds.value = new Set(selectedCaseIds.value)
  console.log('[DEBUG] onCaseSelectionChange done, selectedCaseIds:', [...selectedCaseIds.value])
}

// ========== 左侧树勾选 ==========
async function onTreeCheck(data, checkInfo) {
  // Element Plus @check 事件参数: (data, { checkedNodes, checkedKeys, halfCheckedNodes, halfCheckedKeys })
  // 判断当前节点是否被勾选：看 nodeKey 是否在 checkedKeys 中
  var checked = (checkInfo.checkedKeys || []).includes(data.nodeKey)
  console.log('[DEBUG] onTreeCheck: label:', data.label, 'checked:', checked, 'nodeKey:', data.nodeKey)

  // ★ 关键：在改变任何数据之前先设守卫
  isSyncingTable = true

  if (data.isInterface) {
    // 勾选接口 → 切换到该接口并选中/取消所有用例
    currentInterfaceId.value = data.interfaceId
    currentInterfaceName.value = data.label
    await loadInterfaceCases(data.interfaceId)
    var cases = caseCache.value[data.interfaceId] || []
    console.log('[DEBUG] loaded', cases.length, 'cases for interface', data.interfaceId)
    cases.forEach(function (c) {
      if (checked) selectedCaseIds.value.add(c.id)
      else selectedCaseIds.value.delete(c.id)
    })
  } else {
    // 勾选目录 → 递归选中/取消所有用例（同时切换右侧显示）
    // 同时手动勾选/取消目录下的所有接口子节点
    currentInterfaceId.value = null
    currentInterfaceName.value = data.label + '（全部用例）'
    var allCases = []
    await collectCasesRecursive(data, allCases)
    currentCases.value = allCases
    console.log('[DEBUG] catalog: loaded', allCases.length, 'total cases')
    await selectCatalogRecursive(data, checked)

    // 手动设置目录下所有接口子节点的勾选状态
    if (treeRef.value) {
      setChildNodesChecked(data, checked)
    }
  }
  selectedCaseIds.value = new Set(selectedCaseIds.value)
  console.log('[DEBUG] selectedCaseIds after tree check:', [...selectedCaseIds.value])
  scheduleSyncSelection()
}

// 递归设置目录下所有接口节点的勾选状态
function setChildNodesChecked(node, checked) {
  if (!treeRef.value) return
  if (node.isInterface) {
    treeRef.value.setChecked(node.nodeKey, checked, false)
  }
  if (node.children && node.children.length) {
    for (var i = 0; i < node.children.length; i++) {
      setChildNodesChecked(node.children[i], checked)
    }
  }
}

async function selectCatalogRecursive(node, checked) {
  if (node.isInterface) {
    await loadInterfaceCases(node.interfaceId)
    var cases = caseCache.value[node.interfaceId] || []
    cases.forEach(function (c) {
      if (checked) selectedCaseIds.value.add(c.id)
      else selectedCaseIds.value.delete(c.id)
    })
  }
  if (node.children) {
    for (var i = 0; i < node.children.length; i++) {
      await selectCatalogRecursive(node.children[i], checked)
    }
  }
}

// ========== 确定 ==========
async function onConfirm() {
  if (!selectedCaseIds.value.size) return
  if (!props.currentInterfaceId) {
    ElMessage.warning('未选择目标接口')
    return
  }
  saving.value = true
  try {
    var res = await reuseApiCases({
      source_case_ids: [...selectedCaseIds.value],
      target_interface_id: props.currentInterfaceId,
      target_case_kind: props.caseKind,
    })
    var data = res.data.data
    if (data && data.failures && data.failures.length) {
      ElMessage.warning('部分用例复用失败: ' + data.failures.length + ' 条')
    } else {
      ElMessage.success(res.data.message || '复用成功')
    }
    emit('confirmed')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error(e?.message || '复用失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.reuse-dialog-body {
  display: flex;
  gap: 16px;
  height: 60vh;
  min-height: 400px;
}

.reuse-left {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  padding-right: 16px;
}

.reuse-right {
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

// 关键：让标签 span 占满整个节点内容区，阻止空白区域点击冒泡到 el-tree
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

.reuse-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.reuse-count {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
</style>
