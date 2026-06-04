<template>
  <div class="ui-tree-sidebar catalog-tree-sidebar">
    <el-input
      v-if="showSearch"
      :model-value="keyword"
      :placeholder="searchPlaceholder"
      clearable
      style="margin-bottom: 12px"
      @update:model-value="$emit('update:keyword', $event)"
    />

    <div
      v-if="rootLabel"
      class="ui-tree-node-row ui-tree-node-row--catalog catalog-tree-root"
      :class="{ 'is-active': isRootActive }"
      @click="$emit('select-root')"
    >
      <el-icon class="ui-tree-node-icon"><component :is="rootIcon" /></el-icon>
      <span class="ui-tree-node-label">{{ rootLabel }}</span>
      <el-dropdown
        v-if="canEdit && showAddMenu"
        trigger="click"
        @command="(cmd) => $emit('section-command', cmd)"
      >
        <TreeNodeMenuTrigger />
        <template #dropdown>
          <el-dropdown-menu>
            <slot name="add-menu">
              <el-dropdown-item command="catalog">{{ addCatalogLabel }}</el-dropdown-item>
            </slot>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div v-if="rootLabel" class="ui-tree-nested catalog-tree-children">
      <slot />
    </div>
    <slot v-else />
  </div>
</template>

<script setup>
import { FolderOpened } from '@element-plus/icons-vue'
import TreeNodeMenuTrigger from '@/components/common/TreeNodeMenuTrigger.vue'

defineProps({
  keyword: { type: String, default: '' },
  showSearch: { type: Boolean, default: true },
  searchPlaceholder: { type: String, default: '' },
  rootLabel: { type: String, default: '' },
  rootIcon: { type: Object, default: () => FolderOpened },
  isRootActive: { type: Boolean, default: false },
  addCatalogLabel: { type: String, default: '' },
  canEdit: { type: Boolean, default: true },
  showAddMenu: { type: Boolean, default: true },
})

defineEmits(['update:keyword', 'select-root', 'section-command'])
</script>

<style scoped>
.catalog-tree-root {
  font-size: var(--font-size-base);
}

.catalog-tree-children {
  margin-top: 2px;
}
</style>
