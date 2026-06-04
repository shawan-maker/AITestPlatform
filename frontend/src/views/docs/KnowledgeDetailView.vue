<template>
  <div v-loading="loading" class="knowledge-detail-view app-card">
    <PageHeader :title="doc?.title || t('page.knowledge.title')">
      <template #actions>
        <el-button @click="router.push('/docs/knowledge')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" @click="showReupload = true">{{ t('page.knowledge.reupload') }}</el-button>
        <el-button @click="showHistory = true">{{ t('page.knowledge.versionHistory') }}</el-button>
        <el-button @click="download">{{ t('common.download') }}</el-button>
        <el-button v-if="canEdit && canSaveInterfaces(doc)" @click="openImport">
          {{ t('page.knowledge.saveInterfaces') }}
        </el-button>
        <el-button v-if="canEdit && canSaveRequirement(doc)" @click="openCandidate">
          {{ t('page.knowledge.saveRequirement') }}
        </el-button>
        <ConfirmDelete v-if="canEdit" :message="t('page.knowledge.deleteConfirm')" @confirm="remove">
          <el-button type="danger">{{ t('common.delete') }}</el-button>
        </ConfirmDelete>
      </template>
    </PageHeader>

    <AsyncJobBanner
      :visible="isProcessing"
      :title="processingTitle"
      :description="parseStatusLabel"
    />

    <el-descriptions v-if="doc" :column="2" border class="detail-meta">
      <el-descriptions-item :label="t('page.knowledge.module')">{{ doc.module_name || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.versionNo')">
        {{ doc.version_label || doc.current_version?.version_label || '—' }}
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.indexStatus')">
        <IndexStatusBadge
          :status="doc.index_status"
          :doc-type="doc.doc_type"
          :parse-status="doc.parse_status"
        />
      </el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.docType')">
        {{ doc.doc_type === 'api_doc' ? t('page.knowledge.docTypeApi') : t('page.knowledge.docTypeRequirement') }}
      </el-descriptions-item>
    </el-descriptions>

    <div class="knowledge-detail-body">
      <section
        v-if="doc?.doc_type === 'requirement'"
        v-loading="contentLoading"
        class="doc-content-section"
      >
        <h3 class="section-title">{{ t('page.knowledge.documentContent') }}</h3>
        <div class="doc-content-fill">
          <pre v-if="documentContent" class="doc-content-pre">{{ documentContent }}</pre>
          <p v-else class="doc-content-empty">{{ t('page.knowledge.textPreviewEmpty') }}</p>
        </div>
      </section>

      <ApiDocParsedInterfaceTable
        v-if="doc?.doc_type === 'api_doc'"
        :items="parsedInterfaces"
        :loading="loading || parsedInterfacesLoading"
        :parse-status="doc.parse_status ?? ''"
        :interfaces-saved="doc.interfaces_saved === true"
      />
    </div>

    <KnowledgeImportWizard
      v-if="importDocId"
      v-model="showImport"
      :document-id="importDocId"
      :version-id="importVersionId"
      :document-title="doc?.title ?? ''"
      :version-label="doc?.version_label ?? doc?.current_version?.version_label ?? ''"
      @imported="load"
    />
    <DocumentReuploadDialog v-model="showReupload" :loading="reuploading" @submit="submitReupload" />
    <KnowledgeVersionHistoryDrawer
      v-model="showHistory"
      :document-id="docId"
      :document="doc"
      @download-version="downloadVersionRow"
    />
    <CandidateConfirmDialog
      v-model="showCandidate"
      :candidate="candidate"
      :document-id="docId"
      :version-id="candidateVersionId"
      :document-title="doc?.title ?? ''"
      :version-label="doc?.version_label ?? doc?.current_version?.version_label ?? ''"
      :loading="confirming"
      @confirm="onConfirmCandidate"
    />
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  deleteDocument,
  downloadDocument as downloadDocApi,
  downloadVersion as downloadVersionApi,
  getDocument,
  getParsedInterfaces,
  getRequirementCandidate,
  getVersionTextPreview,
  previewImport,
  uploadVersion,
} from '@/api/knowledge'
import { confirmCandidate } from '@/api/functional'
import { usePermission } from '@/composables/usePermission'
import { useDownload } from '@/composables/useDownload'
import { usePolling } from '@/composables/usePolling'
import {
  canSaveInterfaces,
  canSaveRequirement,
  isDocumentProcessing,
  resolveParseDisplayStatus,
} from '@/utils/knowledge'
import { mergeParsedInterfaceItems } from '@/utils/parsedInterfaceMerge'
import PageHeader from '@/components/common/PageHeader.vue'
import AsyncJobBanner from '@/components/common/AsyncJobBanner.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import IndexStatusBadge from '@/components/common/IndexStatusBadge.vue'
import KnowledgeImportWizard from '@/components/knowledge/KnowledgeImportWizard.vue'
import DocumentReuploadDialog from '@/components/knowledge/DocumentReuploadDialog.vue'
import KnowledgeVersionHistoryDrawer from '@/components/knowledge/KnowledgeVersionHistoryDrawer.vue'
import CandidateConfirmDialog from '@/components/knowledge/CandidateConfirmDialog.vue'
import ApiDocParsedInterfaceTable from '@/components/knowledge/ApiDocParsedInterfaceTable.vue'
import { useKnowledgeStore } from '@/stores/knowledge'

const knowledgeStore = useKnowledgeStore()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const { downloadFromResponse } = useDownload()

const docId = computed(() => Number(route.params.documentId))
const doc = ref(null)
const loading = ref(false)
const contentLoading = ref(false)
const documentContent = ref('')
const parsedInterfaces = ref([])
const parsedInterfacesLoading = ref(false)
const showImport = ref(false)
const importDocId = ref(null)
const importVersionId = ref(null)
const showReupload = ref(false)
const reuploading = ref(false)
const showHistory = ref(false)
const showCandidate = ref(false)
const candidate = ref(null)
const confirming = ref(false)

const currentVersionId = computed(
  () => doc.value?.current_version?.id ?? doc.value?.current_version_id ?? null,
)

const candidateVersionId = computed(
  () =>
    candidate.value?.source_document_version_id ??
    doc.value?.current_version?.id ??
    doc.value?.current_version_id ??
    null,
)

const isProcessing = computed(() => isDocumentProcessing(doc.value))

const processingTitle = computed(() =>
  doc.value?.doc_type === 'api_doc' ? t('page.knowledge.parsing') : t('page.knowledge.indexing'),
)

const parseStatusLabel = computed(() => {
  const key = resolveParseDisplayStatus(doc.value)
  return key ? t(`indexStatus.${key}`) : ''
})

const polling = usePolling(
  async () => {
    await load({ silent: true })
  },
  {
    interval: 3000,
    until: () => !isProcessing.value,
  },
)

async function loadDocumentContent() {
  const versionId = currentVersionId.value
  if (!versionId || doc.value?.doc_type !== 'requirement') {
    documentContent.value = ''
    return
  }
  contentLoading.value = true
  try {
    const res = await getVersionTextPreview(docId.value, versionId)
    documentContent.value = res.data.data?.text ?? ''
  } catch {
    documentContent.value = ''
  } finally {
    contentLoading.value = false
  }
}

async function loadParsedInterfaces() {
  if (doc.value?.doc_type !== 'api_doc') {
    parsedInterfaces.value = []
    return
  }
  const versionId = currentVersionId.value
  if (!versionId || doc.value?.parse_status !== 'parsed') {
    parsedInterfaces.value = []
    return
  }

  parsedInterfacesLoading.value = true
  try {
    const fromDetail = doc.value?.parsed_interfaces ?? doc.value?.parsedInterfaces ?? []
    const [parsedRes, previewRes] = await Promise.allSettled([
      getParsedInterfaces(docId.value, versionId),
      previewImport(docId.value, versionId, { silentError: true }),
    ])

    const sources = [fromDetail]
    if (parsedRes.status === 'fulfilled') {
      sources.push(parsedRes.value.data.data?.items ?? [])
    }
    if (previewRes.status === 'fulfilled') {
      sources.push(previewRes.value.data.data?.items ?? [])
    }

    parsedInterfaces.value = mergeParsedInterfaceItems(...sources)
  } finally {
    parsedInterfacesLoading.value = false
  }
}

async function load(opts = {}) {
  if (!opts.silent) loading.value = true
  try {
    const docRes = await getDocument(docId.value)
    doc.value = docRes.data.data
    importDocId.value = doc.value?.id ?? null
    importVersionId.value = currentVersionId.value
    await Promise.all([loadDocumentContent(), loadParsedInterfaces()])
  } finally {
    if (!opts.silent) loading.value = false
  }
}

async function tryOpenCandidate() {
  if (!canSaveRequirement(doc.value)) return
  try {
    const res = await getRequirementCandidate(docId.value)
    const cand = res.data.data
    if (cand) {
      candidate.value = cand
      showCandidate.value = true
    }
  } catch {
    /* no candidate */
  }
}

async function openCandidate() {
  await tryOpenCandidate()
  if (!candidate.value) {
    ElMessage.warning(t('page.knowledge.noCandidate'))
  }
}

function openImport() {
  if (!importVersionId.value) {
    ElMessage.warning(t('page.knowledge.noVersion'))
    return
  }
  showImport.value = true
}

async function download() {
  const res = await downloadDocApi(docId.value)
  downloadFromResponse(res, doc.value?.title || 'document')
}

async function downloadVersionRow(version) {
  const res = await downloadVersionApi(docId.value, version.id)
  downloadFromResponse(res, `${doc.value?.title || 'doc'}_${version.version_label}`)
}

async function remove() {
  await deleteDocument(docId.value)
  ElMessage.success(t('common.deleted'))
  router.push('/docs/knowledge')
}

async function submitReupload(formData) {
  reuploading.value = true
  try {
    await uploadVersion(docId.value, formData)
    ElMessage.success(t('page.knowledge.reuploadOk'))
    showReupload.value = false
    await load()
    polling.start()
  } finally {
    reuploading.value = false
  }
}

async function onConfirmCandidate(payload) {
  if (!candidate.value) return
  confirming.value = true
  try {
    await confirmCandidate(candidate.value.id, payload)
    ElMessage.success(t('page.requirements.confirmedMsg'))
    showCandidate.value = false
    candidate.value = null
    knowledgeStore.requestRefresh()
    await load()
  } finally {
    confirming.value = false
  }
}

watch(isProcessing, (processing) => {
  if (processing) polling.start()
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

onMounted(async () => {
  await load()
  if (isProcessing.value) polling.start()
})
</script>

<style scoped lang="scss">
.knowledge-detail-view {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 120px);
}

.detail-meta {
  flex-shrink: 0;
}

.knowledge-detail-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-top: 20px;
}

.doc-content-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
}

.doc-content-fill {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.doc-content-pre {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 12px 16px;
  overflow: auto;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  background: var(--el-fill-color-blank);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
}

.doc-content-empty {
  flex: 1;
  margin: 0;
  padding: 24px;
  color: var(--el-text-color-placeholder);
  text-align: center;
}
</style>
