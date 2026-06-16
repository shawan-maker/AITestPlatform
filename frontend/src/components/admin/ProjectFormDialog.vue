<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="isEdit ? t('page.admin.projects.edit') : t('page.admin.projects.create')" width="480px" @closed="reset">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item :label="t('page.admin.projects.name')" prop="name">
        <el-input v-model="form.name" maxlength="100" show-word-limit />
      </el-form-item>
      <el-form-item :label="t('page.admin.projects.description')" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()
const formRef = ref()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.project?.id)

const form = reactive({ name: '', description: '' })
const rules = {
  name: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
}

watch(
  () => props.project,
  (p) => {
    form.name = p?.name ?? ''
    form.description = p?.description ?? ''
  },
  { immediate: true },
)

function reset() {
  formRef.value?.resetFields()
}

async function submit() {
  await formRef.value?.validate()
  emit('submit', { name: form.name, description: form.description })
}
</script>
