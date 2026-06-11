<template>
  <div class="knowledge-list-view app-card">
    <PageHeader :title="t('page.knowledge.title')" />

    <FilterBar @search="load" @reset="resetFilters">
      <template #primary>
        <el-button v-if="canEdit && projectId" type="primary" @click="showUpload = true">
          {{ t('page.knowledge.upload') }}
        </el-button>
      </template>
      <el-input
        v-model="filters.title"
        :placeholder="t('page.knowledge.titleSearchPlaceholder')"
        clearable
      />
      <el-input
        v-if="!projectId"
        v-model="filters.project_name"
        :placeholder="t('page.admin.projects.name')"
        clearable
      />
      <el-select v-model="filters.doc_type" :placeholder="t('page.knowledge.docType')" clearable>
        <el-option :label="t('page.knowledge.docTypeRequirement')" value="requirement" />
        <el-option :label="t('page.knowledge.docTypeApi')" value="api_doc" />
        <el-option :label="t('page.knowledge.docTypeOther')" value="other" />
      </el-select>
      <el-select v-model="filters.index_status" :placeholder="t('page.knowledge.indexStatus')" clearable>
        <el-option
          v-for="s in INDEX_STATUS_FILTER"
          :key="s"
          :label="t(`indexStatus.${s}`)"
          :value="s"
        />
      </el-select>
    </FilterBar>

    <EmptyState
      v-if="!projectId && !loading && !items.length && !hasFilters"
      :title="t('page.knowledge.globalHintTitle')"
      :description="t('page.knowledge.globalHintDesc')"
    />

    <PaginatedTable
      v-else
      v-model:page="page"
      v-model:page-size="pageSize"
      :data="items"
      :loading="loading"
      :total="total"
      @page-change="load"
      @size-change="load"
    >
      <AppTableColumn
        prop="title"
        variant="content"
        :label="t('page.knowledge.titleCol')"
        :min-width="160"
      />
      <AppTableColumn
        prop="module_name"
        variant="flex"
        :label="t('page.knowledge.module')"
      >
        <template #default="{ row }">{{ row.module_name || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn prop="doc_type" variant="flex" :label="t('page.knowledge.docType')">
        <template #default="{ row }">
          <el-tag :type="docTypeTagType(row.doc_type)" size="small">
            {{ docTypeLabel(row.doc_type) }}
          </el-tag>
        </template>
      </AppTableColumn>
      <AppTableColumn variant="flex" :label="t('page.knowledge.indexStatus')" :max-width="112">
        <template #default="{ row }">
          <IndexStatusBadge
            :status="row.index_status"
            :doc-type="row.doc_type"
            :parse-status="row.parse_status"
          />
        </template>
      </AppTableColumn>
      <AppTableColumn prop="updated_at" variant="flex" :label="t('common.updatedAt')" :max-width="168">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </AppTableColumn>
      <AppTableColumn prop="updated_by_username" variant="flex" :label="t('page.knowledge.updatedBy')">
        <template #default="{ row }">{{ row.updated_by_username || '—' }}</template>
      </AppTableColumn>
      <AppTableColumn
        v-if="!projectId"
        prop="project_name"
        variant="flex"
        :label="t('page.admin.projects.name')"
      />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="420">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row)">{{ t('common.view') }}</el-button>
          <el-button link @click="downloadRow(row)">{{ t('common.download') }}</el-button>
          <el-button v-if="canEdit" link @click="openReupload(row)">{{ t('page.knowledge.reupload') }}</el-button>
          <el-button link @click="openHistory(row)">{{ t('page.knowledge.versionHistory') }}</el-button>
          <el-button
            v-if="canEdit && canSaveInterfaces(row)"
            link
            @click="openSaveInterface(row)"
          >
            {{ t('page.knowledge.saveInterfaces') }}
          </el-button>
          <ConfirmDelete v-if="canEdit" :message="t('page.knowledge.deleteConfirm')" @confirm="remove(row)">
            <el-button link type="danger">{{ t('common.delete') }}</el-button>
          </ConfirmDelete>
        </template>
      </AppTableColumn>
    </PaginatedTable>

    <DocumentUploadWizard v-model="showUpload" :loading="uploading" @submit="upload" />
    <DocumentReuploadDialog
      v-model="showReupload"
      :loading="reuploading"
      @submit="submitReupload"
    />
    <KnowledgeVersionHistoryDrawer
      v-model="showHistory"
      :document-id="historyDocId"
      :document="historyDoc"
      @download-version="downloadHistoryVersion"
    />
    <KnowledgeImportWizard
      v-if="importDocId"
      v-model="showImport"
      :document-id="importDocId"
      :version-id="importVersionId"
      :document-title="importDocumentTitle"
      :version-label="importVersionLabel"
      @imported="load"
    />
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  deleteDocument,
  downloadDocument,
  downloadVersion,
  getDocument,
  listDocuments,
  uploadDocument,
  uploadVersion,
} from '@/api/knowledge'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useDownload } from '@/composables/useDownload'
import { INDEX_STATUS } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import { canSaveInterfaces, isDocumentProcessing } from '@/utils/knowledge'
import { usePolling } from '@/composables/usePolling'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import IndexStatusBadge from '@/components/common/IndexStatusBadge.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import DocumentUploadWizard from '@/components/knowledge/DocumentUploadWizard.vue'
import DocumentReuploadDialog from '@/components/knowledge/DocumentReuploadDialog.vue'
import KnowledgeVersionHistoryDrawer from '@/components/knowledge/KnowledgeVersionHistoryDrawer.vue'
import KnowledgeImportWizard from '@/components/knowledge/KnowledgeImportWizard.vue'
import { useKnowledgeStore } from '@/stores/knowledge'

