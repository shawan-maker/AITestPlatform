<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder || t('page.apiCases.selectEnv')"
    filterable
    clearable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
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
const { withProjectParams } = useProjectScope()
const environments = ref([])

async function load() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  environments.value = res.data.data?.items ?? []
}

onMounted(load)
watch(() => withProjectParams(), load)
</script>
