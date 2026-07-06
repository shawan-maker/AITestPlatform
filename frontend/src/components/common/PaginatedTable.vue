<template>
  <div ref="rootRef" class="paginated-table">
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="data"
      border
      table-layout="fixed"
      class="paginated-table__table"
      v-bind="$attrs"
      @selection-change="$emit('selection-change', $event)"
      @row-click="$emit('row-click', $event)"
      @header-dragend="onHeaderDragend"
    >
      <slot />
    </el-table>
    <div v-if="showPagination && total > 0" class="paginated-table__footer">
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
import { computed, onMounted, onUnmounted, provide, ref, toRef, watch } from 'vue'
import { DEFAULT_PAGE_SIZE } from '@/utils/constants'
import { useTableColumnLayout } from '@/composables/useTableColumnLayout'
import { TABLE_LAYOUT_KEY } from '@/components/common/tableLayoutKey'
import { useLocaleStore } from '@/stores/locale'

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

const rootRef = ref()
const tableRef = ref()
const dataRef = toRef(props, 'data')
const layout = useTableColumnLayout(tableRef, dataRef)
const localeStore = useLocaleStore()

provide(TABLE_LAYOUT_KEY, layout)

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

function onHeaderDragend(newWidth, oldWidth, column, event) {
  layout.onHeaderDragend(newWidth, oldWidth, column, event)
}

let resizeObserver = null

onMounted(() => {
  layout.scheduleLayout()
  if (typeof ResizeObserver !== 'undefined' && rootRef.value) {
    resizeObserver = new ResizeObserver(() => layout.scheduleLayout())
    resizeObserver.observe(rootRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

watch(
  () => [props.data, props.loading],
  () => layout.scheduleLayout(),
  { deep: true },
)

watch(() => localeStore.locale, () => layout.scheduleLayout())

defineExpose({ tableRef })
</script>

<style scoped lang="scss">
.paginated-table {
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  flex: 1;

  &__table {
    width: 100%;
    flex: 1;
  }

  &__footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
    flex-shrink: 0;
  }
}
</style>
