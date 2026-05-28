<template>
  <StatusTag :status="status" :map="INDEX_STATUS_MAP" />
</template>

<script setup>
import { INDEX_STATUS_MAP } from '@/utils/constants'
import StatusTag from '@/components/common/StatusTag.vue'

defineProps({ status: { type: String, default: '' } })
</script>
