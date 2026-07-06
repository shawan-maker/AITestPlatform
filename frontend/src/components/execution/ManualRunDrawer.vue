<template>
  <el-drawer :model-value="modelValue" :title="t('page.test.manualRun')" size="70%" @update:model-value="$emit('update:modelValue', $event)">
    <div class="manual-run-body">
      <div class="manual-left">
        <el-tree :data="treeData" :props="{ children: 'children', label: 'label' }" node-key="nodeKey" highlight-current @node-click="onTreeNodeClick" default-expand-all />
      </div>
      <div class="manual-right">
        <AppTable :data="filteredCases" :loading="loading" :empty-text="t('execution.selectCatalogHint')">
          <AppTableColumn prop="case_name" variant="content" :label="t('page.functional.caseName')" />
          <AppTableColumn variant="fixed" :label="t('common.status')" :width="100">
            <template #default="{ row }">
              <el-tag v-if="row.exec_result" :type="resultType(row.exec_result)" size="small">{{ resultLabel(row.exec_result) }}</el-tag>
              <span v-else>-</span>
            </template>
          </AppTableColumn>
          <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('common.view'), t('page.test.linkDefect')]">
            <template #default="{ row }">
              <el-button link type="primary" @click="openCase(row)">{{ t('common.view') }}</el-button>
              <el-button v-if="row.exec_result === 'failed'" link type="danger" @click="createDefectForRow(row)">{{ t('page.test.linkDefect') }}</el-button>
            </template>
          </AppTableColumn>
        </AppTable>
      </div>
    </div>

    <el-dialog :close-on-click-modal="false" v-model="caseVisible" :title="currentCase?.case_name || currentCase?.name" width="600px">
      <div v-if="currentCase">
        <div v-if="currentCase.precondition" style="margin-bottom: 12px">
          <h4>{{ t('execution.precondition') }}</h4>
          <pre style="white-space: pre-wrap; background: #f5f7fa; padding: 8px; border-radius: 4px">{{ currentCase.precondition }}</pre>
        </div>
        <div v-if="currentCase.test_steps" style="margin-bottom: 12px">
          <h4>{{ t('execution.testSteps') }}</h4>
          <pre style="white-space: pre-wrap; background: #f5f7fa; padding: 8px; border-radius: 4px">{{ currentCase.test_steps }}</pre>
        </div>
        <div v-if="currentCase.expected_result" style="margin-bottom: 12px">
          <h4>{{ t('execution.expectedResult') }}</h4>
          <pre style="white-space: pre-wrap; background: #f5f7fa; padding: 8px; border-radius: 4px">{{ currentCase.expected_result }}</pre>
        </div>
        <el-divider />
        <el-form-item :label="t('execution.execResult')">
          <el-radio-group v-model="caseResult">
            <el-radio value="passed">{{ t('execution.passed') }}</el-radio>
            <el-radio value="failed">{{ t('execution.failed') }}</el-radio>
            <el-radio value="blocked">{{ t('execution.blocked') }}</el-radio>
            <el-radio value="skipped">{{ t('execution.skipped') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('execution.remark')">
          <el-input v-model="caseComment" type="textarea" :rows="2" />
        </el-form-item>
      </div>
      <template #footer>
        <el-button @click="caseVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="caseSaving" @click="saveCase">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <DefectCreateDialog v-model="showDefectDialog" :default-title="defectDefaultTitle" :default-steps="defectDefaultSteps" :loading="defectSaving" @submit="submitDefect" />
  </el-drawer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getManualContext, getManualCase, patchManualCase, createDefectFromRun } from '@/api/testExecution'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import DefectCreateDialog from './DefectCreateDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  taskId: { type: Number, required: true },
  runId: { type: [Number, null], default: null },
})

defineEmits(['update:modelValue'])
const { t } = useI18n()

const loading = ref(false)
const allCases = ref([])
const treeData = ref([])
const selectedCatalog = ref(null)
const caseVisible = ref(false)
const currentCase = ref(null)
const caseResult = ref('passed')
const caseComment = ref('')
const caseSaving = ref(false)

const showDefectDialog = ref(false)
const defectDefaultTitle = ref('')
const defectDefaultSteps = ref('')
const defectSaving = ref(false)
const defectRowRef = ref(null)

const filteredCases = computed(() => {
  if (!selectedCatalog.value) return allCases.value
  return allCases.value.filter(c => c.catalog_id === selectedCatalog.value)
})

function resultType(r) {
  if (r === 'passed') return 'success'
  if (r === 'failed') return 'danger'
  if (r === 'blocked') return 'warning'
  return 'info'
}

function resultLabel(r) {
  var map = { passed: t('execution.passed'), failed: t('execution.failed'), blocked: t('execution.blocked'), skipped: t('execution.skipped') }
  return map[r] || r || '-'
}

function buildTree(catalogs) {
  if (!catalogs || !Array.isArray(catalogs)) return []
  return catalogs.map(c => ({
    nodeKey: 'cat-' + c.id,
    label: c.name || t('execution.unnamed'),
    catalogId: c.id,
    children: c.children ? buildTree(c.children) : [],
  }))
}

async function load() {
  if (!props.runId) return
  loading.value = true
  try {
    const res = await getManualContext(props.runId)
    var data = res.data.data || {}
    allCases.value = data.cases ?? data.items ?? []
    treeData.value = buildTree(data.catalogs ?? data.tree ?? [])
    selectedCatalog.value = null
  } finally {
    loading.value = false
  }
}

function onTreeNodeClick(nodeData) {
  selectedCatalog.value = nodeData.catalogId || null
}

async function openCase(row) {
  try {
    const res = await getManualCase(props.runId, row.case_id ?? row.id)
    currentCase.value = res.data.data
    caseResult.value = currentCase.value.exec_result || 'passed'
    caseComment.value = currentCase.value.comment || ''
    caseVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function saveCase() {
  caseSaving.value = true
  try {
    await patchManualCase(props.runId, currentCase.value.case_id ?? currentCase.value.id, {
      exec_result: caseResult.value,
      comment: caseComment.value || undefined,
    })
    ElMessage.success(t('common.saved'))
    caseVisible.value = false
    load()
  } finally {
    caseSaving.value = false
  }
}

function createDefectForRow(row) {
  defectRowRef.value = row
  defectDefaultTitle.value = (row.case_name || row.name || '') + ' - ' + t('execution.defectSuffix')
  defectDefaultSteps.value = currentCase.value?.test_steps || ''
  showDefectDialog.value = true
}

async function submitDefect(payload) {
  defectSaving.value = true
  try {
    await createDefectFromRun({
      ...payload,
      source_type: 'functional_case',
      source_run_id: props.runId,
      source_case_id: defectRowRef.value?.case_id ?? defectRowRef.value?.id,
    })
    ElMessage.success(t('common.saved'))
    showDefectDialog.value = false
  } finally {
    defectSaving.value = false
  }
}

watch(() => props.modelValue, (v) => { if (v) load() })
</script>

<style scoped>
.manual-run-body {
  display: flex;
  gap: 16px;
  height: 100%;
}
.manual-left {
  width: 260px;
  flex-shrink: 0;
  overflow: auto;
  border-right: 1px solid var(--el-border-color-lighter);
  padding-right: 16px;
}
.manual-right {
  flex: 1;
  min-width: 0;
}
</style>
