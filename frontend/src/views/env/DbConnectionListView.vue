<template>
  <div class="db-list-view app-card">
    <PageHeader :title="t('page.env.db.title')" />
    <FilterBar @search="load" @reset="reset">
      <el-select v-model="filters.bound" :placeholder="t('page.env.db.boundFilter')" clearable>
        <el-option :label="t('page.env.db.bound')" :value="true" />
        <el-option :label="t('page.env.db.unbound')" :value="false" />
      </el-select>
    </FilterBar>
    <PaginatedTable :data="items" :loading="loading" :total="total" v-model:page="page" v-model:page-size="pageSize" @page-change="load">
      <AppTableColumn prop="name" variant="content" :label="t('common.name')" />
      <AppTableColumn prop="db_type" variant="flex" label="Type" />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="160">
        <template #default="{ row }">
          <el-button link @click="testConn(row)">{{ t('page.env.db.test') }}</el-button>
        </template>
      </AppTableColumn>
    </PaginatedTable>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { listDbConnections, testDbConnection } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const { page, pageSize, total } = usePagination()
const filters = reactive({ bound: null })
const items = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const params = withProjectParams({ page: page.value, page_size: pageSize.value, bound: filters.bound ?? undefined }) || { page: page.value, page_size: pageSize.value, bound: filters.bound ?? undefined }
    const res = await listDbConnections(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() { filters.bound = null; page.value = 1; load() }

async function testConn(row) {
  await testDbConnection(row.id)
  ElMessage.success(t('page.env.db.testOk'))
}

onMounted(load)
</script>
