<template>
  <ul class="ui-tree-list">
    <li v-for="cat in catalogNodes" :key="cat.id" class="tree-node">
      <div
        class="ui-tree-node-row ui-tree-node-row--catalog"
        :class="{ 'is-active': selectedCatalogId === cat.id }"
        :draggable="canEdit"
        @dragstart="onCatalogDragStart($event, cat)"
        @dragover.prevent="onCatalogDragOver($event, cat)"
        @drop.prevent="onCatalogDrop(cat)"
        @click="$emit('select-catalog', cat.id)"
      >
        <el-icon
          v-if="cat.children?.length"
          class="expand-toggle"
          @click.stop="toggleExpand(cat.id)"
        >
          <ArrowDown v-if="isExpanded(cat.id)" />
          <ArrowRight v-else />
        </el-icon>
        <span v-else class="expand-placeholder" />
        <el-icon class="ui-tree-node-icon"><Folder /></el-icon>
        <span class="ui-tree-node-label">{{ cat.name }}</span>
        <span v-if="cat.case_count != null" class="ui-tree-node-count">
          {{ t('page.functional.caseCount', { count: cat.case_count }) }}
        </span>
        <el-dropdown
          v-if="canEdit"
          trigger="click"
          @command="(cmd) => $emit('catalog-command', cmd, cat)"
        >
          <TreeNodeMenuTrigger />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="child">{{ t('page.functional.addCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="rename">{{ t('page.functional.renameCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="move">{{ t('page.functional.moveCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="up">{{ t('page.functional.moveUp') }}</el-dropdown-item>
              <el-dropdown-item command="down">{{ t('page.functional.moveDown') }}</el-dropdown-item>
              <el-dropdown-item command="root">{{ t('page.functional.moveToRoot') }}</el-dropdown-item>
              <el-dropdown-item command="delete" divided>{{ t('common.delete') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="isExpanded(cat.id) && cat.children?.length" class="ui-tree-nested">
        <FunctionalCatalogTreeNode
          :catalog-nodes="cat.children"
          :selected-catalog-id="selectedCatalogId"
          :expanded-catalog-ids="expandedCatalogIds"
          :can-edit="canEdit"
          @select-catalog="(id) => $emit('select-catalog', id)"
          @toggle-expand="(id) => $emit('toggle-expand', id)"
          @catalog-command="(cmd, node) => $emit('catalog-command', cmd, node)"
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

defineOptions({ name: 'FunctionalCatalogTreeNode' })

const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  selectedCatalogId: { type: Number, default: null },
  expandedCatalogIds: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits(['select-catalog', 'toggle-expand', 'catalog-command', 'catalog-drop'])

const { t } = useI18n()
const localDraggingId = ref(null)

function isExpanded(catalogId) {
  return props.expandedCatalogIds.includes(catalogId)
}

function toggleExpand(catalogId) {
  emit('toggle-expand', catalogId)
}

function onCatalogDragStart(event, cat) {
  if (!props.canEdit) return
  localDraggingId.value = cat.id
  event.dataTransfer.effectAllowed = 'move'
}

function onCatalogDragOver(event, cat) {
  if (localDraggingId.value && localDraggingId.value !== cat.id) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onCatalogDrop(targetCat) {
  const dragId = localDraggingId.value
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
