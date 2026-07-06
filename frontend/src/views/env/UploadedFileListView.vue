<template>
  <div class="uploaded-file-list app-card">
    <PageHeader :title="t('page.env.files.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="reset">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="fileInput?.click()">{{ t('common.upload') }}</el-button>
          <el-button v-if="canEdit && selectedIds.length" type="danger" @click="batchRemove">{{ t('common.batchDelete') }} ({{ selectedIds.length }})</el-button>
          <input ref="fileInput" type="file" hidden @change="onUpload" />
        </template>
        <el-input v-model="filters.keyword" :placeholder="t('page.env.files.keywordPlaceholder')" clearable />
        <el-select
          v-model="filters.uploaded_by_id"
          :placeholder="t('page.env.files.uploaderFilter')"
          clearable
          filterable
        >
          <el-option v-for="u in uploaderOptions" :key="u.id" :label="u.label" :value="u.id" />
        </el-select>
        <el-input v-model="filters.mime_type" :placeholder="t('page.env.files.mimeFilter')" clearable />
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
        <AppTableColumn prop="file_name" variant="content" :label="t('common.name')" />
        <AppTableColumn prop="storage_path" variant="flex" :label="t('page.env.files.storagePath')">
          <template #default="{ row }">files/{{ row.project_id }}/{{ row.file_name }}</template>
        </AppTableColumn>
        <AppTableColumn prop="file_size" variant="flex" :label="t('common.size')">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </AppTableColumn>
        <AppTableColumn prop="mime_type" variant="flex" :label="t('page.env.files.mimeType')" />
        <AppTableColumn prop="uploaded_by_id" variant="flex" :label="t('page.env.files.uploader')">
          <template #default="{ row }">{{ uploaderLabel(row.uploaded_by_id) }}</template>
        </AppTableColumn>
        <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')" />
        <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('common.view'), t('common.download'), t('common.delete')]">
          <template #default="{ row }">
            <el-button link @click="openPreview(row)">{{ t('common.view') }}</el-button>
            <el-button link @click="download(row)">{{ t('common.download') }}</el-button>
            <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
              <el-button link type="danger">{{ t('common.delete') }}</el-button>
            </ConfirmDelete>
          </template>
        </AppTableColumn>
      </PaginatedTable>
    </template>

    <FilePreviewDialog
      v-model="showPreview"
      :file-id="previewFile?.id"
      :file-name="previewFile?.file_name"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchDeleteUploadedFiles, deleteUploadedFile, downloadUploadedFile, listUploadedFiles, uploadFile } from '@/api/environment'
import { lookupUsers } from '@/api/users'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useDownload } from '@/composables/useDownload'
import { formatFileSize } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import FilePreviewDialog from '@/components/env/FilePreviewDialog.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const { downloadFromResponse } = useDownload()
const fileInput = ref()
const items = ref([])
const loading = ref(false)
const showPreview = ref(false)
const previewFile = ref(null)
const uploaderOptions = ref([])
const uploaderMap = ref({})
const selectedIds = ref([])
const filters = reactive({ keyword: '', uploaded_by_id: null, mime_type: '' })

function uploaderLabel(id) {
  if (!id) return '-'
  return uploaderMap.value[id] || `#${id}`
}

async function loadUploaders() {
  try {
    const res = await lookupUsers({ page: 1, page_size: 50 })
    const users = res.data.data?.items ?? res.data.data ?? []
    uploaderOptions.value = users.map((u) => ({
      id: u.id,
      label: u.username || u.email || String(u.id),
    }))
    uploaderMap.value = Object.fromEntries(uploaderOptions.value.map((u) => [u.id, u.label]))
  } catch {
    uploaderOptions.value = []
  }
}

function syncUploadersFromFiles(fileItems) {
  const known = new Set(uploaderOptions.value.map((u) => u.id))
  for (const row of fileItems) {
    const id = row.uploaded_by_id
    if (!id || known.has(id)) continue
    known.add(id)
    const label = uploaderMap.value[id] || `#${id}`
    uploaderOptions.value.push({ id, label })
  }
}

async function load() {
  const params = withProjectParams({
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.keyword || undefined,
    uploaded_by_id: filters.uploaded_by_id ?? undefined,
    mime_type: filters.mime_type || undefined,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listUploadedFiles(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
    syncUploadersFromFiles(items.value)
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.keyword = ''
  filters.uploaded_by_id = null
  filters.mime_type = ''
  page.value = 1
  load()
}

function openPreview(row) {
  previewFile.value = row
  showPreview.value = true
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning(t('page.env.files.sizeLimit'))
    return
  }
  const fd = new FormData()
  fd.append('file', file)
  const params = withProjectParams()
  try {
    await uploadFile(fd, params)
    ElMessage.success(t('common.uploaded'))
    load()
  } finally {
    e.target.value = ''
  }
}

async function download(row) {
  try {
    const res = await downloadUploadedFile(row.id)
    downloadFromResponse(res, row.file_name)
  } catch {
    ElMessage.error(t('page.env.files.downloadFailed'))
  }
}

async function remove(row) {
  await deleteUploadedFile(row.id)
  ElMessage.success(t('common.deleted'))
  if (previewFile.value?.id === row.id) previewFile.value = null
  load()
}

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
    var res = await batchDeleteUploadedFiles(selectedIds.value)
    var data = res.data.data
    selectedIds.value = []
    if (data && data.failures && data.failures.length) {
      ElMessage.warning(t('common.batchDeletePartial'))
    } else if (data && data.deleted_ids && data.deleted_ids.length) {
      ElMessage.success(t('common.batchDeleteSuccess', { count: data.deleted_ids.length }))
    }
    load()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e?.response?.data?.message || e.message)
    }
  }
}

onMounted(() => {
  loadUploaders()
  load()
})
</script>
