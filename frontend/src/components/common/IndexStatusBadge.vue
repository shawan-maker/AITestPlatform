<template>
  <StatusTag :status="displayStatus" :map="statusMap" />
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { INDEX_STATUS_TYPES } from '@/utils/constants'
import { resolveParseDisplayStatus } from '@/utils/knowledge'
import StatusTag from '@/components/common/StatusTag.vue'

const props = defineProps({
  status: { type: String, default: '' },
  docType: { type: String, default: '' },
  parseStatus: { type: String, default: '' },
})

const { t } = useI18n()

const displayStatus = computed(() =>
  resolveParseDisplayStatus({
    index_status: props.status,
    doc_type: props.docType,
    parse_status: props.parseStatus,
  }),
)

const statusMap = computed(() => {
  const base = Object.fromEntries(
    Object.entries(INDEX_STATUS_TYPES).map(([key, type]) => [
      key,
      { type, label: t(`indexStatus.${key}`) },
    ]),
  )
  base.parsed = { type: 'success', label: t('indexStatus.parsed') }
  return base
})
</script>
