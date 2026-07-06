<template>
  <div>
    <RunProgressPanel v-if="activeRun" :progress="progress" />
    <AppTable :data="history">
      <AppTableColumn prop="id" variant="fixed" label="ID" :width="70" />
      <AppTableColumn variant="fixed" :label="t('common.status')" :width="100">
        <template #default="{ row }"><StatusTag :status="row.status" :map="runStatusMap" /></template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.test.totalCases')" :width="90">
        <template #default="{ row }">{{ row.total_cases ?? '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.test.successRate')" :width="140">
        <template #default="{ row }">{{ row.success_rate || '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('execution.duration')" :width="100">
        <template #default="{ row }">{{ row.duration_ms ? (row.duration_ms / 1000).toFixed(1) + 's' : '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.test.executor')" :width="100">
        <template #default="{ row }">{{ row.triggered_by_name || '-' }}</template>
      </AppTableColumn>
      <AppTableColumn variant="fixed" :label="t('page.test.startedAt')" :width="170">
        <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
      </AppTableColumn>
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :button-labels="[t('page.test.report')]">
        <template #default="{ row }">
          <el-button link type="primary" @click="$emit('viewReport', row)">{{ t('page.test.report') }}</el-button>
        </template>
      </AppTableColumn>
    </AppTable>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getRunStatusMap } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import RunProgressPanel from './RunProgressPanel.vue'

const { t } = useI18n()
const runStatusMap = computed(() => getRunStatusMap(t))

defineProps({
  history: { type: Array, default: () => [] },
  activeRun: { type: Object, default: null },
  progress: { type: Object, default: null },
})

defineEmits(['viewReport'])
</script>
