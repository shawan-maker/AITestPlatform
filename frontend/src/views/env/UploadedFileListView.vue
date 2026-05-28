<template>
  <div class="uploaded-file-list app-card">
    <PageHeader :title="t('page.env.files.title')" />
    <EmptyState v-if="!projectId" :title="t('common.noProject')" :description="t('common.selectProjectHint')" />
    <template v-else>
      <FilterBar @search="load" @reset="load">
        <template #primary>
          <el-button v-if="canEdit" type="primary" @click="fileInput?.click()">{{ t('common.upload') }}</el-button>
          <input ref="fileInput" type="file" hidden @change="onUpload" />
        </template>
      </FilterBar>
      <SplitView :initial-width="360">
      <template #left>
        <PaginatedTable :data="items" :loading="loading" :total="total" v-model:page="page" v-model:page-size="pageSize" @page-change="load">
          <AppTableColumn prop="name" variant="content" :label="t('common.name')">
            <template #default="{ row }">{{ row.name || row.file_name }}</template>
          </AppTableColumn>
          <AppTableColumn prop="size" variant="flex" :label="t('common.size')">
            <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
          </AppTableColumn>
          <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="240">
            <template #default="{ row }">
              <el-button link @click="selectFile(row)">{{ t('common.view') }}</el-button>
              <el-button link @click="download(row)">{{ t('common.download') }}</el-button>
              <ConfirmDelete v-if="canEdit" @confirm="remove(row)">
                <el-button link type="danger">{{ t('common.delete') }}</el-button>
              </ConfirmDelete>
            </template>
          </AppTableColumn>
        </PaginatedTable>
      </template>
      <template #right>
        <FilePreviewPanel v-if="previewFile" :file-id="previewFile.id" :file-name="previewFile.name || previewFile.file_name" />
        <EmptyState v-else :title="t('page.env.files.selectPreview')" />
      </template>
      </SplitView>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { deleteUploadedFile, downloadUploadedFile, listUploadedFiles, uploadFile } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useDownload } from '@/composables/useDownload'
import { formatFileSize } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SplitView from '@/components/common/SplitView.vue'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import FilePreviewPanel from '@/components/env/FilePreviewPanel.vue'

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const { canEdit } = usePermission()
const { page, pageSize, total } = usePagination()
const { downloadFromResponse } = useDownload()
const fileInput = ref()
const items = ref([])
const loading = ref(false)
const previewFile = ref(null)

async function load() {
  const params = withProjectParams({ page: page.value, page_size: pageSize.value })
  if (!params) return
  loading.value = true
  try {
    const res = await listUploadedFiles(params)
    items.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

function selectFile(row) {
  previewFile.value = row
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
  await uploadFile(fd, params)
  ElMessage.success(t('common.uploaded'))
  load()
}

async function download(row) {
  const res = await downloadUploadedFile(row.id)
  downloadFromResponse(res, row.name || row.file_name)
}

async function remove(row) {
  await deleteUploadedFile(row.id)
  ElMessage.success(t('common.deleted'))
  if (previewFile.value?.id === row.id) previewFile.value = null
  load()
}

onMounted(load)
</script>
