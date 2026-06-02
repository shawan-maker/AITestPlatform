<template>
  <PaginatedTable
    :data="items"
    :loading="loading"
    :total="total"
    v-model:page="page"
    v-model:page-size="pageSize"
    @page-change="load"
  >
    <AppTableColumn prop="tested_at" variant="flex" :label="t('common.time')" :min-width="168">
      <template #default="{ row }">{{ formatDateTime(row.tested_at) }}</template>
    </AppTableColumn>
    <AppTableColumn prop="success" variant="flex" :label="t('common.status')" :min-width="88">
      <template #default="{ row }">
        <el-tag :type="row.success ? 'success' : 'danger'" size="small">
          {{ row.success ? t('common.success') : t('common.failed') }}
        </el-tag>
      </template>
    </AppTableColumn>
    <AppTableColumn
      prop="message"
      variant="content"
      :label="t('common.message')"
      :show-overflow-tooltip="false"
    >
      <template #default="{ row }">
        <div class="db-test-log-table__message">{{ row.message || '—' }}</div>
      </template>
    </AppTableColumn>
  </PaginatedTable>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDbTestLogs } from '@/api/environment'
import { usePagination } from '@/composables/usePagination'
import { formatDateTime } from '@/utils/format'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const props = defineProps({
  connectionId: { type: Number, default: null },
})

const { t } = useI18n()
const { page, pageSize, total } = usePagination()
const items = ref([])
const loading = ref(false)

async function load() {
  if (!props.connectionId) {
    items.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const res = await getDbTestLogs(props.connectionId, {
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

watch(
  () => props.connectionId,
  () => {
    page.value = 1
    load()
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.db-test-log-table__message {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  text-align: left;
}
</style>
