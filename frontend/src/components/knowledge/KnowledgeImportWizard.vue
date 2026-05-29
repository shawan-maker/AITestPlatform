<template>
  <el-dialog v-model="visible" :title="t('page.knowledge.importInterfaces')" width="720px">
    <el-form inline style="margin-bottom: 12px">
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="moduleId" />
      </el-form-item>
      <el-form-item :label="t('page.apiCases.importMode')">
        <el-radio-group v-model="importMode">
          <el-radio value="skip">{{ t('page.apiCases.actionSkip') }}</el-radio>
          <el-radio value="upsert">{{ t('page.apiCases.actionUpsert') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-button type="primary" :loading="previewing" @click="loadPreview">{{ t('page.apiCases.preview') }}</el-button>
    </el-form>
    <AppTable v-if="items.length" :data="items" :row-class-name="rowClassName" @selection-change="onSelect">
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
import { confirmImport, previewImport } from '@/api/knowledge'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  documentId: { type: Number, required: true },
  versionId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const moduleId = ref(null)
const importMode = ref('skip')
const items = ref([])
const selected = ref([])
const previewing = ref(false)
const confirming = ref(false)

watch(visible, (v) => {
  if (!v) {
    items.value = []
    selected.value = []
    importMode.value = 'skip'
  }
})

function rowClassName({ row }) {
  return row.conflict ? 'import-row--conflict' : ''
}

function onSelect(rows) {
  selected.value = rows
}

async function loadPreview() {
  previewing.value = true
  try {
    const res = await previewImport(props.documentId, {
      version_id: props.versionId || undefined,
      module_id: moduleId.value || undefined,
    })
    items.value = res.data.data?.items ?? res.data.data ?? []
    selected.value = [...items.value]
  } finally {
    previewing.value = false
  }
}

async function confirm() {
  confirming.value = true
  try {
    await confirmImport(props.documentId, {
      version_id: props.versionId || undefined,
      module_id: moduleId.value || undefined,
      mode: importMode.value,
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
