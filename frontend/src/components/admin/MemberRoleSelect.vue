<template>
  <el-select :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <el-option
      v-for="item in roleOptions"
      :key="item.value"
      :label="t(`role.${item.label}`)"
      :value="item.value"
    />
  </el-select>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { PROJECT_MEMBER_ROLES, PROJECT_ROLE } from '@/utils/constants'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  allowAdmin: { type: Boolean, default: false },
})

defineEmits(['update:modelValue'])
const { t } = useI18n()

const roleOptions = computed(() => {
  if (props.allowAdmin) {
    return [...PROJECT_MEMBER_ROLES, { value: PROJECT_ROLE.OWNER, label: 'admin' }]
  }
  return PROJECT_MEMBER_ROLES
})
</script>
