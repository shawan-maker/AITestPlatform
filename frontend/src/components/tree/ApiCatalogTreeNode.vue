<template>
  <ul class="ui-tree-list">
    <li v-for="cat in catalogNodes" :key="cat.id" class="tree-node">
      <div
        class="ui-tree-node-row ui-tree-node-row--catalog"
        :class="{ 'is-active': selectedCatalogId === cat.id && !selectedInterfaceId }"
        :draggable="canEdit"
        @dragstart="onCatalogDragStart($event, cat)"
        @dragover.prevent="onCatalogDragOver($event, cat)"
        @drop.prevent="onCatalogDrop(cat)"
        @click="onSelectCatalog(cat)"
      >
        <el-icon
          v-if="hasExpandableContent(cat)"
          class="expand-toggle"
          @click.stop="toggleExpand(cat.id)"
        >
          <ArrowDown v-if="isExpanded(cat.id)" />
          <ArrowRight v-else />
        </el-icon>
        <span v-else class="expand-placeholder" />
        <el-icon class="ui-tree-node-icon"><Folder /></el-icon>
        <span class="ui-tree-node-label">{{ cat.name }}</span>
        <span v-if="cat.interface_count != null" class="ui-tree-node-count">
          {{ t('page.apiCases.interfaceCount', { count: cat.interface_count }) }}
        </span>
        <el-dropdown
          v-if="canEdit"
          trigger="click"
          @command="(cmd) => $emit('catalog-command', cmd, cat)"
        >
          <TreeNodeMenuTrigger />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="child">{{ t('page.apiCases.addChildCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="rename">{{ t('page.apiCases.renameCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="move">{{ t('page.apiCases.moveCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="root">{{ t('page.apiCases.moveToRoot') }}</el-dropdown-item>
              <el-dropdown-item command="delete" divided>{{ t('common.delete') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="isExpanded(cat.id)" class="ui-tree-nested">
        <ApiInterfaceTreeList
          v-if="interfaceState(cat.id)?.items?.length"
          :interfaces="interfaceState(cat.id).items"
          :selected-interface-id="selectedInterfaceId"
          :can-edit="canEdit"
          :has-more="interfaceState(cat.id).hasMore"
          :loading-more="interfaceState(cat.id).loadingMore"
          @select="(iface) => $emit('select-interface', iface, cat.id)"
          @command="(cmd, iface) => $emit('interface-command', cmd, iface)"
          @load-more="$emit('load-more-interfaces', cat.id)"
          @reorder="(payload) => $emit('interface-reorder', { ...payload, catalogId: cat.id })"
        />
        <ApiCatalogTreeNode
          v-if="cat.children?.length"
          :catalog-nodes="cat.children"
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
      </div>
    </li>
  </ul>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowDown, ArrowRight, Folder } from '@element-plus/icons-vue'
import TreeNodeMenuTrigger from '@/components/common/TreeNodeMenuTrigger.vue'
import ApiInterfaceTreeList from '@/components/tree/ApiInterfaceTreeList.vue'

defineOptions({ name: 'ApiCatalogTreeNode' })

const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  selectedCatalogId: { type: Number, default: null },
  selectedInterfaceId: { type: Number, default: null },
  expandedCatalogIds: { type: Array, default: () => [] },
  interfacesByCatalog: { type: Object, default: () => ({}) },
  canEdit: { type: Boolean, default: true },
  draggingCatalogId: { type: Number, default: null },
})

const emit = defineEmits([
  'select-catalog',
  'select-interface',
  'toggle-expand',
  'catalog-command',
  'interface-command',
  'load-more-interfaces',
  'interface-reorder',
  'catalog-drop',
])

const { t } = useI18n()
const localDraggingId = ref(null)

function isExpanded(catalogId) {
  return props.expandedCatalogIds.includes(catalogId)
}

function interfaceState(catalogId) {
  return props.interfacesByCatalog[catalogId] || { items: [], hasMore: false, loadingMore: false }
}

function hasExpandableContent(cat) {
  return (cat.children?.length ?? 0) > 0 || (cat.interface_count ?? 0) > 0
}

function toggleExpand(catalogId) {
  emit('toggle-expand', catalogId)
}

function onSelectCatalog(cat) {
  emit('select-catalog', cat.id)
  if (hasExpandableContent(cat) && !isExpanded(cat.id)) {
    emit('toggle-expand', cat.id)
  }
}

function onCatalogDragStart(event, cat) {
  if (!props.canEdit) return
  localDraggingId.value = cat.id
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(cat.id))
}

function onCatalogDragOver(event, cat) {
  const dragId = props.draggingCatalogId ?? localDraggingId.value
  if (dragId && dragId !== cat.id) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onCatalogDrop(targetCat) {
  const dragId = props.draggingCatalogId ?? localDraggingId.value
  localDraggingId.value = null
  if (!dragId || dragId === targetCat.id) return
  emit('catalog-drop', { catalogId: dragId, targetParentId: targetCat.id })
}
</script>

<style scoped lang="scss">
.expand-toggle,
.expand-placeholder {
  flex-shrink: 0;
  width: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.expand-placeholder {
  display: inline-block;
}

.ui-tree-node-count {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
