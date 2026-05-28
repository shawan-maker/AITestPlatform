<template>
  <div class="task-list-view app-card">
    <PageHeader :title="t('page.test.tasks.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
        </template>
        <el-select v-model="filters.task_type" :placeholder="t('page.test.taskType')" clearable>
          <el-option v-for="tt in TASK_TYPES" :key="tt" :label="tt" :value="tt" />
        </el-select>
      </FilterBar>
      <PaginatedTable v-model:page="page" v-model:page-size="pageSize" :data="items" :loading="loading" :total="total" @page-change="load">
        <AppTableColumn prop="name" variant="content" :label="t('common.name')" />
        <AppTableColumn prop="task_type" variant="flex" :label="t('page.test.taskType')" />
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/test/tasks/${row.id}`)">{{ t('common.view') }}</el-button>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { listTasks } from '@/api/testManagement'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { TASK_TYPES } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ task_type: '' })
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value, task_type: filters.task_type || undefined })
  if (!params) return
  loading.value = true
  try {
    const res = await listTasks(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() { filters.task_type = ''; page.value = 1; load() }
onMounted(load)
</script>
