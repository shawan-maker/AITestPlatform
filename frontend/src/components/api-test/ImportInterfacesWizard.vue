<template>
  <el-dialog v-model="visible" :title="t('page.apiCases.importInterfaces')" width="720px">
    <el-form inline style="margin-bottom: 12px">
      <el-form-item :label="t('page.knowledge.titleCol')">
        <el-input-number v-model="documentId" :min="1" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.versionNo')">
        <el-input-number v-model="versionId" :min="1" />
      </el-form-item>
      <el-button type="primary" :loading="previewing" @click="loadPreview">{{ t('page.apiCases.preview') }}</el-button>
    </el-form>
    <el-form v-if="items.length" inline style="margin-bottom: 12px">
      <el-form-item :label="t('page.apiCases.importMode')">
        <el-radio-group v-model="importMode">
          <el-radio value="skip">{{ t('page.apiCases.actionSkip') }}</el-radio>
          <el-radio value="upsert">{{ t('page.apiCases.actionUpsert') }}</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <AppTable
      v-if="items.length"
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
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="confirming" :disabled="!selected.length" @click="confirm">
        {{ t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { confirmApiImport, previewApiImport } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()
const { projectId } = useProjectScope()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const documentId = ref(null)
const versionId = ref(null)
const items = ref([])
const selected = ref([])
const previewing = ref(false)
const confirming = ref(false)
const importMode = ref('skip')

watch(visible, (v) => {
  if (!v) {
    items.value = []
    selected.value = []
    importMode.value = 'skip'
  }
})

function rowClassName({ row }) {
  if (row.conflict) return 'import-row--conflict'
  return ''
}

function onSelect(rows) {
  selected.value = rows
}

async function loadPreview() {
  if (!documentId.value || !versionId.value) {
    ElMessage.warning(t('validation.required'))
    return
  }
  previewing.value = true
  try {
    const res = await previewApiImport({
      document_id: documentId.value,
      version_id: versionId.value,
    })
    items.value = res.data.data?.items ?? []
    selected.value = [...items.value]
  } finally {
    previewing.value = false
  }
}

async function confirm() {
  if (!props.catalogId) {
    ElMessage.warning(t('page.apiCases.selectCatalog'))
    return
  }
  confirming.value = true
  try {
    await confirmApiImport({
      project_id: projectId.value,
      document_id: documentId.value,
      version_id: versionId.value,
      catalog_id: props.catalogId,
      mode: importMode.value,
      items: selected.value.map((i) => ({
        method: i.method,
        path: i.path,
        summary: i.summary,
      })),
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
