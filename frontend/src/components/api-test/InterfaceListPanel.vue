<template>
  <!-- v2-Q5: 严格12列顺序 + 接口目录完整路径 -->
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
      <!-- v2: 列1 - 序号（隐式在PaginatedTable中） -->
      <AppTableColumn prop="summary" :label="'接口名称'" variant="content" min-width="150">
        <template #default="{ row }">
          {{ row.summary || row.name || '-' }}
        </template>
      </AppTableColumn>
      <AppTableColumn prop="method" :label="'请求方法'" :width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="methodTagType(row.method)">{{ row.method }}</el-tag>
        </template>
      </AppTableColumn>
      <AppTableColumn prop="path" :label="'请求路径'" variant="content" min-width="180">
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
      <!-- v2-Q5: 列5 - 接口目录完整路径 -->
      <AppTableColumn prop="catalog_full_path" :label="'接口目录'" variant="content" min-width="160">
        <template #default="{ row }">
          {{ row.catalog_full_path || '-' }}
        </template>
      </AppTableColumn>
      <!-- 列6-9 创建/更新信息 -->
      <AppTableColumn :label="'创建时间'" :width="160">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </AppTableColumn>
      <AppTableColumn :label="'更新时间'" :width="160">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </AppTableColumn>
      <!-- 列10-12 操作列 -->
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="$emit('edit', row)">编辑</el-button>
          <el-button link @click.stop="$emit('copy', row)">复制</el-button>
          <el-button link type="danger" @click.stop="$emit('delete', row)">删除</el-button>
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

function formatTime(isoStr) {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return isoStr
  }
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
