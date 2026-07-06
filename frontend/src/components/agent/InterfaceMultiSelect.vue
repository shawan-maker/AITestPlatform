<template>
  <div class="interface-multi-select">
    <div class="interface-multi-select__trigger" @click="showDialog = true">
      <template v-if="selectedList.length">
        <el-tag
          v-for="iface in selectedList.slice(0, 3)"
          :key="iface.id"
          size="small"
          :type="methodTagType(iface.method)"
          closable
          @close.stop="removeInterface(iface.id)"
          class="interface-multi-select__tag"
        >
          {{ iface.method }} {{ iface.summary || iface.path }}
        </el-tag>
        <el-tag v-if="selectedList.length > 3" size="small" type="info" class="interface-multi-select__tag">
          +{{ selectedList.length - 3 }}
        </el-tag>
      </template>
      <span v-else class="interface-multi-select__placeholder">
        {{ t('page.agent.selectInterfaces') }}
      </span>
      <el-icon class="interface-multi-select__arrow"><ArrowDown /></el-icon>
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

function removeInterface(id) {
  const ids = (props.modelValue || []).filter(v => v !== id)
  emit('update:modelValue', ids)
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

function onTreeCheck() {
  // With check-strictly=false (default), el-tree handles cascade automatically.
  // Just collect all checked leaf nodes (interfaces).
  if (!treeRef.value) return
  const checkedNodes = treeRef.value.getCheckedNodes(true) // true = include half-checked
  const ids = new Set()
  for (const node of checkedNodes) {
    if (node.isInterface && node.interfaceId) {
      ids.add(node.interfaceId)
    }
  }
  checkedInterfaceIds.value = ids
}

function onConfirm() {
  emit('update:modelValue', Array.from(checkedInterfaceIds.value))
  showDialog.value = false
}

async function onOpen() {
  searchKey.value = ''
  checkedInterfaceIds.value = new Set(props.modelValue || [])
  await loadTree()
  // Restore checks: only set leaf (interface) nodes; tree auto-cascades to parents
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

defineExpose({ selectedList })
</script>

<style scoped lang="scss">
.interface-multi-select {
  display: inline-flex;
  vertical-align: middle;
}

.interface-multi-select__trigger {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  cursor: pointer;
  padding: 2px 8px;
  min-height: 32px;
  min-width: 160px;
  max-width: 320px;
  border: 1px solid var(--el-border-color);
  border-radius: $radius-btn;
  font-size: var(--font-size-base);
  color: var(--el-text-color-primary);
  background: var(--el-bg-color);
  transition: border-color 0.15s;

  &:hover {
    border-color: var(--el-color-primary);
  }
}

.interface-multi-select__placeholder {
  color: var(--el-text-color-placeholder);
}

.interface-multi-select__arrow {
  margin-left: 4px;
  flex-shrink: 0;
}

.interface-multi-select__tag {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
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
