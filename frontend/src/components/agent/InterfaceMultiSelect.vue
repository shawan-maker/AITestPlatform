<template>
  <div class="interface-multi-select">
    <div class="interface-multi-select__trigger" @click="showDialog = true">
      <span v-if="selectedList.length" class="interface-multi-select__count">
        {{ t('page.agent.selectedInterfaces', { count: selectedList.length }) }}
      </span>
      <span v-else class="interface-multi-select__placeholder">
        {{ t('page.agent.selectInterfaces') }}
      </span>
      <el-icon style="margin-left: 4px"><ArrowDown /></el-icon>
    </div>

    <el-dialog
      v-model="showDialog"
      :title="t('page.agent.interfaceMultiSelectTitle')"
      width="640px"
      destroy-on-close
      @open="onOpen"
    >
      <div class="interface-multi-select__body">
        <el-input
          v-model="searchKey"
          :placeholder="t('page.agent.selectInterfaces')"
          clearable
          :prefix-icon="Search"
          class="interface-multi-select__search"
        />
        <div class="interface-multi-select__tree" v-loading="treeLoading">
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
              <span class="tree-node-label">
                <el-tag
                  v-if="data.isInterface && data.method"
                  :type="methodTagType(data.method)"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ data.method }}
                </el-tag>
                <el-icon v-else-if="!data.isInterface" style="margin-right: 4px"><Folder /></el-icon>
                {{ data.label }}
                <span v-if="!data.isInterface && data.interfaceCount" class="tree-node-count">
                  ({{ data.interfaceCount }})
                </span>
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <template #footer>
        <div class="interface-multi-select__footer">
          <span class="interface-multi-select__summary">
            {{ t('page.agent.selectedInterfaces', { count: checkedInterfaceIds.size }) }}
          </span>
          <div>
            <el-button @click="showDialog = false">{{ t('common.cancel') }}</el-button>
            <el-button type="primary" @click="onConfirm">{{ t('common.confirm') }}</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, Folder, ArrowDown } from '@element-plus/icons-vue'
import { getApiCatalogTree, listInterfacesByCatalog } from '@/api/apiTest'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  projectId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const showDialog = ref(false)
const treeRef = ref(null)
const treeLoading = ref(false)
const searchKey = ref('')
const catalogTree = ref([])
const interfacesByCatalog = ref({})
const checkedInterfaceIds = ref(new Set(props.modelValue || []))

const treeProps = { children: 'children', label: 'label' }

const selectedList = computed(() => {
  const ids = props.modelValue || []
  const result = []
  for (const catId in interfacesByCatalog.value) {
    for (const iface of interfacesByCatalog.value[catId]) {
      if (ids.includes(iface.id)) {
        result.push(iface)
      }
    }
  }
  return result
})

const treeData = computed(() => buildTreeNodes(catalogTree.value))

const filteredTree = computed(() => {
  if (!searchKey.value) return treeData.value
  return filterTree(treeData.value, searchKey.value.toLowerCase())
})

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function buildTreeNodes(nodes) {
  const result = []
  for (const node of nodes) {
    const treeNode = {
      nodeKey: 'cat-' + node.id,
      label: node.name || '未命名目录',
      isInterface: false,
      catalogId: node.id,
      interfaceCount: node.interface_count || 0,
      children: [],
    }
    const ifaces = interfacesByCatalog.value[node.id] || []
    for (const iface of ifaces) {
      treeNode.children.push({
        nodeKey: 'iface-' + iface.id,
        label: iface.summary || iface.name || iface.path,
        method: iface.method,
        path: iface.path,
        isInterface: true,
        interfaceId: iface.id,
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
  const result = []
  for (const node of nodes) {
    const childMatch = node.children ? filterTree(node.children, keyword) : []
    if (node.label.toLowerCase().includes(keyword) || childMatch.length) {
      result.push({
        ...node,
        children: childMatch.length ? childMatch : node.children,
      })
    }
  }
  return result
}

function onTreeCheck(nodeData, checkState) {
  if (nodeData.isInterface) {
    if (checkState.checked) {
      checkedInterfaceIds.value.add(nodeData.interfaceId)
    } else {
      checkedInterfaceIds.value.delete(nodeData.interfaceId)
    }
  } else {
    // catalog node: check/uncheck all child interfaces
    const childIds = collectInterfaceIds(nodeData)
    for (const id of childIds) {
      if (checkState.checked) {
        checkedInterfaceIds.value.add(id)
      } else {
        checkedInterfaceIds.value.delete(id)
      }
    }
    // update tree check state
    if (treeRef.value) {
      for (const id of childIds) {
        treeRef.value.setChecked('iface-' + id, checkState.checked, false)
      }
    }
  }
}

function collectInterfaceIds(node) {
  const ids = []
  if (node.isInterface) {
    ids.push(node.interfaceId)
  }
  if (node.children) {
    for (const child of node.children) {
      ids.push(...collectInterfaceIds(child))
    }
  }
  return ids
}

function onConfirm() {
  emit('update:modelValue', Array.from(checkedInterfaceIds.value))
  showDialog.value = false
}

async function onOpen() {
  searchKey.value = ''
  checkedInterfaceIds.value = new Set(props.modelValue || [])
  await loadTree()
  // restore checks
  if (treeRef.value) {
    for (const id of checkedInterfaceIds.value) {
      treeRef.value.setChecked('iface-' + id, true, false)
    }
  }
}

async function loadTree() {
  if (!props.projectId) return
  treeLoading.value = true
  try {
    const res = await getApiCatalogTree({ project_id: props.projectId })
    catalogTree.value = res.data.data?.items ?? res.data.data ?? []
    await loadAllCatalogInterfaces(catalogTree.value)
  } catch (e) {
    console.error('加载目录树失败:', e)
  } finally {
    treeLoading.value = false
  }
}

async function loadAllCatalogInterfaces(nodes) {
  for (const node of nodes) {
    if (!interfacesByCatalog.value[node.id]) {
      try {
        const res = await listInterfacesByCatalog(node.id, { page: 1, page_size: 200 })
        interfacesByCatalog.value[node.id] = res.data.data?.items ?? []
      } catch {
        interfacesByCatalog.value[node.id] = []
      }
    }
    if (node.children && node.children.length) {
      await loadAllCatalogInterfaces(node.children)
    }
  }
}

watch(() => props.projectId, () => {
  catalogTree.value = []
  interfacesByCatalog.value = {}
})
</script>

<style scoped lang="scss">
.interface-multi-select__trigger {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 0 16px;
  min-height: 64px;
  min-width: 200px;
  border: 2px solid var(--el-border-color);
  border-radius: 12px;
  font-size: 22px;
  color: var(--el-text-color-primary);
  background: var(--el-bg-color);

  &:hover {
    border-color: var(--el-color-primary);
  }
}

.interface-multi-select__placeholder {
  color: var(--el-text-color-placeholder);
}

.interface-multi-select__count {
  color: var(--el-color-primary);
  font-weight: 500;
}

.interface-multi-select__body {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.interface-multi-select__search {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.interface-multi-select__tree {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 8px;
}

.interface-multi-select__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.interface-multi-select__summary {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.tree-node-label {
  display: inline-flex;
  align-items: center;
  font-size: 14px;
}

.tree-node-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 4px;
}
</style>
