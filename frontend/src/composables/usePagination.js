import { ref } from 'vue'
import { DEFAULT_PAGE_SIZE } from '@/utils/constants'

export function usePagination(initialPageSize = DEFAULT_PAGE_SIZE) {
  const page = ref(1)
  const pageSize = ref(initialPageSize)
  const total = ref(0)

  function onPageChange(p) {
    page.value = p
  }

  function onSizeChange(size) {
    pageSize.value = size
    page.value = 1
  }

  function reset() {
    page.value = 1
    total.value = 0
  }

  return { page, pageSize, total, onPageChange, onSizeChange, reset }
}
