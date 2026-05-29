<template>
  <el-select
    v-model="innerValue"
    filterable
    remote
    clearable
    reserve-keyword
    :remote-method="searchProjects"
    :loading="loading"
    :placeholder="placeholder || t('page.admin.projects.keyword')"
    @change="onChange"
  >
    <el-option v-for="p in options" :key="p.id" :label="p.name" :value="p.id" />
  </el-select>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listProjects } from '@/api/projects'

const props = defineProps({
  modelValue: { type: Number, default: null },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const innerValue = ref(props.modelValue)
const options = ref([])
const loading = ref(false)

watch(
  () => props.modelValue,
  (v) => { innerValue.value = v },
)

async function searchProjects(query) {
  loading.value = true
  try {
    const res = await listProjects({ name: query?.trim() || undefined, page: 1, page_size: 30 })
    options.value = res.data.data?.items ?? []
  } catch {
    options.value = []
  } finally {
    loading.value = false
  }
}

function onChange(v) {
  emit('update:modelValue', v ?? null)
}

searchProjects('')
</script>
