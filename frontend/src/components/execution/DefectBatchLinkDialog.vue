<template>
  <el-dialog v-model="visible" :title="t('execution.batchLink')" width="520px">
    <el-alert :title="t('execution.batchLinkHint', { count: caseRunIds.length })" type="info" show-icon :closable="false" />
    <el-form label-width="120px" style="margin-top: 16px">
      <el-form-item :label="t('execution.linkMode')">
        <el-radio-group v-model="mode">
          <el-radio value="external_key">{{ t('execution.modeExternalKey') }}</el-radio>
          <el-radio value="defect_id">{{ t('execution.modeDefectId') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="mode === 'external_key'" :label="t('execution.externalKey')">
        <el-input v-model="externalKey" :placeholder="t('execution.externalKeyPlaceholder')" />
      </el-form-item>
      <el-form-item v-else :label="t('page.defects.title')">
        <el-input-number v-model="defectId" :min="1" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseRunIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const mode = ref('external_key')
const externalKey = ref('')
const defectId = ref(null)

watch(visible, (v) => {
  if (v) {
    mode.value = 'external_key'
    externalKey.value = ''
    defectId.value = null
  }
})

function submit() {
  const payload = { case_run_ids: props.caseRunIds }
  if (mode.value === 'external_key') {
    payload.external_key = externalKey.value
  } else {
    payload.defect_id = defectId.value
  }
  emit('submit', payload)
}
</script>
