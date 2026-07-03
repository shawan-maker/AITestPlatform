<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder || t('page.apiCases.selectEnv')"
    filterable
    clearable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option v-for="e in environments" :key="e.id" :label="e.env_name || e.name" :value="e.id" />
  </el-select>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listEnvironments } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'

defineProps({
  modelValue: { type: [Number, null], default: null },
  placeholder: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const { t } = useI18n()
const { projectId, withProjectParams } = useProjectScope()
const environments = ref([])

async function load() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  environments.value = res.data.data?.items ?? []
}

onMounted(load)
// 直接监听 projectId 而非 withProjectParams()，避免每次返回新对象导致 watch 引用比较失效
watch(projectId, () => {
  load()
})

defineExpose({ environments })
</script>
