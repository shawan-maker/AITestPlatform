import { computed, onMounted, onUnmounted, ref } from 'vue'

/** 含大段文本/脚本/用例的弹窗：宽与高约占半屏，垂直居中 */
export function useContentDialog(bodyOffset = 180) {
  const viewportHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 800)

  function updateViewport() {
    viewportHeight.value = window.innerHeight
  }

  onMounted(() => window.addEventListener('resize', updateViewport))
  onUnmounted(() => window.removeEventListener('resize', updateViewport))

  const bodyMaxHeight = computed(() =>
    Math.max(240, Math.floor(viewportHeight.value * 0.5 - bodyOffset)),
  )

  return {
    dialogWidth: '50vw',
    dialogTop: '25vh',
    dialogClass: 'ui-dialog--content-half',
    bodyMaxHeight,
  }
}

/** 半屏弹窗 + Monaco 编辑器高度（脚本类对话框） */
export function useHalfScreenDialog(bodyOffset = 220) {
  const content = useContentDialog(bodyOffset)
  const editorHeight = computed(() => content.bodyMaxHeight.value)
  return {
    ...content,
    editorHeight,
  }
}
