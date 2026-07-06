<template>
  <el-dialog :close-on-click-modal="false"
    :model-value="modelValue"
    :title="t('page.agent.newSession')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-form label-width="auto">
      <el-form-item :label="t('page.agent.sessionTitle')">
        <el-input v-model="form.title" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item :label="t('page.agent.requirement')">
        <el-input
          v-model="form.requirement_text"
          type="textarea"
          :rows="textareaRows"
          :style="{ maxHeight: `${bodyMaxHeight}px` }"
        />
      </el-form-item>
      <el-form-item :label="t('page.agent.knowledgeDoc')">
        <el-input-number v-model="form.knowledge_document_id" :min="1" controls-position="right" style="width: 100%" />
      </el-form-item>
      <el-form-item :label="t('page.agent.prompt')">
        <el-input v-model="form.user_prompt" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.create') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useContentDialog } from '@/composables/useContentDialog'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  initialRequirement: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(240)
const textareaRows = computed(() => Math.max(6, Math.floor(bodyMaxHeight.value / 28)))

const form = reactive({
  title: '',
  requirement_text: '',
  knowledge_document_id: null,
  user_prompt: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.title = ''
      form.requirement_text = props.initialRequirement || ''
      form.knowledge_document_id = null
      form.user_prompt = ''
    }
  },
)

function submit() {
  if (!form.requirement_text?.trim() && !form.knowledge_document_id) {
    ElMessage.warning(t('page.agent.requirementRequired'))
    return
  }
  emit('submit', {
    title: form.title || undefined,
    requirement_text: form.requirement_text || undefined,
    knowledge_document_id: form.knowledge_document_id || undefined,
    user_prompt: form.user_prompt || undefined,
  })
}
</script>
