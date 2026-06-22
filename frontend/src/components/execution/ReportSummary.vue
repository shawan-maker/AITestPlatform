<template>
  <div v-if="report" class="report-summary">
    <div class="report-summary__charts">
      <div ref="passRateRef" class="report-summary__chart" />
      <div ref="defectRef" class="report-summary__chart" />
    </div>
    <el-descriptions :column="2" border style="margin-top: 16px">
      <el-descriptions-item :label="t('page.test.passRate')">{{ passRateDisplay }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.test.totalCases')">{{ totalCount }}</el-descriptions-item>
      <el-descriptions-item :label="t('execution.passed')">{{ passedCount }}</el-descriptions-item>
      <el-descriptions-item :label="t('execution.failed')">{{ failedCount }}</el-descriptions-item>
    </el-descriptions>
    <div v-if="envSnapshotSummary" class="env-snapshot">
      <div class="env-snapshot__label">{{ t('execution.envSnapshot') }}</div>
      <pre>{{ envSnapshotSummary }}</pre>
    </div>
    <ReportCaseTable
      v-if="cases.length"
      :cases="cases"
      :can-edit="canEdit"
      @view-log="$emit('view-log', $event)"
      @linked="$emit('linked')"
      @create-defect="$emit('create-defect', $event)"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { summarizePayload } from '@/utils/format'
import ReportCaseTable from './ReportCaseTable.vue'

echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  report: { type: Object, default: null },
  canEdit: { type: Boolean, default: true },
})

defineEmits(['view-log', 'linked', 'create-defect'])

const { t } = useI18n()
const passRateRef = ref(null)
const defectRef = ref(null)
let passChart = null
let defectChart = null

const summary = computed(() => props.report?.summary ?? props.report)
const cases = computed(() => props.report?.cases ?? [])
const defectChartData = computed(() => props.report?.defect_chart ?? [])

const totalCount = computed(() => summary.value?.total ?? summary.value?.total_count ?? 0)
const passedCount = computed(() => summary.value?.passed ?? summary.value?.passed_count ?? 0)
const failedCount = computed(() => summary.value?.failed ?? summary.value?.failed_count ?? 0)

const passRateDisplay = computed(() => {
  if (summary.value?.pass_rate_display) return summary.value.pass_rate_display
  const total = totalCount.value
  const passed = passedCount.value
  return total ? `${Math.round((passed / total) * 100)}%` : '0%'
})

const envSnapshotSummary = computed(() => {
  const snap = props.report?.env_snapshot
  if (!snap) return ''
  return summarizePayload(typeof snap === 'string' ? snap : JSON.stringify(snap, null, 2), 500)
})

function renderCharts() {
  if (passRateRef.value) {
    passChart?.dispose()
    passChart = echarts.init(passRateRef.value)
    const passed = passedCount.value
    const failed = failedCount.value
    const other = Math.max(0, totalCount.value - passed - failed)
    passChart.setOption({
      title: { text: t('page.test.passRate'), left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        data: [
          { name: t('execution.passed'), value: passed, itemStyle: { color: '#67c23a' } },
          { name: t('execution.failed'), value: failed, itemStyle: { color: '#f56c6c' } },
          { name: t('execution.other'), value: other, itemStyle: { color: '#909399' } },
        ].filter((d) => d.value > 0),
      }],
    })
  }
  if (defectRef.value) {
    defectChart?.dispose()
    defectChart = echarts.init(defectRef.value)
    const data = defectChartData.value.length
      ? defectChartData.value.map((d) => ({ name: d.severity, value: d.count }))
      : [{ name: t('execution.noDefects'), value: 1, itemStyle: { color: '#dcdfe6' } }]
    defectChart.setOption({
      title: { text: t('page.defects.severity'), left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '60%', data }],
    })
  }
}

watch(() => props.report, async () => {
  await nextTick()
  renderCharts()
}, { deep: true })

onMounted(async () => {
  await nextTick()
  renderCharts()
})

onBeforeUnmount(() => {
  passChart?.dispose()
  defectChart?.dispose()
})
</script>

<style scoped lang="scss">
.report-summary__charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.report-summary__chart {
  height: 220px;
  min-width: 0;
}

.env-snapshot {
  margin-top: 12px;

  &__label {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    margin-bottom: 4px;
  }

  pre {
    padding: 12px;
    background: var(--el-fill-color-light);
    max-height: 160px;
    overflow: auto;
    font-size: 12px;
  }
}
</style>
