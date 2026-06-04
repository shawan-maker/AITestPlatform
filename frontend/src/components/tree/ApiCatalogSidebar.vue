<template>
  <CatalogTreeSidebar
    :keyword="keyword"
    :root-icon="Folder"
    :search-placeholder="t('page.apiCases.searchInterfaces')"
    :root-label="t('page.apiCases.allInterfaces')"
    :is-root-active="selectedCatalogId == null && !selectedInterfaceId"
    :add-catalog-label="t('page.apiCases.addCatalog')"
    :can-edit="canEdit"
    @update:keyword="$emit('update:keyword', $event)"
    @select-root="$emit('select-root')"
    @section-command="$emit('section-command', $event)"
  >
    <ApiCatalogTreeNode
      v-if="filteredCatalogNodes.length"
      :catalog-nodes="filteredCatalogNodes"
      :selected-catalog-id="selectedCatalogId"
      :selected-interface-id="selectedInterfaceId"
      :expanded-catalog-ids="expandedCatalogIds"
      :interfaces-by-catalog="interfacesByCatalog"
      :can-edit="canEdit"
      :dragging-catalog-id="draggingCatalogId"
      @select-catalog="(id) => $emit('select-catalog', id)"
      @select-interface="(iface, catalogId) => $emit('select-interface', iface, catalogId)"
      @toggle-expand="(id) => $emit('toggle-expand', id)"
      @catalog-command="(cmd, node) => $emit('catalog-command', cmd, node)"
      @interface-command="(cmd, iface) => $emit('interface-command', cmd, iface)"
      @load-more-interfaces="(id) => $emit('load-more-interfaces', id)"
      @interface-reorder="(payload) => $emit('interface-reorder', payload)"
      @catalog-drop="(payload) => $emit('catalog-drop', payload)"
    />
    <p v-else-if="keyword.trim()" class="tree-empty-hint">—</p>
  </CatalogTreeSidebar>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Folder } from '@element-plus/icons-vue'
import CatalogTreeSidebar from '@/components/tree/CatalogTreeSidebar.vue'
import ApiCatalogTreeNode from '@/components/tree/ApiCatalogTreeNode.vue'
const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  keyword: { type: String, default: '' },
  selectedCatalogId: { type: Number, default: null },
  selectedInterfaceId: { type: Number, default: null },
  expandedCatalogIds: { type: Array, default: () => [] },
  interfacesByCatalog: { type: Object, default: () => ({}) },
  canEdit: { type: Boolean, default: true },
  draggingCatalogId: { type: Number, default: null },
})

defineEmits([
  'update:keyword',
  'select-root',
  'select-catalog',
  'select-interface',
  'toggle-expand',
  'section-command',
  'catalog-command',
  'interface-command',
  'load-more-interfaces',
  'interface-reorder',
  'catalog-drop',
])

const { t } = useI18n()

function filterCatalogTree(nodes, kw) {
  const result = []
  for (const node of nodes) {
    const children = node.children?.length ? filterCatalogTree(node.children, kw) : []
    const nameMatch = node.name?.toLowerCase().includes(kw)
    if (nameMatch || children.length) {
      result.push({ ...node, children })
    }
  }
  return result
}

const filteredCatalogNodes = computed(() => {
  const kw = props.keyword.trim().toLowerCase()
  if (!kw) return props.catalogNodes
  return filterCatalogTree(props.catalogNodes, kw)
})
</script>

<style scoped>
.tree-empty-hint {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
