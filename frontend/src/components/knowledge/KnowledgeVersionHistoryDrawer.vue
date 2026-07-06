<template>
  <el-drawer v-model="visible" :title="t('page.knowledge.versionHistory')" size="640px" destroy-on-close>
    <el-descriptions v-if="document" :column="1" border class="doc-summary">
      <el-descriptions-item :label="t('page.knowledge.titleCol')">{{ document.title }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.module')">{{ document.module_name || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.knowledge.docType')">
        {{ document.doc_type === 'api_doc' ? t('page.knowledge.docTypeApi') : t('page.knowledge.docTypeRequirement') }}
      </el-descriptions-item>
    </el-descriptions>

    <PaginatedTable
      v-model:page="page"
      v-model:page-size="pageSize"
      :data="versions"
      :loading="loading"
      :total="total"
      class="version-table"
      @page-change="loadVersions"
      @size-change="loadVersions"
    >
      <AppTableColumn prop="version_label" variant="fixed" :label="t('page.knowledge.versionNo')" :width="90" />
      <AppTableColumn prop="file_name" variant="content" :label="t('page.knowledge.file')" />
      <AppTableColumn variant="fixed" :label="t('page.knowledge.indexStatus')" :width="120">
        <template #default="{ row }">
          <IndexStatusBadge
            :status="row.index_status"
            :doc-type="document?.doc_type"
            :parse-status="row.parse_status"
          />
        </template>
      </AppTableColumn>
      <AppTableColumn prop="created_at" variant="flex" :label="t('common.createdAt')">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </AppTableColumn>
      <AppTableColumn prop="created_by_username" variant="flex" :label="t('page.knowledge.uploader')" />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('common.download')]">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.file_expired" @click="emit('download-version', row)">
            {{ t('common.download') }}
          </el-button>
        </template>
      </AppTableColumn>
    </PaginatedTable>
  </el-drawer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listVersions } from '@/api/knowledge'
import { usePagination } from '@/composables/usePagination'
import { formatDateTime } from '@/utils/format'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import IndexStatusBadge from '@/components/common/IndexStatusBadge.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  documentId: { type: Number, default: null },
  document: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'download-version'])
const { t } = useI18n()
const { page, pageSize, total } = usePagination()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const versions = ref([])
const loading = ref(false)

async function loadVersions() {
  if (!props.documentId) return
  loading.value = true
  try {
    const res = await listVersions(props.documentId, {
      page: page.value,
      page_size: pageSize.value,
    })
    versions.value = res.data.data?.items ?? []
    total.value = res.data.data?.total ?? 0
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      page.value = 1
      loadVersions()
    }
  },
)
</script>

<style scoped lang="scss">
.doc-summary {
  margin-bottom: 16px;
}
.version-table {
  margin-top: 8px;
}
</style>
