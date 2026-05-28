<template>
  <el-dialog v-model="visible" :title="t('page.requirements.confirmTitle')" width="560px" destroy-on-close>
    <el-alert v-if="candidate?.version_no" :title="t('page.requirements.versionHint', { v: candidate.version_no })" type="info" show-icon :closable="false" style="margin-bottom: 12px" />
    <el-form label-width="100px">
      <el-form-item :label="t('page.requirements.title')">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item :label="t('page.requirements.description')">
        <el-input v-model="form.description" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="form.module_id" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  candidate: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ title: '', description: '', module_id: null })

watch(
  () => props.candidate,
  (c) => {
    form.title = c?.title ?? ''
    form.description = c?.description ?? ''
    form.module_id = c?.module_id ?? null
  },
  { immediate: true },
)

function submit() {
  emit('confirm', { ...form })
}
</script>
