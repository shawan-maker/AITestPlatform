<template>
  <el-dialog
    v-model="visible"
    :title="t('page.knowledge.reupload')"
    width="480px"
    destroy-on-close
    @closed="fileList = []"
  >
    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      :file-list="fileList"
      @change="onFileChange"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">{{ t('page.knowledge.reuploadHint') }}</div>
    </el-upload>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="submit">
        {{ t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { UploadFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const fileList = ref([])
const selectedFile = ref(null)

function onFileChange(uploadFile, uploadFiles) {
  fileList.value = uploadFiles.slice(-1)
  selectedFile.value = uploadFile?.raw ?? null
}

function submit() {
  if (!selectedFile.value) return
  const fd = new FormData()
  fd.append('file', selectedFile.value)
  emit('submit', fd)
}
</script>
