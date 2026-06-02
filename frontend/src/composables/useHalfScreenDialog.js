import { computed, onMounted, onUnmounted, ref } from 'vue'

/** 弹窗约占半屏，Monaco 高度随视口自适应 */
export function useHalfScreenDialog(editorOffset = 220) {
  const viewportHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 800)

  function updateViewport() {
    viewportHeight.value = window.innerHeight
  }

  onMounted(() => window.addEventListener('resize', updateViewport))
  onUnmounted(() => window.removeEventListener('resize', updateViewport))

  const editorHeight = computed(() =>
    Math.max(280, Math.floor(viewportHeight.value * 0.5 - editorOffset)),
  )

  return {
    editorHeight,
    dialogWidth: '50vw',
    // 50vh 弹窗垂直居中：上下各留 25vh
    dialogTop: '25vh',
    dialogClass: 'env-function-code-dialog',
  }
}
