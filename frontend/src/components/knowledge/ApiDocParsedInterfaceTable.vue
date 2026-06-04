<template>
  <section v-loading="loading" class="api-parsed-section">
    <h3 class="api-parsed-section__title">{{ t('page.knowledge.parsedInterfaces') }}</h3>
    <EmptyState
      v-if="!loading && !displayItems.length"
      :title="emptyTitle"
    />
    <div v-else class="api-parsed-section__table-wrap">
      <PaginatedTable :data="displayItems" :show-pagination="false">
      <AppTableColumn prop="method" variant="fixed" :label="t('page.knowledge.parsedMethod')" :width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="methodTagType(row.method)">{{ row.method }}</el-tag>
        </template>
      </AppTableColumn>
      <AppTableColumn prop="path" variant="content" :label="t('page.knowledge.parsedPath')" />
      <AppTableColumn prop="summary" variant="content" :label="t('page.knowledge.parsedSummary')">
        <template #default="{ row }">{{ row.summary || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn
        prop="request_modules"
        variant="content"
        :label="t('page.knowledge.requestModules')"
        :min-width="160"
      >
        <template #default="{ row }">{{ row.request_modules || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn
        prop="api_path"
        variant="content"
        :label="t('page.knowledge.apiDocPath')"
        :min-width="140"
      >
        <template #default="{ row }">{{ row.api_path || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn
        v-if="showSavedColumns"
        prop="module_name"
        variant="content"
        :label="t('page.knowledge.module')"
        :min-width="100"
      >
        <template #default="{ row }">{{ row.module_name || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn
        v-if="showSavedColumns"
        prop="catalog_path"
        variant="content"
        :label="t('page.knowledge.interfaceCatalogPath')"
        :min-width="140"
      >
        <template #default="{ row }">{{ row.catalog_path || '—' }}</template>
      </AppTableColumn>
      </PaginatedTable>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  parseStatus: { type: String, default: '' },
  interfacesSaved: { type: Boolean, default: false },
})

const { t } = useI18n()

const displayItems = computed(() => props.items ?? [])

const showSavedColumns = computed(
  () =>
    props.interfacesSaved ||
    displayItems.value.some((row) => row?.module_name || row?.catalog_path),
)

const emptyTitle = computed(() => {
  if (props.parseStatus === 'parsing' || props.parseStatus === 'pending') {
    return t('page.knowledge.parsing')
  }
  return t('page.knowledge.parsedInterfacesEmpty')
})

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}
</script>

<style scoped lang="scss">
.api-parsed-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-top: 20px;

  &__title {
    margin: 0 0 12px;
    font-size: 16px;
    font-weight: 600;
    flex-shrink: 0;
  }

  &__table-wrap {
    flex: 1;
    min-height: 0;
    overflow-x: auto;
    width: 100%;
  }

  :deep(.paginated-table) {
    flex: 1;
    min-height: 0;
  }
}
</style>
