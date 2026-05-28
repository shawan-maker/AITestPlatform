<template>
  <el-drawer :model-value="modelValue" :title="t('page.test.manualRun')" size="50%" @update:model-value="$emit('update:modelValue', $event)">
    <div v-loading="loading">
      <el-table :data="cases" border @row-click="openCase">
        <el-table-column prop="name" :label="t('page.functional.caseName')" />
        <el-table-column prop="result" :label="t('common.status')" width="100" />
      </el-table>
    </div>
    <el-dialog v-model="caseVisible" :title="currentCase?.name" width="480px">
      <el-radio-group v-model="caseResult">
        <el-radio label="pass">pass</el-radio>
        <el-radio label="fail">fail</el-radio>
        <el-radio label="block">block</el-radio>
        <el-radio label="skip">skip</el-radio>
      </el-radio-group>
      <template #footer>
        <el-button type="primary" @click="saveCase">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getManualContext, getManualCase, patchManualCase } from '@/api/testExecution'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  taskId: { type: Number, required: true },
  runId: { type: [Number, null], default: null },
})

defineEmits(['update:modelValue'])
const { t } = useI18n()

const loading = ref(false)
const cases = ref([])
const caseVisible = ref(false)
const currentCase = ref(null)
const caseResult = ref('pass')

async function load() {
  if (!props.runId) return
  loading.value = true
  try {
    const res = await getManualContext(props.runId)
    cases.value = res.data.data?.cases ?? res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

async function openCase(row) {
  const res = await getManualCase(props.runId, row.id ?? row.case_id)
  currentCase.value = res.data.data
  caseResult.value = currentCase.value.result ?? 'pass'
  caseVisible.value = true
}

async function saveCase() {
  await patchManualCase(props.runId, currentCase.value.case_id ?? currentCase.value.id, { result: caseResult.value })
  caseVisible.value = false
  load()
}

watch(() => props.modelValue, (v) => { if (v) load() })
</script>
