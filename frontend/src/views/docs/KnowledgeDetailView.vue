<template>
  <div v-loading="loading" class="knowledge-detail-view app-card">
    <PageHeader :title="doc?.title || t('page.knowledge.title')">
      <template #actions>
        <el-button @click="router.push('/docs/knowledge')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" @click="download">{{ t('common.download') }}</el-button>
        <el-button v-if="canEdit && doc?.doc_type === 'api_doc' && doc?.index_status === 'indexed'" @click="openImport">
          {{ t('page.knowledge.importInterfaces') }}
        </el-button>
        <el-button v-if="canEdit" :disabled="isIndexing" @click="reindex">{{ t('page.knowledge.reindex') }}</el-button>
        <ConfirmDelete v-if="canEdit" @confirm="remove">
          <el-button type="danger">{{ t('common.delete') }}</el-button>
        </ConfirmDelete>
      </template>
    </PageHeader>

    <AsyncJobBanner
      :visible="isIndexing"
      :title="t('page.knowledge.indexing')"
      :description="doc?.index_status"
    />

    <el-descriptions v-if="doc" :column="2" border>
      <el-descriptions-item :label="t('page.knowledge.module')">{{ doc.module_name || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.indexStatus')"><IndexStatusBadge :status="doc.index_status" /></el-descriptions-item>
    </el-descriptions>

    <h3>{{ t('page.knowledge.versions') }}</h3>
    <AppTable :data="versions">
      <AppTableColumn prop="version_no" variant="fixed" :label="t('page.knowledge.versionNo')" :width="100" />
      <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="200">
        <template #default="{ row }">
          <el-button link @click="downloadVersion(row)">{{ t('common.download') }}</el-button>
          <el-button
            v-if="canEdit && doc?.doc_type === 'api_doc' && doc?.index_status === 'indexed'"
            link
            @click="openImportForVersion(row)"
          >{{ t('page.knowledge.importInterfaces') }}</el-button>
        </template>
      </AppTableColumn>
    </AppTable>

    <KnowledgeImportWizard
      v-model="showImport"
      :document-id="docId"
      :version-id="importVersionId"
      @imported="load"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  deleteDocument,
  downloadDocument as downloadDocApi,
  downloadVersion as downloadVersionApi,
  getDocument,
  listVersions,
  reindexDocument,
} from '@/api/knowledge'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import { usePolling } from '@/composables/usePolling'
import { formatDateTime } from '@/utils/format'
import PageHeader from '@/components/common/PageHeader.vue'
import AsyncJobBanner from '@/components/common/AsyncJobBanner.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import IndexStatusBadge from '@/components/common/IndexStatusBadge.vue'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import KnowledgeImportWizard from '@/components/knowledge/KnowledgeImportWizard.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const { downloadFromResponse } = useDownload()

const docId = computed(() => Number(route.params.documentId))
const doc = ref(null)
const versions = ref([])
const loading = ref(false)
const showImport = ref(false)
const importVersionId = ref(null)

const isIndexing = computed(() => ['indexing', 'parsing', 'pending'].includes(doc.value?.index_status))

async function load() {
  loading.value = true
  try {
    const [docRes, verRes] = await Promise.all([getDocument(docId.value), listVersions(docId.value)])
    doc.value = docRes.data.data
    versions.value = verRes.data.data?.items ?? verRes.data.data ?? []
  } finally {
    loading.value = false
  }
}

async function download() {
  const res = await downloadDocApi(docId.value)
  downloadFromResponse(res, `${doc.value?.title || 'document'}`)
}

async function downloadVersion(row) {
  const res = await downloadVersionApi(docId.value, row.id)
  downloadFromResponse(res, `v${row.version_no}`)
}

async function reindex() {
  await reindexDocument(docId.value)
  ElMessage.success(t('page.knowledge.reindexStarted'))
  load()
}

async function remove() {
  await deleteDocument(docId.value)
  ElMessage.success(t('common.deleted'))
  router.push('/docs/knowledge')
}

function openImport() {
  importVersionId.value = versions.value[0]?.id ?? null
  showImport.value = true
}

function openImportForVersion(row) {
  importVersionId.value = row.id
  showImport.value = true
}

onMounted(() => {
  load()
  const polling = usePolling(load, {
    interval: 3000,
    until: () => !isIndexing.value,
  })
  if (isIndexing.value) polling.start()
})
</script>

<style scoped lang="scss">
h3 {
  margin: 24px 0 12px;
  font-size: 16px;
}
</style>
