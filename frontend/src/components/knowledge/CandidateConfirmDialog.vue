<template>
  <el-dialog
    v-model="visible"
    :title="t('page.knowledge.saveRequirement')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
    destroy-on-close
    @opened="onOpened"
  >
    <el-alert
      v-if="versionLabel"
      :title="t('page.requirements.versionHint', { v: versionLabel })"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />
    <el-alert
      v-if="previewTruncated"
      :title="t('page.knowledge.previewTruncatedHint')"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />
    <el-form v-loading="loadingText" label-width="100px" class="candidate-form">
      <el-form-item :label="t('page.requirements.title')">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item :label="t('page.requirements.description')">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="16"
          :style="{ maxHeight: `${bodyMaxHeight}px` }"
        />
      </el-form-item>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="form.module_id" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="onCancel">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getVersionTextPreview } from '@/api/knowledge'
import { useContentDialog } from '@/composables/useContentDialog'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import { formatDocumentVersionTitle } from '@/utils/knowledge'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  candidate: { type: Object, default: null },
  documentId: { type: Number, default: null },
  versionId: { type: Number, default: null },
  documentTitle: { type: String, default: '' },
  versionLabel: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])
const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(220)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ title: '', description: '', module_id: null })
const loadingText = ref(false)
const previewTruncated = ref(false)

const versionLabel = computed(
  () =>
    props.versionLabel ||
    props.candidate?.source_version_label ||
    props.candidate?.version_label ||
    '',
)

function defaultTitle() {
  return formatDocumentVersionTitle(props.documentTitle, versionLabel.value)
}

watch(
  () => [props.candidate, props.documentTitle, props.versionLabel],
  () => {
    form.title = defaultTitle()
    form.description = props.candidate?.description ?? ''
    form.module_id = props.candidate?.module_id ?? null
  },
  { immediate: true },
)

async function onOpened() {
  if (!props.documentId || !props.versionId) return
  loadingText.value = true
  previewTruncated.value = false
  try {
    const res = await getVersionTextPreview(props.documentId, props.versionId)
    const data = res.data.data
    if (data?.text) {
      form.description = data.text
      previewTruncated.value = !!data.truncated
    }
    if (data?.suggested_title) {
      form.title = data.suggested_title
    } else {
      form.title = defaultTitle()
    }
  } catch {
    // keep candidate preview
  } finally {
    loadingText.value = false
  }
}

function onCancel() {
  emit('cancel')
  visible.value = false
}

function submit() {
  emit('confirm', { ...form, direct_save: true })
}
</script>

<style scoped lang="scss">
.candidate-form :deep(.el-textarea__inner) {
  min-height: 320px;
}
</style>
