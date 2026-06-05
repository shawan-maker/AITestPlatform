/**
 * useResizable - composable for drag-to-resize sidebar width.
 * Persists to localStorage.
 */
export function useResizable(storageKey, options) {
  const minWidth = options.minWidth || 160
  const maxWidth = options.maxWidth || 360
  const defaultWidth = options.defaultWidth || 220

  let width = ref(defaultWidth)
  let isDragging = ref(false)
  let containerRef = ref(null)

  function onDragStart(e) {
    isDragging.value = true
    const startX = e.clientX
    const startW = width.value

    function onMove(ev) {
      if (!isDragging.value) return
      const delta = ev.clientX - startX
      width.value = Math.min(maxWidth, Math.max(minWidth, startW + delta))
    }

    function onUp() {
      isDragging.value = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      try { localStorage.setItem(storageKey, String(width.value)) } catch {}
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  // Load saved width
  try {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      const w = parseInt(saved, 10)
      if (w >= minWidth && w <= maxWidth) width.value = w
    }
  } catch {}

  return { width, isDragging, containerRef, onDragStart }
}
