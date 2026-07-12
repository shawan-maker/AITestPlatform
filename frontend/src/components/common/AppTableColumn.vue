<template>
  <el-table-column
    v-bind="columnAttrs"
    :prop="prop"
    :label="label"
    :type="type"
    :column-key="columnKey"
    :width="resolvedWidth"
    :min-width="resolvedMinWidth"
    :show-overflow-tooltip="showOverflowTooltip"
    :align="columnAlign"
    :header-align="columnAlign"
    :class-name="columnCellClass"
    :label-class-name="columnHeaderClass"
    :fixed="resolvedFixed"
  >
    <template v-if="$slots.default" #default="scope">
      <div v-if="actions" class="app-table-column__actions">
        <slot v-bind="scope" />
      </div>
      <slot v-else v-bind="scope" />
    </template>
    <template v-if="$slots.header" #header="scope">
      <slot name="header" v-bind="scope" />
    </template>
  </el-table-column>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, useAttrs, useId, watch } from 'vue'
import { TABLE_LAYOUT_KEY } from '@/components/common/tableLayoutKey'

const props = defineProps({
  variant: {
    type: String,
    default: 'flex',
    validator: (v) => ['flex', 'content', 'fixed'].includes(v),
  },
  prop: { type: String, default: undefined },
  label: { type: String, default: undefined },
  type: { type: String, default: undefined },
  columnKey: { type: String, default: undefined },
  width: { type: [Number, String], default: undefined },
  minWidth: { type: [Number, String], default: undefined },
  maxWidth: { type: [Number, String], default: undefined },
  showOverflowTooltip: { type: Boolean, default: true },
  actions: { type: Boolean, default: false },
  buttonLabels: { type: Array, default: () => [] },
})

const attrs = useAttrs()
const columnId = useId()
const layout = inject(TABLE_LAYOUT_KEY, null)

const columnAttrs = computed(() => {
  const { variant, prop, label, type, columnKey, width, minWidth, showOverflowTooltip, ...rest } = {
    ...props,
    ...attrs,
  }
  return rest
})

const resolvedWidth = computed(() => {
  if (props.variant === 'fixed' && !layout?.widths.value?.[columnId]) {
    return props.width ?? 100
  }
  const assigned = layout?.widths.value?.[columnId]
  if (assigned) return assigned
  return undefined
})

const resolvedMinWidth = computed(() => {
  if (props.variant === 'fixed') return undefined
  if (layout?.widths.value?.[columnId]) return undefined
  if (props.variant === 'content') return props.minWidth ?? 140
  if (!layout && props.variant === 'flex') return props.minWidth ?? 80
  return undefined
})

const columnAlign = computed(() => (props.variant === 'content' ? 'left' : 'center'))

const resolvedFixed = computed(() => {
  // Explicit fixed prop takes precedence
  if (attrs.fixed !== undefined) return attrs.fixed
  // Actions columns auto-fix to right
  if (props.actions) return 'right'
  return undefined
})

const columnCellClass = computed(() =>
  props.variant === 'content' ? 'app-table-col--content' : 'app-table-col--center',
)

const columnHeaderClass = computed(() => `${columnCellClass.value} app-table-col__header`)

function registerColumn() {
  layout?.register({
    id: columnId,
    type: props.type,
    variant: props.type === 'selection' ? 'fixed' : props.variant,
    prop: props.prop,
    label: props.label,
    columnKey: props.columnKey,
    actions: props.actions,
    buttonLabels: props.buttonLabels,
    width: props.type === 'selection' ? (props.width ?? 48) : props.width,
    minWidth: props.minWidth ? Number(props.minWidth) : undefined,
    maxWidth: props.maxWidth ? Number(props.maxWidth) : undefined,
  })
}

onMounted(() => {
  registerColumn()
})

watch(() => props.buttonLabels, () => {
  registerColumn()
}, { deep: true })

onUnmounted(() => {
  layout?.unregister(columnId)
})
</script>

<style scoped lang="scss">
.app-table-column__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  width: 100%;
  gap: 8px;
}
</style>
