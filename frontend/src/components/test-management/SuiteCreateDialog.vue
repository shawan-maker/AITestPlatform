<template>
  <el-dialog
    :close-on-click-modal="false"
    :model-value="modelValue"
    :title="t('page.test.suites.create')"
    width="1100px"
    top="4vh"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <!-- 上部：表单输入 -->
    <el-form label-width="auto" class="suite-form">
      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item :label="t('page.test.suites.suiteName')" required>
            <el-input v-model="form.suite_name" :placeholder="t('page.test.suites.suiteName')" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="t('page.test.suiteType')">
            <el-radio-group v-model="form.type">
              <el-radio value="api">API</el-radio>
              <el-tooltip :content="t('page.test.suites.uiNotSupported')" placement="top">
                <el-radio value="ui" disabled>UI</el-radio>
              </el-tooltip>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item :label="t('common.description')">
            <el-input v-model="form.description" type="textarea" :rows="2" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="t('page.apiCases.selectEnv')">
            <EnvironmentSelect v-model="form.environment_id" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item :label="t('page.test.runMode')">
            <el-radio-group v-model="form.run_mode">
              <el-radio value="serial">{{ t('page.test.serial') }}</el-radio>
              <el-radio value="parallel">{{ t('page.test.parallel') }}</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <!-- 下部：关联用例 -->
    <div class="suite-cases-section">
      <div class="suite-cases-header">
        <span class="suite-cases-title">{{ t('page.test.tabCases') }}</span>
        <span v-if="associatedCases.length" class="suite-cases-count">({{ associatedCases.length }})</span>
      </div>
      <div class="suite-cases-toolbar">
        <el-input
          v-model="caseSearch"
          :placeholder="t('page.test.suites.searchByName')"
          clearable
          style="width: 260px"
        />
        <el-button type="primary" @click="showPicker = true">{{ t('page.test.addCases') }}</el-button>
        <template v-if="selectedCaseIds.length">
          <el-button type="danger" @click="batchRemoveCases">{{ t('common.batchDelete') }} ({{ selectedCaseIds.length }})</el-button>
          <el-button @click="batchToggleDep(true)">{{ t('page.test.enableDep') }}</el-button>
          <el-button @click="batchToggleDep(false)">{{ t('page.test.disableDep') }}</el-button>
        </template>
      </div>
      <el-table
        ref="caseTableRef"
        :data="filteredCases"
        row-key="_uid"
        max-height="340"
        style="width: 100%"
        @selection-change="onCaseSelectionChange"
      >
        <el-table-column type="selection" :width="50" />
        <el-table-column prop="id" label="ID" :width="70" />
        <el-table-column prop="title" :label="t('page.functional.caseName')" min-width="160" show-overflow-tooltip />
        <el-table-column prop="interface_name" :label="t('page.defects.interfaceName')" min-width="140" show-overflow-tooltip />
        <el-table-column label="Path" :width="220">
          <template #default="{ row }">
            <el-tag v-if="row.interface_method" size="small" style="margin-right: 4px">{{ row.interface_method }}</el-tag>
            <span class="path-text">{{ row.interface_path || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('page.apiCases.preconditionCases')" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="preconditionNamesMap[row.id] && preconditionNamesMap[row.id].length">
              <el-tag v-for="name in preconditionNamesMap[row.id]" :key="name" size="small" type="info" style="margin: 2px">{{ name }}</el-tag>
            </template>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('page.test.useDependency')" :width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.use_dependency" />
          </template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" :width="250" align="center">
          <template #default="{ row, $index }">
            <div class="table-cell-actions">
              <el-button link :disabled="$index === 0" @click="moveCase(row, -1)">{{ t('page.test.moveUp') }}</el-button>
              <el-button link :disabled="$index === filteredCases.length - 1" @click="moveCase(row, 1)">{{ t('page.test.moveDown') }}</el-button>
              <el-button link type="danger" @click="removeCase(row)">{{ t('common.delete') }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 嵌套：用例选择器（复用接口用例目录树组件） -->
    <ReuseCaseDialog v-model="showPicker" mode="select" :pre-selected-ids="existingCaseIds" @confirmed="onPickerConfirmed" />

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" :disabled="!canSave" @click="save">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createSuite } from '@/api/testManagement'
import { batchGetApiCases } from '@/api/apiTest'
import { useProjectScope } from '@/composables/useProjectScope'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import ReuseCaseDialog from '@/components/api-test/ReuseCaseDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()

// ── Form ──
const form = reactive({
  suite_name: '',
  type: 'api',
  description: '',
  environment_id: null,
  run_mode: 'serial',
})

// ── Associated cases (local state) ──
let uidCounter = 0
const associatedCases = ref([])
const caseSearch = ref('')
const selectedCaseIds = ref([])
const caseTableRef = ref(null)

// ── Precondition names cache (caseId → [name, ...]) ──
const preconditionNamesMap = ref({})

async function loadPreconditionNames(caseIds) {
  if (!caseIds.length) return
  try {
    var res = await batchGetApiCases(caseIds)
    var cases = res.data.data || []
    var allPreIds = []
    var casePreMap = {}
    cases.forEach(function (c) {
      var preIds = (c.case_payload || {}).precondition_ids || []
      if (preIds.length) {
        casePreMap[c.id] = preIds
        preIds.forEach(function (pid) { if (!allPreIds.includes(pid)) allPreIds.push(pid) })
      }
    })
    if (!allPreIds.length) return
    // Load precondition case details to get names
    var preRes = await batchGetApiCases(allPreIds)
    var preCases = preRes.data.data || []
    var preNameMap = {}
    preCases.forEach(function (pc) { preNameMap[pc.id] = pc.title || pc.name || '' })
    // Build names map
    for (var cid in casePreMap) {
      preconditionNamesMap.value[cid] = casePreMap[cid].map(function (pid) { return preNameMap[pid] || '' }).filter(Boolean)
    }
  } catch (e) {
    console.error('[SuiteCreateDialog] loadPreconditionNames failed:', e)
  }
}

const filteredCases = computed(() => {
  const kw = caseSearch.value.trim().toLowerCase()
  if (!kw) return associatedCases.value
  return associatedCases.value.filter(
    (c) =>
      (c.title || '').toLowerCase().includes(kw) ||
      (c.interface_name || '').toLowerCase().includes(kw)
  )
})

const canSave = computed(() => {
  return (
    form.suite_name?.trim() &&
    (form.type !== 'api' || form.environment_id) &&
    associatedCases.value.length > 0
  )
})

const saving = ref(false)

// ── Case table operations ──
function onCaseSelectionChange(rows) {
  selectedCaseIds.value = rows.map((r) => r._uid)
}

function moveCase(row, dir) {
  const arr = associatedCases.value
  const idx = arr.findIndex((c) => c._uid === row._uid)
  const ni = idx + dir
  if (ni < 0 || ni >= arr.length) return
  const copy = [...arr];
  [copy[idx], copy[ni]] = [copy[ni], copy[idx]]
  associatedCases.value = copy
}

async function removeCase(row) {
  try {
    await ElMessageBox.confirm(
      t('page.test.suites.removeCaseConfirm', { name: row.title }),
      t('common.warning'),
      { type: 'warning' }
    )
  } catch { return }
  associatedCases.value = associatedCases.value.filter((c) => c._uid !== row._uid)
}

async function batchRemoveCases() {
  try {
    await ElMessageBox.confirm(
      t('page.test.suites.batchRemoveCaseConfirm', { count: selectedCaseIds.value.length }),
      t('common.warning'),
      { type: 'warning' }
    )
  } catch { return }
  const ids = new Set(selectedCaseIds.value)
  associatedCases.value = associatedCases.value.filter((c) => !ids.has(c._uid))
  selectedCaseIds.value = []
}

function batchToggleDep(enable) {
  const ids = new Set(selectedCaseIds.value)
  associatedCases.value.forEach((c) => {
    if (ids.has(c._uid)) c.use_dependency = enable
  })
}

// ── Case picker (ReuseCaseDialog in select mode) ──
const showPicker = ref(false)
const existingCaseIds = computed(() => associatedCases.value.map((c) => c.id))

function onPickerConfirmed(selectedCases) {
  if (!selectedCases || !selectedCases.length) return
  const existingIds = new Set(associatedCases.value.map((c) => c.id))
  const newCases = selectedCases
    .filter((c) => !existingIds.has(c.id))
    .map((c) => ({
      _uid: ++uidCounter,
      id: c.id,
      title: c.title,
      interface_name: c.interface_name,
      interface_path: c.interface_path,
      interface_method: c.interface_method,
      use_dependency: true,
    }))
  if (newCases.length) {
    associatedCases.value = [...associatedCases.value, ...newCases]
    // Load precondition names for newly added cases
    loadPreconditionNames(newCases.map(c => c.id))
  }
}

// ── Save ──
async function save() {
  if (!form.suite_name?.trim()) {
    ElMessage.warning(t('page.test.suites.suiteNameRequired'))
    return
  }
  if (form.type === 'api' && !form.environment_id) {
    ElMessage.warning(t('page.test.suites.envRequired'))
    return
  }
  if (!associatedCases.value.length) {
    ElMessage.warning(t('page.test.suites.casesRequired'))
    return
  }
  saving.value = true
  try {
    const params = withProjectParams()
    await createSuite({
      project_id: params.project_id,
      suite_name: form.suite_name.trim(),
      type: form.type,
      description: form.description || null,
      environment_id: form.environment_id,
      run_mode: form.run_mode,
      cases: associatedCases.value.map((c) => ({
        case_id: c.id,
        use_dependency: c.use_dependency,
      })),
    })
    ElMessage.success(t('common.saved'))
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    saving.value = false
  }
}

// ── Reset on open ──
function onOpen() {
  Object.assign(form, {
    suite_name: '',
    type: 'api',
    description: '',
    environment_id: null,
    run_mode: 'serial',
  })
  associatedCases.value = []
  caseSearch.value = ''
  selectedCaseIds.value = []
  uidCounter = 0
}
</script>

<style scoped>
.suite-form {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.suite-cases-section {
  margin-top: 4px;
}

.suite-cases-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.suite-cases-count {
  font-weight: normal;
  color: var(--el-text-color-secondary);
}

.suite-cases-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.path-text {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
</style>
