<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.defects.createFromRun')" width="480px">
    <el-form label-width="100px">
      <el-form-item :label="t('page.defects.title')"><el-input v-model="form.title" /></el-form-item>
      <el-form-item :label="t('page.defects.category')">
        <el-select v-model="form.category"><el-option v-for="c in DEFECT_CATEGORY" :key="c" :label="c" :value="c" /></el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { DEFECT_CATEGORY } from '@/utils/constants'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseRunId: { type: Number, default: null },
  defaultTitle: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ title: props.defaultTitle, category: DEFECT_CATEGORY[0] })

function submit() {
  emit('submit', { case_run_id: props.caseRunId, ...form })
}
</script>
