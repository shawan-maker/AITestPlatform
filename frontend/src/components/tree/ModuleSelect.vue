<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder || t('page.knowledge.selectModule')"
    clearable
    filterable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" />
  </el-select>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useModuleSelect } from '@/composables/useModuleSelect'

defineProps({
  modelValue: { type: [Number, null], default: null },
  placeholder: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
const { t } = useI18n()
const { modules } = useModuleSelect()
</script>
