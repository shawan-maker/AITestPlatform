<template>
  <div class="function-list-view app-card">
    <PageHeader :title="t('page.env.function.title')">
      <template #actions>
        <el-button v-if="canEdit && projectId" type="primary" @click="showCreate = true">{{ t('common.create') }}</el-button>
      </template>
    </PageHeader>
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <PaginatedTable v-else :data="items" :loading="loading" :total="total" v-model:page="page" v-model:page-size="pageSize" @page-change="load">
      <el-table-column prop="file_name" :label="t('common.name')">
        <template #default="{ row }">{{ row.file_name || row.name }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="240">
        <template #default="{ row }">
          <el-button link @click="validate(row)">{{ t('page.env.function.validate') }}</el-button>
          <el-button link @click="openDebug(row)">{{ t('page.env.function.debug') }}</el-button>
          <el-button link @click="editCode(row)">{{ t('common.edit') }}</el-button>
        </template>
      </el-table-column>
    </PaginatedTable>

    <FunctionDebugDialog v-model="showDebug" :file="debugFile" />
    <el-dialog v-model="showCode" :title="t('page.env.function.editCode')" width="800px">
      <MonacoJsonEditor v-model="codeForm.source_code" language="python" :height="400" />
      <template #footer>
        <el-button @click="showCode = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveCode">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getFunctionFile, listFunctionFiles, updateFunctionFile, validateFunctionFile } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import FunctionDebugDialog from '@/components/env/FunctionDebugDialog.vue'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const items = ref([])
const loading = ref(false)
const showCreate = ref(false)
const showDebug = ref(false)
const debugFile = ref(null)
const showCode = ref(false)
const codeForm = reactive({ id: null, source_code: '' })

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value })
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

async function validate(row) {
  const detail = await getFunctionFile(row.id)
  const f = detail.data.data
  await validateFunctionFile({ file_name: f.file_name, source_code: f.source_code })
  ElMessage.success(t('page.env.function.valid'))
}

async function openDebug(row) {
  const detail = await getFunctionFile(row.id)
  debugFile.value = detail.data.data
  showDebug.value = true
}

async function editCode(row) {
  const detail = await getFunctionFile(row.id)
  const f = detail.data.data
  codeForm.id = f.id
  codeForm.source_code = f.source_code ?? ''
  showCode.value = true
}

async function saveCode() {
  await updateFunctionFile(codeForm.id, { source_code: codeForm.source_code })
  ElMessage.success(t('common.saved'))
  showCode.value = false
  load()
}

onMounted(load)
</script>
