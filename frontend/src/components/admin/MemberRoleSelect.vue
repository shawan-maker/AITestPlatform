<template>
  <el-select :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <el-option
      v-for="item in PROJECT_MEMBER_ROLES"
      :key="item.value"
      :label="t(`role.${item.label}`)"
      :value="item.value"
    />
  </el-select>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { PROJECT_MEMBER_ROLES } from '@/utils/constants'

defineProps({ modelValue: { type: Number, default: 0 } })
defineEmits(['update:modelValue'])
const { t } = useI18n()
</script>
