<template>
  <el-dialog v-model="visible" :title="t('page.knowledge.upload')" width="520px" @closed="reset">
    <el-form label-width="100px">
      <el-form-item :label="t('page.knowledge.file')">
        <input ref="fileInput" type="file" @change="onFileChange" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="form.module_id" />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.docType')">
        <el-select v-model="form.doc_type">
          <el-option label="requirement" value="requirement" />
          <el-option label="api" value="api" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.upload') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'

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

const form = reactive({ module_id: null, doc_type: 'requirement' })

function onFileChange(e) {
  file.value = e.target.files?.[0] ?? null
}

function reset() {
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
  form.module_id = null
  form.doc_type = 'requirement'
}

function submit() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('doc_type', form.doc_type)
  if (form.module_id) fd.append('module_id', form.module_id)
  emit('submit', fd)
}
</script>
