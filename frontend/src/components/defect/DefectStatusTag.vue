<template>
  <StatusTag :status="status" :map="defectStatusMap" />
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDefectStatusMap } from '@/utils/constants'
import StatusTag from '@/components/common/StatusTag.vue'

defineProps({ status: { type: String, default: '' } })
const { t } = useI18n()
const defectStatusMap = computed(() => getDefectStatusMap(t))
</script>
