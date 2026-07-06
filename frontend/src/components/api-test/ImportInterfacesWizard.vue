<template>
  <!-- v2-L4: 强制选择新目录，移除mode选项，冲突高亮并禁用confirm -->
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="t('page.apiCases.importInterfaces')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <el-form inline style="margin-bottom: 12px">
      <el-form-item :label="t('page.knowledge.titleCol')">
        <el-input-number v-model="documentId" :min="1" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.versionNo')">
        <el-input-number v-model="versionId" :min="1" />
      </el-form-item>
      <el-button type="primary" :loading="previewing" @click="loadPreview">{{ t('page.apiCases.preview') }}</el-button>
    </el-form>
    <!-- v2-L4: 移除mode选择，强制新建模式；冲突时显示警告 -->
    <div v-if="hasConflicts" style="margin-bottom: 12px">
      <el-alert
        type="warning"
        :title="t('page.apiCases.import.conflictHint')"
        :closable="false"
        show-icon
      />
    </div>
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
          <el-tag :type="row._target_conflict ? 'danger' : 'success'">
            {{ row._target_conflict ? t('page.apiCases.import.statusConflict') : t('page.apiCases.import.statusNew') }}
          </el-tag>
        </template>
      </AppTableColumn>
    </AppTable>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button
        type="primary"
        :loading="confirming"
        :disabled="!selected.length || hasConflicts"
        @click="confirm"
      >
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
import { useContentDialog } from '@/composables/useContentDialog'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()
const { projectId } = useProjectScope()
const { dialogWidth, dialogTop, dialogClass } = useContentDialog(200)

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

watch(visible, (v) => {
  if (!v) {
    items.value = []
    selected.value = []
  }
})

// v2-L4: 检查是否有目标目录内冲突
const hasConflicts = computed(() =>
  items.value.some((item) => item._target_conflict)
)

function rowClassName({ row }) {
  if (row._target_conflict) return 'import-row--conflict'
  return ''
}

function onSelect(rows) {
  // v2-L4: 不允许选中冲突行
  selected.value = rows.filter((r) => !r._target_conflict)
}

async function loadPreview() {
  if (!documentId.value || !versionId.value) {
    ElMessage.warning(t('validation.required'))
    return
  }
  if (!props.catalogId) {
    ElMessage.warning(t('page.apiCases.import.selectCatalogFirst'))
    return
  }
  previewing.value = true
  try {
    const res = await previewApiImport({
      document_id: documentId.value,
      version_id: versionId.value,
    })
    const rawItems = res.data.data?.items ?? []
    items.value = rawItems.map((i) => ({
      ...i,
      _target_conflict: false,
    }))
    selected.value = [...items.value]
  } finally {
    previewing.value = false
  }
}

async function confirm() {
  if (!props.catalogId) {
    ElMessage.warning(t('page.apiCases.import.selectCatalogFirst'))
    return
  }
  confirming.value = true
  try {
    // v2-L4: 不再传mode参数，后端强制新目录模式
    const res = await confirmApiImport({
      project_id: projectId.value,
      document_id: documentId.value,
      version_id: versionId.value,
      catalog_id: props.catalogId,
      items: selected.value.map((i) => ({
        method: i.method,
        path: i.path,
        summary: i.summary,
      })),
    })
    const result = res.data.data
    if (result.failed > 0 && result.conflicts?.length) {
      ElMessage.error(
        t('page.apiCases.import.importFailMsg', { count: result.failed }) +
        result.conflicts.map((c) => `${c.method} ${c.path}`).join('; ')
      )
    } else {
      ElMessage.success(t('common.saved'))
      emit('imported')
      visible.value = false
    }
  } finally {
    confirming.value = false
  }
}
</script>

<style scoped lang="scss">
::deep(.import-row--conflict) {
  background-color: var(--el-color-danger-light-9);
}
</style>
