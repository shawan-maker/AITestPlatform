<template>
  <el-tag :type="tagType" size="small" effect="dark">{{ label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  value: { type: String, default: '' },
})

const { t } = useI18n()

const tagType = computed(() => {
  const map = { passed: 'success', failed: 'danger', blocked: 'warning', skipped: 'info' }
  return map[props.value] || 'info'
})
const label = computed(() => {
  const map = { pending: t('status.exec.pending'), passed: t('status.exec.passed'), failed: t('status.exec.failed'), blocked: t('status.exec.blocked'), skipped: t('status.exec.skipped') }
  return map[props.value] || props.value
})
</script>
