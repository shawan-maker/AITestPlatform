<template>
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="t('page.knowledge.saveInterfaces')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
    destroy-on-close
    @opened="loadPreview"
  >
    <el-form label-width="100px" style="margin-bottom: 12px">
      <el-form-item :label="t('page.knowledge.titleCol')">
        <el-input :model-value="sourceTitle" readonly />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.saveCatalog')">
        <CatalogTreeSelect
          v-model="catalogId"
          :placeholder="t('page.knowledge.saveCatalogPlaceholder')"
        />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="moduleId" />
      </el-form-item>
    </el-form>
    <AppTable
      v-loading="previewing"
      :data="items"
      :row-class-name="rowClassName"
      @selection-change="onSelect"
    >
      <AppTableColumn type="selection" variant="fixed" :width="48" />
      <AppTableColumn prop="method" variant="fixed" label="Method" :width="90" />
      <AppTableColumn prop="path" variant="content" label="Path" />
      <AppTableColumn prop="summary" variant="content" :label="t('page.apiCases.summary')" />
      <AppTableColumn variant="fixed" :label="t('common.status')" :width="120">
        <template #default="{ row }">
          <el-tag :type="row.conflict ? 'warning' : 'success'">
            {{ row.conflict ? t('page.apiCases.actionUpsert') : t('page.apiCases.actionCreate') }}
          </el-tag>
        </template>
      </AppTableColumn>
    </AppTable>
    <el-alert
      v-if="!previewing && items.length === 0"
      :title="t('page.knowledge.parsedInterfacesEmpty')"
      type="info"
      :closable="false"
      show-icon
      style="margin-top: 12px"
    />
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="confirming" :disabled="!selected.length" @click="doConfirm">
        {{ t('common.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { confirmImport, previewImport } from '@/api/knowledge'
import { useContentDialog } from '@/composables/useContentDialog'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import CatalogTreeSelect from '@/components/tree/CatalogTreeSelect.vue'
import { formatDocumentVersionTitle } from '@/utils/knowledge'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  documentId: { type: Number, required: true },
  versionId: { type: Number, default: null },
  documentTitle: { type: String, default: '' },
  versionLabel: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass } = useContentDialog()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const catalogId = ref(null)
const moduleId = ref(null)
const items = ref([])
const selected = ref([])
const previewing = ref(false)
const confirming = ref(false)

const sourceTitle = computed(() =>
  formatDocumentVersionTitle(props.documentTitle, props.versionLabel),
)

watch(visible, (v) => {
  if (!v) {
    items.value = []
    selected.value = []
    catalogId.value = null
    moduleId.value = null
  }
})

// 切换目录时重新检测冲突（基于目标目录范围）
watch(catalogId, () => {
  if (visible.value && props.versionId) {
    loadPreview()
  }
})

function rowClassName({ row }) {
  return row.conflict ? 'import-row--conflict' : ''
}

function onSelect(rows) {
  selected.value = rows
}

async function loadPreview() {
  if (!props.versionId) return
  previewing.value = true
  try {
    const res = await previewImport(props.documentId, props.versionId, {
      params: { catalog_id: catalogId.value || undefined },
    })
    items.value = res.data.data?.items ?? []
    selected.value = []
  } finally {
    previewing.value = false
  }
}

async function doConfirm() {
  if (!catalogId.value) {
    ElMessage.warning(t('page.knowledge.saveCatalogPlaceholder'))
    return
  }
  if (!selected.value.length) {
    ElMessage.warning(t('page.knowledge.selectAtLeastOneInterface'))
    return
  }
  confirming.value = true
  try {
    await confirmImport(props.documentId, props.versionId, {
      catalog_id: catalogId.value,
      module_id: moduleId.value || undefined,
      items: selected.value,
    })
    ElMessage.success(t('common.saved'))
    emit('imported')
    visible.value = false
  } finally {
    confirming.value = false
  }
}

</script>

<style scoped lang="scss">
:deep(.import-row--conflict) {
  background-color: var(--el-color-warning-light-9);
}
</style>
