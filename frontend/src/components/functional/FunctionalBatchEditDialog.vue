<template>
  <el-dialog v-model="visible" :title="t('page.functional.batchEdit')" width="480px">
    <el-alert :title="t('page.functional.batchEditHint', { count: caseIds.length })" type="info" show-icon :closable="false" />
    <el-form label-width="100px" style="margin-top: 16px">
      <el-form-item :label="t('page.functional.priority')">
        <el-input v-model="form.priority" clearable />
      </el-form-item>
      <el-form-item :label="t('page.functional.module')">
        <ModuleSelect v-model="form.module_id" clearable />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :disabled="!hasChanges" :loading="loading" @click="submit">
        {{ t('common.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ priority: '', module_id: null })

const hasChanges = computed(() => form.priority !== '' || form.module_id != null)

watch(visible, (v) => {
  if (v) {
    form.priority = ''
    form.module_id = null
  }
})

function submit() {
  const payload = { case_ids: props.caseIds }
  if (form.priority) payload.priority = form.priority
  if (form.module_id != null) payload.module_id = form.module_id
  emit('submit', payload)
}
</script>
