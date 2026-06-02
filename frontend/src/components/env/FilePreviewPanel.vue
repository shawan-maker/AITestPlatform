<template>
  <div v-loading="loading" class="file-preview-panel">
    <template v-if="previewType === 'image'">
      <img :src="objectUrl" :alt="fileName" class="file-preview-panel__image" />
    </template>
    <template v-else-if="previewType === 'json'">
      <MonacoJsonEditor v-model="textContent" read-only :height="360" />
    </template>
    <template v-else-if="previewType === 'text'">
      <pre v-if="!loadError" class="file-preview-panel__text">{{ textContent }}</pre>
      <EmptyState v-else :title="t('page.env.files.previewFailed')" />
    </template>
    <EmptyState v-else :title="t('page.env.files.noPreview')" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { downloadUploadedFile } from '@/api/environment'
import MonacoJsonEditor from '@/components/editor/MonacoJsonEditor.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps({
  fileId: { type: Number, default: null },
  fileName: { type: String, default: '' },
})

const { t } = useI18n()
const loading = ref(false)
const loadError = ref(false)
const textContent = ref('')
const objectUrl = ref('')

const ext = computed(() => (props.fileName?.split('.').pop() ?? '').toLowerCase())

const previewType = computed(() => {
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext.value)) return 'image'
  if (['json'].includes(ext.value)) return 'json'
  if (['txt', 'xml', 'csv', 'log', 'md'].includes(ext.value)) return 'text'
  return 'unknown'
})

async function load() {
  if (!props.fileId) return
  loadError.value = false
  textContent.value = ''
  if (previewType.value === 'unknown') return
  loading.value = true
  try {
    const res = await downloadUploadedFile(props.fileId)
    const blob = res.data
    if (!(blob instanceof Blob)) {
      loadError.value = true
      return
    }
    if (previewType.value === 'image') {
      if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
      objectUrl.value = URL.createObjectURL(blob)
    } else {
      textContent.value = await blob.text()
    }
  } catch {
    loadError.value = true
    textContent.value = ''
  } finally {
    loading.value = false
  }
}

watch(() => [props.fileId, props.fileName], load, { immediate: true })

onBeforeUnmount(() => {
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
})
</script>

<style scoped lang="scss">
.file-preview-panel {
  min-height: 200px;
}

.file-preview-panel__image {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.file-preview-panel__text {
  padding: 12px;
  background: var(--el-fill-color-light);
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
