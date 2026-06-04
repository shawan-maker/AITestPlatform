<template>
  <ul v-if="interfaces.length" class="ui-tree-list api-interface-list">
    <li
      v-for="(iface, index) in interfaces"
      :key="iface.id"
      class="tree-node"
    >
      <div
        class="ui-tree-node-row ui-tree-node-row--interface"
        :class="{ 'is-active': selectedInterfaceId === iface.id }"
        :draggable="canEdit"
        @dragstart="onDragStart($event, index)"
        @dragover.prevent="onDragOver($event, index)"
        @drop.prevent="onDrop(index)"
        @click="$emit('select', iface)"
      >
        <el-tag size="small" :type="methodTagType(iface.method)" class="method-tag">
          {{ iface.method }}
        </el-tag>
        <span class="ui-tree-node-label">{{ ifaceLabel(iface) }}</span>
        <el-dropdown
          v-if="canEdit"
          trigger="click"
          @command="(cmd) => $emit('command', cmd, iface)"
        >
          <TreeNodeMenuTrigger />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit">{{ t('common.edit') }}</el-dropdown-item>
              <el-dropdown-item command="copy">{{ t('common.copy') }}</el-dropdown-item>
              <el-dropdown-item command="delete" divided>{{ t('common.delete') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </li>
    <li v-if="hasMore" class="load-more-row">
      <el-button link type="primary" :loading="loadingMore" @click="$emit('load-more')">
        {{ t('page.apiCases.loadMore') }}
      </el-button>
    </li>
  </ul>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import TreeNodeMenuTrigger from '@/components/common/TreeNodeMenuTrigger.vue'

const props = defineProps({
  interfaces: { type: Array, default: () => [] },
  selectedInterfaceId: { type: Number, default: null },
  canEdit: { type: Boolean, default: true },
  hasMore: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'command', 'load-more', 'reorder'])

const { t } = useI18n()

let dragFromIndex = null

function ifaceLabel(iface) {
  return iface.summary ? `${iface.path} — ${iface.summary}` : iface.path
}

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function onDragStart(event, index) {
  dragFromIndex = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDragOver(event, index) {
  if (dragFromIndex != null && dragFromIndex !== index) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(toIndex) {
  const from = dragFromIndex
  dragFromIndex = null
  if (from == null || from === toIndex) return
  emit('reorder', { fromIndex: from, toIndex })
}
</script>

<style scoped lang="scss">
.api-interface-list {
  padding-left: 9px;
  margin: 2px 0 4px;
}

.ui-tree-node-row--interface {
  color: var(--text-primary);
  font-weight: 400;
  gap: 8px;

  .method-tag {
    flex-shrink: 0;
    min-width: 52px;
    text-align: center;
  }
}

.load-more-row {
  list-style: none;
  padding: 4px 10px 4px 14px;
}
</style>
