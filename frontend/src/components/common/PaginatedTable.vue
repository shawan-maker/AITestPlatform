<template>
  <div class="paginated-table">
    <el-table
      v-loading="loading"
      :data="data"
      v-bind="$attrs"
      @selection-change="$emit('selection-change', $event)"
      @row-click="$emit('row-click', $event)"
    >
      <slot />
    </el-table>
    <div v-if="showPagination" class="paginated-table__footer">
      <el-pagination
        v-model:current-page="innerPage"
        v-model:page-size="innerPageSize"
        :total="total"
        :page-sizes="pageSizes"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DEFAULT_PAGE_SIZE } from '@/utils/constants'

const props = defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: DEFAULT_PAGE_SIZE },
  pageSizes: { type: Array, default: () => [10, 20, 50, 100] },
  showPagination: { type: Boolean, default: true },
})

const emit = defineEmits(['update:page', 'update:pageSize', 'page-change', 'size-change', 'selection-change', 'row-click'])

const innerPage = computed({
  get: () => props.page,
  set: (v) => emit('update:page', v),
})

const innerPageSize = computed({
  get: () => props.pageSize,
  set: (v) => emit('update:pageSize', v),
})

function onPageChange(p) {
  emit('page-change', p)
}

function onSizeChange(size) {
  emit('size-change', size)
}
</script>

<style scoped lang="scss">
.paginated-table__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
