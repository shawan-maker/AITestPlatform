<template>
  <div class="function-list-view app-card">
    <PageHeader :title="t('page.env.function.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="openCreate">{{ t('common.create') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
        </template>
        <el-input v-model="filters.keyword" :placeholder="t('page.env.function.keywordPlaceholder')" clearable />
        <el-input v-model="filters.method_name" :placeholder="t('page.env.function.methodNameFilter')" clearable />
        <el-select
          v-model="filters.environment_id"
          :placeholder="t('page.env.function.boundEnvFilter')"
          clearable
          filterable
        >
          <el-option
            v-for="env in boundEnvOptions"
            :key="env.id"
            :label="env.env_name"
            :value="env.id"
          />
        </el-select>
      </FilterBar>
      <PaginatedTable
        :data="items"
        :loading="loading"
        :total="total"
        v-model:page="page"
        v-model:page-size="pageSize"
        row-key="id"
        @page-change="load"
        @selection-change="onSelectionChange"
      >
        <AppTableColumn v-if="canEdit" type="selection" variant="fixed" :width="50" />
        <AppTableColumn prop="file_name" variant="content" :label="t('page.env.function.fileName')" />
        <AppTableColumn prop="method_names" variant="flex" :label="t('page.env.function.methodNames')">
          <template #default="{ row }">{{ formatNames(row.method_names) }}</template>
        </AppTableColumn>
        <AppTableColumn prop="environment_names" variant="content" :label="t('page.env.function.boundEnvNames')">
          <template #default="{ row }">{{ formatNames(row.environment_names) }}</template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('page.env.function.detail'), t('common.edit'), t('page.env.function.debug'), t('common.delete')]">
          <template #default="{ row }">
            <el-button link @click="openDetail(row)">{{ t('common.detail') }}</el-button>
            <el-button v-if="canEdit" link @click="openEdit(row)">{{ t('common.edit') }}</el-button>
            <el-button link @click="openDebug(row)">{{ t('page.env.function.debug') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <FunctionFileFormDialog v-model="showForm" :file-id="editId" @saved="onSaved" />
    <FunctionDetailDialog
      v-model="showDetail"
      :file-id="detailId"
      @debug="onDetailDebug"
    />
    <FunctionDebugDialog v-model="showDebug" :file="debugFile" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteFunctionFiles,
  deleteFunctionFile,
  getFunctionFile,
  listFunctionBoundEnvironments,
  listFunctionFiles,
} from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import FunctionFileFormDialog from '@/components/env/FunctionFileFormDialog.vue'
import FunctionDetailDialog from '@/components/env/FunctionDetailDialog.vue'
import FunctionDebugDialog from '@/components/env/FunctionDebugDialog.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const filters = reactive({ keyword: '', method_name: '', environment_id: null })
const items = ref([])
const loading = ref(false)
const boundEnvOptions = ref([])
const showForm = ref(false)
const editId = ref(null)
const showDetail = ref(false)
const detailId = ref(null)
const showDebug = ref(false)
const debugFile = ref(null)
const selectedIds = ref([])

function onSelectionChange(rows) {
  selectedIds.value = rows.map(function (r) { return r.id })
}

async function batchRemove() {
  try {
    await ElMessageBox.confirm(
      t('common.batchDeleteConfirm', { count: selectedIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
    const res = await batchDeleteFunctionFiles(selectedIds.value)
    const data = res.data.data
    selectedIds.value = []
    if (data && data.failures && data.failures.length) {
      ElMessage.warning(t('common.batchDeletePartial'))
    } else if (data && data.deleted_ids && data.deleted_ids.length) {
      ElMessage.success(t('common.batchDeleteSuccess', { count: data.deleted_ids.length }))
    }
    loadBoundEnvOptions()
    load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

function formatNames(names) {
  if (!names?.length) return '—'
  return names.join(', ')
}

async function loadBoundEnvOptions() {
  const params = withProjectParams()
  if (!params) {
    boundEnvOptions.value = []
    return
  }
  try {
    const res = await listFunctionBoundEnvironments(params)
    boundEnvOptions.value = res.data.data ?? []
  } catch {
    boundEnvOptions.value = []
  }
}

async function load() {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.keyword || undefined,
    method_name: filters.method_name || undefined,
    environment_id: filters.environment_id ?? undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listFunctionFiles(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.keyword = ''
  filters.method_name = ''
  filters.environment_id = null
  page.value = 1
  load()
}

function openCreate() {
  editId.value = null
  showForm.value = true
}

function openEdit(row) {
  editId.value = row.id
  showForm.value = true
}

function openDetail(row) {
  detailId.value = row.id
  showDetail.value = true
}

async function openDebug(row) {
  const detail = await getFunctionFile(row.id)
  debugFile.value = detail.data.data
  showDebug.value = true
}

async function onDetailDebug(file) {
  showDetail.value = false
  debugFile.value = file
  showDebug.value = true
}

function onSaved() {
  ElMessage.success(t('common.saved'))
  loadBoundEnvOptions()
  load()
}

async function remove(row) {
  if (row.is_bound) {
    await ElMessageBox.confirm(t('page.env.function.deleteBoundHint'), t('common.warning'), { type: 'warning' })
  }
  await deleteFunctionFile(row.id)
  ElMessage.success(t('common.deleted'))
  loadBoundEnvOptions()
  load()
}

watch(projectId, () => {
  loadBoundEnvOptions()
  load()
})

onMounted(() => {
  loadBoundEnvOptions()
  load()
})
</script>