const INDEX_STATUS_FILTER = INDEX_STATUS.filter((s) => s !== 'na' && s !== 'parsing')

const DOC_TYPE_MAP = {
  requirement: { label: '需求文档', tagType: '' },
  api_doc: { label: '接口文档', tagType: 'success' },
  other: { label: '其他', tagType: 'info' },
}

function docTypeLabel(docType) {
  return DOC_TYPE_MAP[docType]?.label ?? docType ?? '—'
}

function docTypeTagType(docType) {
  return DOC_TYPE_MAP[docType]?.tagType ?? 'info'
}

const { t } = useI18n()
const router = useRouter()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const knowledgeStore = useKnowledgeStore()
const { downloadFromResponse } = useDownload()
const { page, pageSize, total } = usePagination()

const filters = reactive({ title: '', project_name: '', doc_type: '', index_status: '' })
const items = ref([])
const loading = ref(false)
const showUpload = ref(false)
const uploading = ref(false)
const showReupload = ref(false)
const reuploading = ref(false)
const reuploadDocId = ref(null)
const showHistory = ref(false)
const historyDocId = ref(null)
const historyDoc = ref(null)
const showImport = ref(false)
const importDocId = ref(null)
const importVersionId = ref(null)
const importDocumentTitle = ref('')
const importVersionLabel = ref('')

const hasFilters = computed(
  () => !!(filters.title || filters.project_name || filters.doc_type || filters.index_status),
)

const hasProcessingDocs = computed(() => items.value.some((row) => isDocumentProcessing(row)))

const listPolling = usePolling(
  async () => {
    await load({ silent: true })
  },
  {
    interval: 3000,
    until: () => !hasProcessingDocs.value,
  },
)

async function load(opts = {}) {
  const scoped = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    title: filters.title || undefined,
    project_name: !projectId.value ? filters.project_name || undefined : undefined,
    doc_type: filters.doc_type || undefined,
    index_status: filters.index_status || undefined,
  })
  const params = scoped ?? {
    page: page.value,
    page_size: pageSize.value,
    title: filters.title || undefined,
    project_name: filters.project_name || undefined,
    doc_type: filters.doc_type || undefined,
    index_status: filters.index_status || undefined,
  }
  if (!opts.silent) loading.value = true
  try {
    const res = await listDocuments(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    if (!opts.silent) loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { title: '', project_name: '', doc_type: '', index_status: '' })
  page.value = 1
  load()
}

function goDetail(row) {
  router.push(`/docs/knowledge/${row.id}`)
}

async function downloadRow(row) {
  const res = await downloadDocument(row.id)
  downloadFromResponse(res, row.title || 'document')
}

function openReupload(row) {
  reuploadDocId.value = row.id
  showReupload.value = true
}

async function submitReupload(formData) {
  reuploading.value = true
  try {
    await uploadVersion(reuploadDocId.value, formData)
    ElMessage.success(t('page.knowledge.reuploadOk'))
    showReupload.value = false
    await load()
    listPolling.start()
  } finally {
    reuploading.value = false
  }
}

function openHistory(row) {
  historyDocId.value = row.id
  historyDoc.value = row
  showHistory.value = true
}

async function downloadHistoryVersion(version) {
  const res = await downloadVersion(historyDocId.value, version.id)
  downloadFromResponse(res, `${historyDoc.value?.title || 'doc'}_${version.version_label}`)
}

async function openSaveInterface(row) {
  importDocId.value = row.id
  importVersionId.value = row.current_version_id ?? null
  importDocumentTitle.value = row.title ?? ''
  importVersionLabel.value = row.version_label ?? ''
  if (!importVersionId.value) {
    const detail = await getDocument(row.id)
    const data = detail.data.data
    importVersionId.value = data?.current_version?.id ?? null
    importVersionLabel.value =
      data?.version_label ?? data?.current_version?.version_label ?? importVersionLabel.value
  }
  if (!importVersionId.value) {
    ElMessage.warning(t('page.knowledge.noVersion'))
    return
  }
  showImport.value = true
}

async function remove(row) {
  await deleteDocument(row.id)
  ElMessage.success(t('common.deleted'))
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
    await load()
    listPolling.start()
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  await load()
  if (hasProcessingDocs.value) listPolling.start()
})

watch(
  () => knowledgeStore.refreshSeq,
  () => {
    load({ silent: true })
  },
)

onActivated(() => {
  load({ silent: true })
})
</script>
