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
              :data="getInterfaceBaseCases(idx)"
              border
              size="small"
              row-key="_index"
              @selection-change="(sel) => onSelectionChange(idx, sel)"
            >
              <el-table-column type="selection" width="45" />
              <el-table-column prop="name" :label="t('page.agent.caseName') || '用例名称'" min-width="200">
                <template #default="{ row }">
                  <el-input v-model="row.name" size="small" />
                </template>
              </el-table-column>
              <el-table-column :label="t('page.agent.steps') || '步骤'" min-width="250">
                <template #default="{ row }">
                  <el-input
                    v-model="row._stepsText"
                    type="textarea"
                    :rows="2"
                    size="small"
                    @blur="syncStepsFromText(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="t('common.expected') || '预期结果'" min-width="250">
                <template #default="{ row }">
                  <el-input
                    v-model="row._expectedText"
                    type="textarea"
                    :rows="2"
                    size="small"
                    @blur="syncExpectedFromText(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="t('common.dependencies') || '依赖'" width="180">
                <template #default="{ row }">
                  <el-input
                    v-model="row._depsText"
                    size="small"
                    @blur="syncDepsFromText(row)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div class="edit-dialog__iface-summary">
            {{ t('page.agent.selectedCases') || '已选' }}: {{ selectedPerInterface[idx]?.length || 0 }} / {{ getInterfaceBaseCases(idx).length }}
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
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  interfaces: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'save'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const activeTab = ref('0')
const saving = ref(false)
const selectedPerInterface = ref({})

// Build editable base cases per interface
function getInterfaceBaseCases(ifaceIndex) {
  const iface = props.interfaces[ifaceIndex]
  if (!iface) return []
  const cases = iface.base_cases || []
  return cases.map((c, i) => ({
    ...c,
    _index: i,
    _stepsText: Array.isArray(c.steps) ? c.steps.join('\n') : '',
    _expectedText: Array.isArray(c.expected) ? c.expected.join('\n') : '',
    _depsText: Array.isArray(c.dependencies) ? c.dependencies.join(', ') : '',
  }))
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
}

function onSave() {
  saving.value = true
  const result = []
  for (let i = 0; i < props.interfaces.length; i++) {
    const iface = props.interfaces[i]
    const cases = getInterfaceBaseCases(i)
    const selected = selectedPerInterface.value[i] || cases.map((_, idx) => idx)
    result.push({
      index: i,
      selected_indexes: selected,
      edited_cases: cases.map(c => ({
        name: c.name,
        steps: c.steps,
        expected: c.expected,
        dependencies: c.dependencies,
      })),
    })
  }
  emit('save', result)
  visible.value = false
  saving.value = false
}

// Initialize selected indexes when dialog opens
watch(() => props.modelValue, (v) => {
  if (v) {
    selectedPerInterface.value = {}
    for (let i = 0; i < props.interfaces.length; i++) {
      const iface = props.interfaces[i]
      selectedPerInterface.value[i] = iface.selected_indexes || (iface.base_cases || []).map((_, idx) => idx)
    }
    activeTab.value = '0'
  }
})
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
</style>
