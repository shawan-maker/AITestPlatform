<template>
  <div ref="rootRef" class="app-table">
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="data"
      border
      table-layout="fixed"
      class="app-table__inner"
      v-bind="$attrs"
      @header-dragend="onHeaderDragend"
      @selection-change="(...args) => emit('selection-change', ...args)"
    >
      <slot />
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, provide, ref, toRef, watch } from 'vue'
import { useTableColumnLayout } from '@/composables/useTableColumnLayout'
import { TABLE_LAYOUT_KEY } from '@/components/common/tableLayoutKey'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['selection-change'])

const rootRef = ref()
const tableRef = ref()
const dataRef = toRef(props, 'data')
const layout = useTableColumnLayout(tableRef, dataRef)
const localeStore = useLocaleStore()

provide(TABLE_LAYOUT_KEY, layout)

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
</script>

<style scoped lang="scss">
.app-table {
  width: 100%;
  min-width: 0;

  &__inner {
    width: 100%;
  }
}
</style>
