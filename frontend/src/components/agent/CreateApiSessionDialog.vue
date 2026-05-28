<template>
  <el-dialog
    :model-value="modelValue"
    :title="t('page.agent.newSession')"
    width="560px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-form label-width="120px">
      <el-form-item :label="t('page.agent.sessionTitle')">
        <el-input v-model="form.title" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item :label="t('page.agent.mode')">
        <el-radio-group v-model="mode">
          <el-radio value="interface">{{ t('page.agent.fromInterface') }}</el-radio>
          <el-radio value="doc">{{ t('page.agent.fromDoc') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="mode === 'interface'" :label="t('page.apiCases.interface')" required>
        <el-input-number v-model="form.interface_id" :min="1" controls-position="right" style="width: 100%" />
      </el-form-item>
      <el-form-item v-else :label="t('page.agent.apiDoc')" required>
        <el-input v-model="form.api_doc_text" type="textarea" :rows="6" />
      </el-form-item>
      <el-form-item :label="t('page.agent.prompt')">
        <el-input v-model="form.user_prompt" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.create') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  initialInterfaceId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const { t } = useI18n()
const mode = ref('interface')

const form = reactive({
  title: '',
  interface_id: null,
  api_doc_text: '',
  user_prompt: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      mode.value = props.initialInterfaceId ? 'interface' : 'interface'
      form.title = ''
      form.interface_id = props.initialInterfaceId || null
      form.api_doc_text = ''
      form.user_prompt = ''
    }
  },
)

function submit() {
  if (mode.value === 'interface' && !form.interface_id) {
    ElMessage.warning(t('validation.required'))
    return
  }
  if (mode.value === 'doc' && !form.api_doc_text?.trim()) {
    ElMessage.warning(t('validation.required'))
    return
  }
  emit('submit', {
    title: form.title || undefined,
    interface_id: mode.value === 'interface' ? form.interface_id : undefined,
    api_doc_text: mode.value === 'doc' ? form.api_doc_text : undefined,
    user_prompt: form.user_prompt || undefined,
  })
}
</script>
