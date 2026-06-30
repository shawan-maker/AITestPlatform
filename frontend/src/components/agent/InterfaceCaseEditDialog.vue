<template>
  <el-dialog
    v-model="visible"
    :title="t('page.agent.editBaseCases')"
    width="90vw"
    top="3vh"
    destroy-on-close
    @close="onClose"
  >
    <div class="edit-dialog__body">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane
          v-for="(iface, idx) in interfaces"
          :key="idx"
          :label="`${iface.method} ${iface.summary || iface.path}`"
          :name="String(idx)"
        >
          <div class="edit-dialog__table-wrap">
            <el-table
              ref="tableRefs"
              :data="editableCases[idx] || []"
              border
              size="small"
              row-key="_index"
              class="case-preview-table"
              @selection-change="(sel) => onSelectionChange(idx, sel)"
            >
              <el-table-column type="selection" width="40" />
              <el-table-column label="编号" width="55" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column prop="name" :label="t('page.agent.colCaseName')" min-width="160" align="left">
                <template #default="{ row }">
                  <el-input v-model="row.name" size="small" />
                </template>
              </el-table-column>
              <el-table-column :label="t('page.agent.colDependencies')" min-width="140" align="left">
                <template #default="{ row }">
                  <el-input
                    v-model="row._depsText"
                    size="small"
                    :placeholder="t('page.agent.colDependencies')"
                    @blur="syncDepsFromText(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="t('page.agent.colSteps')" min-width="260" align="left">
                <template #default="{ row }">
                  <el-input
                    v-model="row._stepsText"
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 8 }"
                    size="small"
                    @blur="syncStepsFromText(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="t('page.agent.colExpected')" min-width="240" align="left">
                <template #default="{ row }">
                  <el-input
                    v-model="row._expectedText"
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 8 }"
                    size="small"
                    @blur="syncExpectedFromText(row)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="edit-dialog__iface-summary">
            {{ t('page.agent.selectedCases') }}: {{ selectedPerInterface[idx]?.length || 0 }} / {{ (editableCases[idx] || []).length }}
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="edit-dialog__footer">
        <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">
          {{ t('page.agent.saveAndStructure') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  interfaces: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'save'])

const { t } = useI18n()

const visible = ref(false)
const activeTab = ref('0')
const saving = ref(false)
const tableRefs = ref([])
const selectedPerInterface = ref({})
// Pre-computed editable cases per interface (stable references)
const editableCases = ref({})

// Sync visible with modelValue
watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) initEditableCases()
})

watch(visible, (v) => {
  if (!v) emit('update:modelValue', false)
})

function initEditableCases() {
  const casesMap = {}
  const selectedMap = {}
  for (let i = 0; i < props.interfaces.length; i++) {
    const iface = props.interfaces[i]
    const baseCases = iface.base_cases || []
    casesMap[i] = baseCases.map((c, idx) => ({
      _index: idx,
      name: c.name || '',
      steps: Array.isArray(c.steps) ? [...c.steps] : [],
      expected: Array.isArray(c.expected) ? [...c.expected] : [],
      dependencies: Array.isArray(c.dependencies) ? [...c.dependencies] : [],
      _stepsText: Array.isArray(c.steps) ? c.steps.join('\n') : '',
      _expectedText: Array.isArray(c.expected) ? c.expected.join('\n') : '',
      _depsText: Array.isArray(c.dependencies) ? c.dependencies.join(', ') : '',
    }))
    // Initialize selection: use saved selected_indexes or select all
    const savedIndexes = iface.selected_indexes || baseCases.map((_, idx) => idx)
    selectedMap[i] = savedIndexes
  }
  editableCases.value = casesMap
  selectedPerInterface.value = selectedMap
  activeTab.value = '0'

  // After render, restore checkbox selections
  nextTick(() => {
    restoreTableSelections()
  })
}

function restoreTableSelections() {
  const tables = Array.isArray(tableRefs.value) ? tableRefs.value : [tableRefs.value]
  for (let i = 0; i < tables.length; i++) {
    const table = tables[i]
    if (!table) continue
    const cases = editableCases.value[i] || []
    const selected = selectedPerInterface.value[i] || []
    for (const idx of selected) {
      const row = cases.find(c => c._index === idx)
      if (row) {
        try { table.toggleRowSelection(row, true) } catch {}
      }
    }
  }
}

function syncStepsFromText(row) {
  row.steps = row._stepsText ? row._stepsText.split('\n').filter(Boolean) : []
}

function syncExpectedFromText(row) {
  row.expected = row._expectedText ? row._expectedText.split('\n').filter(Boolean) : []
}

function syncDepsFromText(row) {
  row.dependencies = row._depsText ? row._depsText.split(',').map(s => s.trim()).filter(Boolean) : []
}

function onSelectionChange(ifaceIndex, selection) {
  selectedPerInterface.value[ifaceIndex] = selection.map(s => s._index)
}

function onClose() {
  selectedPerInterface.value = {}
  editableCases.value = {}
}

function onSave() {
  saving.value = true
  const result = []
  for (let i = 0; i < props.interfaces.length; i++) {
    const cases = editableCases.value[i] || []
    // Force sync all textareas to arrays (in case user didn't blur before saving)
    for (const c of cases) {
      syncStepsFromText(c)
      syncExpectedFromText(c)
      syncDepsFromText(c)
    }
    const selected = selectedPerInterface.value[i] || cases.map(c => c._index)
    // Only send selected cases to reduce payload and avoid confusion
    const selectedCases = cases
      .filter(c => selected.includes(c._index))
      .map(c => ({
        _index: c._index,
        name: c.name,
        steps: c.steps,
        expected: c.expected,
        dependencies: c.dependencies,
      }))
    result.push({
      index: i,
      selected_indexes: selected,
      edited_cases: selectedCases,
    })
  }
  emit('save', result)
  visible.value = false
  saving.value = false
}
</script>

<style scoped lang="scss">
.edit-dialog__body {
  max-height: 70vh;
  overflow-y: auto;
}

.edit-dialog__table-wrap {
  max-height: 55vh;
  overflow-y: auto;
}

.edit-dialog__iface-summary {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: right;
}

.edit-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Match reference dialog styling */
.case-preview-table {
  :deep(.el-table__row) {
    td {
      padding: 8px 0;
    }
  }

  /* Remove number input spinners */
  :deep(input[type="number"]) {
    -moz-appearance: textfield;
    &::-webkit-inner-spin-button,
    &::-webkit-outer-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
  }

  /* Hide el-input number spinners */
  :deep(.el-input-number__decrease),
  :deep(.el-input-number__increase) {
    display: none;
  }

  /* Textarea auto-size styling */
  :deep(.el-textarea__inner) {
    line-height: 1.5;
    font-size: 13px;
  }
}
</style>
