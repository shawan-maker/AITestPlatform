import { ref, shallowRef } from 'vue'

const CHAR_WIDTH = 8
const CELL_PADDING = 28
const MIN_FLEX = 80
const MIN_CONTENT = 140
const MAX_CONTENT = 520

function measureContentWidth(col, data) {
  const prop = col.prop
  const labelLen = (col.label ?? '').length
  let maxLen = labelLen
  if (prop && Array.isArray(data)) {
    for (const row of data) {
      const value = row[prop]
      if (value != null) maxLen = Math.max(maxLen, String(value).length)
    }
  }
  const min = col.minWidth ?? MIN_CONTENT
  return Math.min(MAX_CONTENT, Math.max(min, maxLen * CHAR_WIDTH + CELL_PADDING))
}

function distributeWidths(cols, bases, remaining, mins) {
  const next = {}
  const count = cols.length
  if (!count) return next

  let baseSum = bases.reduce((sum, w) => sum + w, 0)
  if (baseSum <= 0) {
    const even = Math.max(MIN_FLEX, Math.floor(remaining / count))
    cols.forEach((col, index) => {
      next[col.id] =
        index === count - 1 ? Math.max(MIN_FLEX, remaining - even * (count - 1)) : even
    })
    return next
  }

  if (baseSum <= remaining) {
    const extra = remaining - baseSum
    cols.forEach((col, index) => {
      next[col.id] = Math.round(bases[index] + (bases[index] / baseSum) * extra)
    })
  } else {
    let scale = remaining / baseSum
    cols.forEach((col, index) => {
      next[col.id] = Math.max(mins[index], Math.floor(bases[index] * scale))
    })
    let used = Object.values(next).reduce((sum, w) => sum + w, 0)
    let delta = remaining - used
    let i = 0
    while (delta !== 0 && i < count * 4) {
      const col = cols[i % count]
      const step = delta > 0 ? 1 : -1
      const nextWidth = next[col.id] + step
      if (nextWidth >= mins[i % count]) {
        next[col.id] = nextWidth
        delta -= step
      }
      i += 1
    }
  }

  return next
}

export function useTableColumnLayout(tableRef, dataRef) {
  const columns = shallowRef(new Map())
  const widths = ref({})

  function touchColumns() {
    columns.value = new Map(columns.value)
  }

  function register(col) {
    columns.value.set(col.id, { ...col, userWidth: col.userWidth ?? null })
    touchColumns()
    scheduleLayout()
  }

  function unregister(id) {
    columns.value.delete(id)
    touchColumns()
    scheduleLayout()
  }

  let layoutTimer = null
  function scheduleLayout() {
    clearTimeout(layoutTimer)
    layoutTimer = setTimeout(() => applyLayout(), 32)
  }

  function getTableWidth() {
    const el = tableRef.value?.$el
    return el?.clientWidth ?? 0
  }

  function findColumnByTableColumn(column) {
    const key = column?.property || column?.columnKey || column?.label
    if (!key) return null
    for (const col of columns.value.values()) {
      if (col.prop === key || col.columnKey === key || col.label === key) return col
    }
    return null
  }

  function applyLayout() {
    const tableWidth = getTableWidth()
    if (tableWidth <= 0) return

    const list = [...columns.value.values()]
    const fixedCols = list.filter((c) => c.variant === 'fixed')
    const contentCols = list.filter((c) => c.variant === 'content')
    const flexCols = list.filter((c) => c.variant === 'flex')
    const data = dataRef?.value ?? []
    const next = {}
    let fixedUsed = 0

    for (const col of fixedCols) {
      const w = col.userWidth ?? col.width ?? 100
      next[col.id] = w
      fixedUsed += w
    }

    const adjustable = [...contentCols, ...flexCols]
    const remaining = Math.max(0, tableWidth - fixedUsed)
    if (!adjustable.length) {
      widths.value = { ...next }
      return
    }

    const bases = adjustable.map((col) => {
      if (col.userWidth) return col.userWidth
      if (col.variant === 'content') return measureContentWidth(col, data)
      return MIN_FLEX
    })
    const mins = adjustable.map((col) =>
      col.variant === 'content' ? (col.minWidth ?? MIN_CONTENT) : MIN_FLEX,
    )
    Object.assign(next, distributeWidths(adjustable, bases, remaining, mins))
    widths.value = { ...next }
  }

  function onHeaderDragend(newWidth, oldWidth, column) {
    const target = findColumnByTableColumn(column)
    if (!target || target.variant === 'fixed') return

    target.userWidth = newWidth
    const delta = newWidth - oldWidth
    const adjustable = [...columns.value.values()].filter(
      (c) => c.id !== target.id && c.variant !== 'fixed',
    )
    if (!adjustable.length || delta === 0) {
      applyLayout()
      return
    }

    const per = delta / adjustable.length
    for (const col of adjustable) {
      const current = col.userWidth ?? widths.value[col.id] ?? MIN_FLEX
      const min = col.variant === 'content' ? (col.minWidth ?? MIN_CONTENT) : MIN_FLEX
      col.userWidth = Math.max(min, Math.round(current - per))
    }
    applyLayout()
  }

  return {
    register,
    unregister,
    widths,
    applyLayout,
    onHeaderDragend,
    scheduleLayout,
  }
}
