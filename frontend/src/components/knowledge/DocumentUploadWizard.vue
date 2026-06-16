<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.knowledge.upload')" width="520px" @closed="reset">
    <el-form label-width="100px">
      <el-form-item :label="t('page.knowledge.file')" required>
        <input ref="fileInput" type="file" @change="onFileChange" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.titleCol')" required>
        <el-input v-model="form.title" maxlength="200" :placeholder="t('page.knowledge.titlePlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.docType')" required>
        <el-select v-model="form.doc_type" :placeholder="t('page.knowledge.docTypePlaceholder')">
          <el-option :label="t('page.knowledge.docTypeRequirement')" value="requirement" />
          <el-option :label="t('page.knowledge.docTypeApi')" value="api_doc" />
          <el-option :label="t('page.knowledge.docTypeOther')" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.doc_type === 'api_doc'" :label="t('page.knowledge.parseMode')" required>
        <el-select v-model="form.parse_mode" :placeholder="t('page.knowledge.parseModePlaceholder')">
          <el-option :label="t('page.knowledge.parseModeAi')" value="ai" />
          <el-option :label="t('page.knowledge.parseModeSwagger')" value="swagger" />
          <el-option :label="t('page.knowledge.parseModeOpenapi')" value="openapi" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="form.module_id" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.upload') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import {
  documentTitleFromFileName,
  formatDocumentVersionTitle,
  INITIAL_VERSION_LABEL,
} from '@/utils/knowledge'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()
const fileInput = ref()
const file = ref(null)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const defaultForm = () => ({
  title: '',
  doc_type: 'requirement',
  parse_mode: 'ai',
  module_id: null,
})

const form = reactive(defaultForm())

// doc_type 变化时，重置 parse_mode 逻辑
watch(() => form.doc_type, (newType) => {
  if (newType === 'api_doc') {
    form.parse_mode = 'ai' // 默认 ai，用户可切换
  } else {
    form.parse_mode = 'ai' // requirement / other 固定 ai
  }
})

function titleFromFile(selected) {
  const base = documentTitleFromFileName(selected?.name)
  return formatDocumentVersionTitle(base, INITIAL_VERSION_LABEL)
}

function onFileChange(e) {
  file.value = e.target.files?.[0] ?? null
  if (file.value) {
    form.title = titleFromFile(file.value)
  }
}

function reset() {
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
  Object.assign(form, defaultForm())
}

function submit() {
  if (!file.value) {
    ElMessage.warning(t('page.knowledge.fileRequired'))
    return
  }
  const title = form.title.trim()
  if (!title) {
    ElMessage.warning(t('page.knowledge.titleRequired'))
    return
  }
  if (!form.doc_type) {
    ElMessage.warning(t('page.knowledge.docTypePlaceholder'))
    return
  }
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('title', title)
  fd.append('doc_type', form.doc_type)
  // parse_mode: requirement/other 固定 ai；api_doc 用用户选择的值
  fd.append('parse_mode', form.doc_type === 'api_doc' ? form.parse_mode : 'ai')
  if (form.module_id != null) fd.append('module_id', String(form.module_id))
  emit('submit', fd)
}
</script>
