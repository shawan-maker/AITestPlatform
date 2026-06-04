import { ref, shallowRef } from 'vue'

const CHAR_WIDTH_LATIN = 8
const CHAR_WIDTH_CJK = 14
const CELL_PADDING = 32
const MIN_COL = 56
const MIN_CONTENT = 100
const MAX_CONTENT = 960
const MAX_TIGHT = 200

function stringDisplayWidth(str) {
  let width = 0
  for (const ch of String(str)) {
    width += ch.charCodeAt(0) > 255 ? CHAR_WIDTH_CJK : CHAR_WIDTH_LATIN
  }
  return width
}

function measureTextWidth(col, data, { min = MIN_COL, max = MAX_TIGHT, fallback = '—' } = {}) {
  const labelLen = stringDisplayWidth(col.label ?? '')
  let contentLen = labelLen
  if (col.prop && Array.isArray(data)) {
    for (const row of data) {
      const raw = row[col.prop]
      const text = raw == null || raw === '' ? fallback : String(raw)
      contentLen = Math.max(contentLen, stringDisplayWidth(text))
    }
  }
  const floor = col.minWidth ?? min
  const ceiling = col.maxWidth ?? max
  return Math.min(ceiling, Math.max(floor, contentLen + CELL_PADDING))
}

function measureColumnWidth(col, data) {
  if (col.actions) {
    const labelWidth = stringDisplayWidth(col.label ?? '') + CELL_PADDING
    const hint = col.width ?? 360
    return Math.max(labelWidth, hint)
  }
  if (col.variant === 'content') {
    return measureTextWidth(col, data, {
      min: col.minWidth ?? MIN_CONTENT,
      max: col.maxWidth ?? MAX_CONTENT,
    })
  }
  if (col.variant === 'flex' || (col.variant === 'fixed' && col.prop)) {
    return measureTextWidth(col, data, {
      min: col.minWidth ?? MIN_COL,
      max: col.maxWidth ?? MAX_TIGHT,
    })
  }
  return col.userWidth ?? col.width ?? 100
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
    const data = dataRef?.value ?? []
    const actionCols = list.filter((c) => c.actions)
    const dataCols = list.filter((c) => !c.actions)
    const next = {}

    for (const col of actionCols) {
      next[col.id] = col.userWidth ?? Math.round(measureColumnWidth(col, data))
    }

    const actionUsed = actionCols.reduce((sum, col) => sum + next[col.id], 0)
    const dataBudget = Math.max(0, tableWidth - actionUsed)

    const baseWidths = {}
    let baseSum = 0
    for (const col of dataCols) {
      const w = col.userWidth ?? Math.round(measureColumnWidth(col, data))
      baseWidths[col.id] = w
      baseSum += w
    }

    const count = dataCols.length
    if (!count) {
      widths.value = { ...next }
      return
    }

    const remainder = dataBudget - baseSum
    if (remainder >= 0) {
      const extraEach = Math.floor(remainder / count)
      let leftover = remainder - extraEach * count
      for (const col of dataCols) {
        let w = baseWidths[col.id] + extraEach
        if (leftover > 0) {
          w += 1
          leftover -= 1
        }
        next[col.id] = w
      }
    } else {
      let assigned = 0
      dataCols.forEach((col, index) => {
        if (index === count - 1) {
          next[col.id] = Math.max(MIN_COL, dataBudget - assigned)
        } else {
          const w = Math.max(MIN_COL, Math.floor((baseWidths[col.id] / baseSum) * dataBudget))
          next[col.id] = w
          assigned += w
        }
      })
    }

    widths.value = { ...next }
  }

  function onHeaderDragend(newWidth, _oldWidth, column) {
    const target = findColumnByTableColumn(column)
    if (!target || target.variant === 'fixed' && target.actions) return
    target.userWidth = Math.max(MIN_COL, Math.round(newWidth))
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
