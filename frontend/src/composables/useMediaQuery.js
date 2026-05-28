import { onMounted, onUnmounted, ref } from 'vue'

export function useMediaQuery(query) {
  const matches = ref(false)

  let mql

  function update() {
    matches.value = mql?.matches ?? false
  }

  onMounted(() => {
    mql = window.matchMedia(query)
    update()
    mql.addEventListener('change', update)
  })

  onUnmounted(() => {
    mql?.removeEventListener('change', update)
  })

  return matches
}

export function useIsMobileSidebar() {
  return useMediaQuery('(max-width: 991px)')
}
