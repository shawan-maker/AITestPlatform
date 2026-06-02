<template>
  <div class="knowledge-list-view app-card">
    <PageHeader :title="t('page.knowledge.title')" />

    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />

    <template v-else>
      <FilterBar @search="load" @reset="resetFilters">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="showUpload = true">{{ t('page.knowledge.upload') }}</el-button>
        </template>
        <el-input v-model="filters.keyword" :placeholder="t('common.keyword')" clearable />
        <el-select v-model="filters.doc_type" :placeholder="t('page.knowledge.docType')" clearable>
          <el-option :label="t('page.knowledge.docTypeRequirement')" value="requirement" />
          <el-option :label="t('page.knowledge.docTypeApi')" value="api_doc" />
        </el-select>
        <el-select v-model="filters.index_status" :placeholder="t('page.knowledge.indexStatus')" clearable>
          <el-option v-for="s in INDEX_STATUS" :key="s" :label="s" :value="s" />
        </el-select>
      </FilterBar>

      <PaginatedTable
        v-model:page="page"
        v-model:page-size="pageSize"
        :data="items"
        :loading="loading"
        :total="total"
        @page-change="load"
        @size-change="load"
      >
        <AppTableColumn prop="title" variant="content" :label="t('page.knowledge.titleCol')" />
        <AppTableColumn prop="module_name" variant="flex" :label="t('page.knowledge.module')" />
        <AppTableColumn variant="fixed" :label="t('page.knowledge.indexStatus')" :width="120">
          <template #default="{ row }"><IndexStatusBadge :status="row.index_status" /></template>
        </AppTableColumn>
        <AppTableColumn prop="updated_at" variant="flex" :label="t('common.updatedAt')">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </AppTableColumn>
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/docs/knowledge/${row.id}`)">{{ t('common.view') }}</el-button>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <DocumentUploadWizard v-model="showUpload" :loading="uploading" @submit="upload" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { listDocuments, uploadDocument } from '@/api/knowledge'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { INDEX_STATUS } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import IndexStatusBadge from '@/components/common/IndexStatusBadge.vue'
import DocumentUploadWizard from '@/components/knowledge/DocumentUploadWizard.vue'

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()

const filters = reactive({ keyword: '', doc_type: '', index_status: '' })
const items = ref([])
const loading = ref(false)
const showUpload = ref(false)
const uploading = ref(false)

async function load() {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.keyword || undefined,
    doc_type: filters.doc_type || undefined,
    index_status: filters.index_status || undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listDocuments(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { keyword: '', doc_type: '', index_status: '' })
  page.value = 1
  load()
}

async function upload(formData) {
  const params = withProjectParams()
  if (!params) return
  uploading.value = true
  try {
    await uploadDocument(formData, params)
    ElMessage.success(t('page.knowledge.uploaded'))
    showUpload.value = false
    load()
  } finally {
    uploading.value = false
  }
}

onMounted(load)
</script>
