<template>
  <el-select
    :model-value="modelValue"
    filterable
    remote
    clearable
    :remote-method="search"
    :loading="loading"
    :placeholder="t('page.env.variables.selectFile')"
    style="width: 100%"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="item.name || item.file_name"
      :value="item.id"
    />
  </el-select>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listUploadedFiles } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Number, default: null },
  projectId: { type: Number, required: true },
})

defineEmits(['update:modelValue'])

const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const options = ref([])
const loading = ref(false)

async function search(keyword = '') {
  const params = withProjectParams({
    project_id: props.projectId,
    keyword: keyword || undefined,
    page: 1,
    page_size: 50,
  })
  if (!params) return
  loading.value = true
  try {
    const res = await listUploadedFiles(params)
    options.value = res.data.data?.items ?? []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.projectId,
  () => search(''),
  { immediate: true },
)
</script>
