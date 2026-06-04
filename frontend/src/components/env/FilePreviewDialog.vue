<template>
  <el-dialog
    v-model="visible"
    :title="fileName || t('page.env.files.preview')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <FilePreviewPanel v-if="fileId" :file-id="fileId" :file-name="fileName" />
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContentDialog } from '@/composables/useContentDialog'
import FilePreviewPanel from '@/components/env/FilePreviewPanel.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  fileId: { type: Number, default: null },
  fileName: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass } = useContentDialog()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
