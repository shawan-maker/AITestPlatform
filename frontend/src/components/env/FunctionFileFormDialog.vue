<template>
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="isEdit ? t('page.env.function.edit') : t('page.env.function.create')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="auto">
      <el-form-item :label="t('page.env.function.fileName')" prop="file_name">
        <el-input
          v-model="form.file_name"
          maxlength="100"
          :placeholder="t('page.env.function.fileNamePlaceholder')"
        />
      </el-form-item>
      <el-form-item :label="t('page.env.function.bindEnvironments')">
        <el-select v-model="form.environment_ids" multiple filterable style="width: 100%">
          <el-option
            v-for="env in envOptions"
            :key="env.id"
            :label="env.env_name"
            :value="env.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.env.function.sourceCode')" prop="source_code">
        <MonacoJsonEditor v-model="form.source_code" language="python" :height="editorHeight" />
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
import {
  createFunctionFile,
  getFunctionFile,
  listEnvironments,
  updateFunctionFile,
} from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'
import { useHalfScreenDialog } from '@/composables/useContentDialog'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'

const FUNCTION_FILE_PATTERN = /^[A-Za-z]([A-Za-z0-9_]*[A-Za-z0-9])?\.py$/

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  fileId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const { editorHeight, dialogWidth, dialogTop, dialogClass } = useHalfScreenDialog(320)
const formRef = ref()
const loading = ref(false)
const envOptions = ref([])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.fileId)

const defaultForm = () => ({
  file_name: '',
  source_code: 'def hello():\n    return 1\n',
  environment_ids: [],
})

function suggestFileName() {
  return `function_${Date.now().toString().slice(-6)}.py`
}

const form = reactive(defaultForm())

const rules = {
  file_name: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value || FUNCTION_FILE_PATTERN.test(value)) callback()
        else callback(new Error(t('page.env.function.fileNamePattern')))
      },
      trigger: 'blur',
    },
  ],
  source_code: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
}

async function loadEnvOptions() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  envOptions.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadFile() {
  if (!props.fileId) {
    Object.assign(form, defaultForm())
    form.file_name = suggestFileName()
    return
  }
  const res = await getFunctionFile(props.fileId)
  const f = res.data.data
  Object.assign(form, {
    file_name: f.file_name ?? '',
    source_code: f.source_code ?? '',
    environment_ids: [...(f.environment_ids ?? [])],
  })
}

watch(visible, async (v) => {
  if (v) {
    await loadEnvOptions()
    await loadFile()
  }
})

function reset() {
  formRef.value?.resetFields()
  Object.assign(form, defaultForm())
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const payload = {
      file_name: form.file_name,
      source_code: form.source_code,
      environment_ids: form.environment_ids,
    }
    if (isEdit.value) {
      await updateFunctionFile(props.fileId, payload)
    } else {
      const params = withProjectParams()
      await createFunctionFile(payload, params ?? {})
    }
    emit('saved')
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>
