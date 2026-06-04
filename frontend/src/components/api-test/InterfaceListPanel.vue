<template>
  <div class="interface-list-panel">
    <el-input
      :model-value="searchQuery"
      :placeholder="t('page.apiCases.searchInterfaces')"
      clearable
      class="search-input"
      @update:model-value="$emit('update:searchQuery', $event)"
      @keyup.enter="$emit('search')"
    />

    <PaginatedTable
      :data="interfaces"
      :loading="loading"
      :total="total"
      :page="page"
      :page-size="pageSize"
      row-key="id"
      @row-click="(row) => $emit('select', row)"
      @page-change="$emit('page-change', $event)"
      @size-change="$emit('size-change', $event)"
    >
      <AppTableColumn prop="method" :label="t('page.apiCases.method')" :width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="methodTagType(row.method)">{{ row.method }}</el-tag>
        </template>
      </AppTableColumn>
      <AppTableColumn prop="path" variant="content" :label="t('page.apiCases.path')">
        <template #default="{ row, $index }">
          <span
            v-if="canEdit"
            draggable="true"
            class="drag-handle"
            @dragstart="onDragStart($index)"
            @dragover.prevent
            @drop.prevent="onDrop($index)"
          >⋮⋮</span>
          {{ row.path }}
        </template>
      </AppTableColumn>
      <AppTableColumn prop="summary" variant="content" :label="t('page.apiCases.summary')" />
      <AppTableColumn v-if="canEdit" actions variant="fixed" :label="t('common.actions')" :width="140">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="$emit('edit', row)">{{ t('common.edit') }}</el-button>
          <el-button link @click.stop="$emit('copy', row)">{{ t('common.copy') }}</el-button>
          <el-button link type="danger" @click.stop="$emit('delete', row)">{{ t('common.delete') }}</el-button>
        </template>
      </AppTableColumn>
    </PaginatedTable>
    <EmptyState v-if="!loading && !interfaces.length" :title="t('page.apiCases.noInterface')" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'

defineProps({
  interfaces: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  selectedInterfaceId: { type: Number, default: null },
  searchQuery: { type: String, default: '' },
  canEdit: { type: Boolean, default: true },
})

const emit = defineEmits([
  'update:searchQuery',
  'search',
  'select',
  'edit',
  'copy',
  'delete',
  'page-change',
  'size-change',
  'reorder',
])

const { t } = useI18n()
const dragFromIndex = ref(null)

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function onDragStart(index) {
  dragFromIndex.value = index
}

function onDrop(toIndex) {
  const from = dragFromIndex.value
  dragFromIndex.value = null
  if (from == null || from === toIndex) return
  emit('reorder', { fromIndex: from, toIndex })
}
</script>

<style scoped lang="scss">
.interface-list-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.search-input {
  max-width: 360px;
}

.drag-handle {
  cursor: grab;
  margin-right: 6px;
  color: var(--el-text-color-secondary);
  user-select: none;
}
</style>
