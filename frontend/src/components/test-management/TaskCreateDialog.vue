<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.test.tasks.create')" width="1100px" @closed="onClosed">
    <div class="task-create-body">
      <!-- 表单区 -->
      <el-form label-width="auto" class="task-form">
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item :label="t('page.test.tasks.taskName')" required>
              <el-input v-model="form.task_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('page.test.taskType')" required>
              <el-radio-group v-model="form.type" @change="onTypeChange">
                <el-radio value="api">API</el-radio>
                <el-radio value="functional">{{ t('page.test.manualType') }}</el-radio>
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
          <el-col v-if="isApiType" :span="12">
            <el-form-item :label="t('page.apiCases.selectEnv')" required>
              <EnvironmentSelect v-model="form.environment_id" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row v-if="isApiType" :gutter="24">
          <el-col :span="12">
            <el-form-item :label="t('page.test.runMode')" required>
              <el-radio-group v-model="form.run_mode">
                <el-radio value="serial">{{ t('page.test.serial') }}</el-radio>
                <el-radio value="parallel">{{ t('page.test.parallel') }}</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 关联套件 (API任务) -->
      <div v-if="isApiType" class="association-section">
        <div class="association-toolbar">
          <span class="association-label">{{ t('page.test.tabSuites') }}</span>
          <div class="association-actions">
            <el-button type="primary" size="small" @click="showSuitePicker = true">{{ t('page.test.addSuites') }}</el-button>
            <el-button v-if="selectedSuiteRows.length" type="danger" size="small" @click="batchRemoveSuites">{{ t('common.batchDelete') }} ({{ selectedSuiteRows.length }})</el-button>
          </div>
        </div>
        <el-table :data="associatedSuites" size="small" border max-height="300" @selection-change="onSuiteRowSelect">
          <el-table-column type="selection" :width="40" />
          <el-table-column prop="id" label="ID" :width="60" />
          <el-table-column prop="suite_name" :label="t('page.test.suites.suiteName')" />
          <el-table-column prop="case_count" :label="t('page.test.caseCount')" :width="80" />
          <el-table-column :label="t('common.actions')" :width="250">
            <template #default="{ row, $index }">
              <div class="table-cell-actions">
                <el-button link :disabled="$index === 0" @click="moveSuite(row, -1)">{{ t('page.test.moveUp') }}</el-button>
                <el-button link :disabled="$index === associatedSuites.length - 1" @click="moveSuite(row, 1)">{{ t('page.test.moveDown') }}</el-button>
                <el-button link type="danger" @click="removeSuite(row)">{{ t('common.delete') }}</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 关联用例 (手工/功能任务) -->
      <div v-if="isManualType" class="association-section">
        <div class="association-toolbar">
          <span class="association-label">{{ t('page.test.tabCases') }}</span>
          <div class="association-actions">
            <el-button type="primary" size="small" @click="openCasePicker">{{ t('page.test.addCases') }}</el-button>
          </div>
        </div>
        <el-table :data="associatedCases" size="small" border max-height="300">
          <el-table-column prop="case_no" :label="t('page.functional.caseNo')" :width="130" show-overflow-tooltip />
          <el-table-column prop="case_name" :label="t('page.functional.caseName')" min-width="150" show-overflow-tooltip />
          <el-table-column :label="t('page.functional.priority')" :width="80">
            <template #default="{ row }">
              <PriorityTag v-if="row.priority" :value="row.priority" />
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('page.functional.caseCategory')" :width="100">
            <template #default="{ row }">
              {{ row.case_category ? t('page.functional.cat' + row.case_category.charAt(0).toUpperCase() + row.case_category.slice(1)) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="module_name" :label="t('page.knowledge.module')" :width="120">
            <template #default="{ row }">{{ row.module_name || '-' }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" :width="80">
            <template #default="{ row }">
              <div class="table-cell-actions">
                <el-button link type="danger" @click="removeCase(row)">{{ t('common.delete') }}</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
    </template>

    <!-- 套件选择弹窗 -->
    <el-dialog v-model="showSuitePicker" :title="t('page.test.addSuites')" width="700px" append-to-body>
      <el-input v-model="suiteSearch" :placeholder="t('page.test.suites.suiteName')" clearable size="small" style="width: 260px; margin-bottom: 12px" @change="loadSuitePicker" />
      <PaginatedTable v-model:page="spPage" v-model:page-size="spPageSize" :data="suitePickerItems" :loading="suitePickerLoading" :total="suitePickerTotal" row-key="id" @page-change="loadSuitePicker" @selection-change="onSuitePickerSelect">
        <el-table-column type="selection" :width="40" />
        <el-table-column prop="id" label="ID" :width="60" />
        <el-table-column prop="suite_name" :label="t('page.test.suites.suiteName')" />
        <el-table-column prop="case_count" :label="t('page.test.caseCount')" :width="80" />
      </PaginatedTable>
      <template #footer>
        <el-button @click="showSuitePicker = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="addSuites">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 用例选择弹窗 (目录树+列表) -->
    <FunctionalCasePickerDialog
      v-model="showCasePicker"
      :project-id="projectId"
      :pre-selected-ids="associatedCases.map(c => c.id)"
      :pre-selected-case-map="associatedCaseMap"
      @confirmed="onCasePickerConfirmed"
    />
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createTask, replaceTaskSuites, replaceTaskCases, pickSuites } from '@/api/testManagement'
import { usePagination } from '@/composables/usePagination'
import { useProjectScope } from '@/composables/useProjectScope'
import PaginatedTable from '@/components/common/PaginatedTable.vue'
import EnvironmentSelect from '@/components/picker/EnvironmentSelect.vue'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import FunctionalCasePickerDialog from '@/components/functional/FunctionalCasePickerDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// Form
const form = ref({ task_name: '', type: 'api', description: '', environment_id: null, run_mode: 'serial' })
const saving = ref(false)
const isApiType = computed(() => form.value.type === 'api' || form.value.type === 'ui')
const isManualType = computed(() => form.value.type === 'functional')

function onTypeChange() {
  form.value.environment_id = null
  form.value.run_mode = 'serial'
  associatedSuites.value = []
  associatedCases.value = []
}

// --- Suite association ---
const associatedSuites = ref([])
const selectedSuiteRows = ref([])
const suiteSearch = ref('')
const showSuitePicker = ref(false)
const suitePickerItems = ref([])
const suitePickerLoading = ref(false)
const suitePickerTotal = ref(0)
const suitePickerSelected = ref([])
const { page: spPage, pageSize: spPageSize } = usePagination()

function onSuiteRowSelect(rows) { selectedSuiteRows.value = rows.map(r => r.id) }
function removeSuite(row) { associatedSuites.value = associatedSuites.value.filter(s => s.id !== row.id) }
function batchRemoveSuites() { associatedSuites.value = associatedSuites.value.filter(s => !selectedSuiteRows.value.includes(s.id)); selectedSuiteRows.value = [] }
function moveSuite(row, dir) {
  var arr = associatedSuites.value
  var idx = arr.findIndex(s => s.id === row.id)
  var ni = idx + dir
  if (ni < 0 || ni >= arr.length) return
  ;[arr[idx], arr[ni]] = [arr[ni], arr[idx]]
  associatedSuites.value = [...arr]
}

async function loadSuitePicker() {
  if (!props.projectId) return
  suitePickerLoading.value = true
  try {
    var res = await pickSuites({ project_id: props.projectId, q: suiteSearch.value || undefined, page: spPage.value, page_size: spPageSize.value })
    suitePickerItems.value = res.data.data?.items ?? []
    suitePickerTotal.value = res.data.data?.total ?? 0
  } finally { suitePickerLoading.value = false }
}
function onSuitePickerSelect(rows) { suitePickerSelected.value = rows }
function addSuites() {
  var existingIds = new Set(associatedSuites.value.map(s => s.id))
  suitePickerSelected.value.forEach(s => {
    if (!existingIds.has(s.id)) associatedSuites.value.push(s)
  })
  showSuitePicker.value = false
  suitePickerSelected.value = []
}

// --- Case association ---
const associatedCases = ref([])
const showCasePicker = ref(false)
const associatedCaseMap = computed(() => {
  var map = {}
  associatedCases.value.forEach(function (c) { if (c.catalog_id) map[c.id] = c.catalog_id })
  return map
})

function removeCase(row) { associatedCases.value = associatedCases.value.filter(c => c.id !== row.id) }

function openCasePicker() { showCasePicker.value = true }

function onCasePickerConfirmed(selectedIds, selectedCases) {
  var existingIds = new Set(associatedCases.value.map(c => c.id))
  // Replace with full selection from picker (includes previously associated + newly added)
  associatedCases.value = selectedCases || []
  showCasePicker.value = false
}

// --- Save ---
async function save() {
  if (!form.value.task_name?.trim()) {
    ElMessage.warning(t('page.test.tasks.taskName') + t('page.defects.required'))
    return
  }
  if (isApiType.value && !form.value.environment_id) {
    ElMessage.warning(t('page.apiCases.selectEnv') + t('page.defects.required'))
    return
  }
  saving.value = true
  try {
    var params = withProjectParams()
    var res = await createTask({ ...form.value, project_id: params.project_id })
    var taskId = res.data.data?.id
    // Save associations
    if (taskId && isApiType.value && associatedSuites.value.length) {
      await replaceTaskSuites(taskId, { suite_ids: associatedSuites.value.map(s => s.id) })
    }
    if (taskId && isManualType.value && associatedCases.value.length) {
      await replaceTaskCases(taskId, { case_ids: associatedCases.value.map(c => c.id) })
    }
    ElMessage.success(t('common.saved'))
    visible.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || t('common.requestFailed'))
  } finally {
    saving.value = false
  }
}

function onClosed() {
  form.value = { task_name: '', type: 'api', description: '', environment_id: null, run_mode: 'serial' }
  associatedSuites.value = []
  associatedCases.value = []
  selectedSuiteRows.value = []
  suiteSearch.value = ''
}

// Auto-load picker when dialog opens
watch(visible, (v) => {
  if (v && props.projectId) {
    loadSuitePicker()
  }
})
</script>

<style scoped lang="scss">
.task-create-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.task-form {
  flex-shrink: 0;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.association-section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 12px;
}
.association-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.association-label {
  font-weight: 600;
  font-size: 14px;
}
.association-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.picker-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
