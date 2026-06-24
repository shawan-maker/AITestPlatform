<template>
  <div v-if="report" class="report-summary">
    <!-- 基本信息 -->
    <SectionPanel :title="t('execution.reportBasicInfo')">
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="t('page.test.suites.suiteName')">{{ report.suite_name || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t('page.test.relatedTask')">{{ report.task_name || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.duration')">{{ durationDisplay }}</el-descriptions-item>
        <el-descriptions-item :label="t('execution.startTime')">{{ formatTime(summary.start_time) }}</el-descriptions-item>
      </el-descriptions>
    </SectionPanel>

    <!-- 结果统计 -->
    <SectionPanel :title="t('execution.reportResultStats')" style="margin-top: 16px">
      <div class="report-summary__result-row">
        <div class="report-summary__result-tag">
          <span style="margin-right: 8px; font-weight: 500">{{ t('execution.execResult') }}：</span>
          <el-tag v-if="resultTagType" :type="resultTagType" size="small">{{ resultLabel }}</el-tag>
          <StatusTag v-else :status="summary.status" :map="RUN_STATUS_MAP" />
        </div>
        <div class="report-summary__count-badges">
          <el-tag type="info" effect="plain" size="small">{{ t('page.test.totalCases') }}: {{ totalCount }}</el-tag>
          <el-tag type="success" effect="plain" size="small">{{ t('execution.passed') }}: {{ passedCount }}</el-tag>
          <el-tag type="danger" effect="plain" size="small">{{ t('execution.failed') }}: {{ failedCount + errorCount }}</el-tag>
          <el-tag type="warning" effect="plain" size="small">{{ t('execution.error') }}: {{ errorCount }}</el-tag>
          <el-tag effect="plain" size="small">{{ t('execution.notStarted') }}: {{ notStartedCount }}</el-tag>
        </div>
      </div>
      <div class="report-summary__charts">
        <div ref="passRateRef" class="report-summary__chart" />
        <div ref="defectRef" class="report-summary__chart" />
      </div>
    </SectionPanel>

    <!-- 测试结果 -->
    <SectionPanel :title="t('execution.reportTestResults')" style="margin-top: 16px">
      <ReportCaseTable
        v-if="cases.length"
        :cases="cases"
        :suite-name="report.suite_name"
        :can-edit="canEdit"
        @view-log="$emit('view-log', $event)"
        @linked="$emit('linked')"
        @create-defect="$emit('create-defect', $event)"
      />
    </SectionPanel>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { RUN_STATUS_MAP, DEFECT_SEVERITY_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import SectionPanel from '@/components/common/SectionPanel.vue'
import StatusTag from '@/components/common/StatusTag.vue'
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

const totalCount = computed(() => summary.value?.total ?? 0)
const passedCount = computed(() => summary.value?.passed ?? 0)
const failedCount = computed(() => summary.value?.failed ?? 0)
const errorCount = computed(() => summary.value?.error ?? 0)
const skippedCount = computed(() => summary.value?.skipped ?? 0)
const executedCount = computed(() => passedCount.value + failedCount.value + errorCount.value)
const notStartedCount = computed(() => Math.max(0, totalCount.value - executedCount.value - skippedCount.value))

const durationDisplay = computed(() => {
  var ms = summary.value?.duration_ms
  if (ms == null) return '-'
  if (ms < 1000) return ms + 'ms'
  return (ms / 1000).toFixed(1) + 's'
})

const resultTagType = computed(() => {
  var s = summary.value?.status
  if (s === 'completed' && failedCount.value === 0 && errorCount.value === 0) return 'success'
  if (s === 'completed' || s === 'failed') return 'danger'
  if (s === 'cancelled') return 'info'
  return null
})

const resultLabel = computed(() => {
  var s = summary.value?.status
  if (s === 'completed' && failedCount.value === 0 && errorCount.value === 0) return RUN_STATUS_MAP.completed?.label || '已完成'
  if (s === 'completed' || s === 'failed') return RUN_STATUS_MAP.failed?.label || '已失败'
  if (s === 'cancelled') return RUN_STATUS_MAP.cancelled?.label || '已停止'
  return RUN_STATUS_MAP[s]?.label || s
})

function renderCharts() {
  // Pass rate / execution rate chart
  if (passRateRef.value) {
    passChart?.dispose()
    passChart = echarts.init(passRateRef.value)
    var total = totalCount.value
    var executed = executedCount.value
    var passed = passedCount.value
    var failed = failedCount.value + errorCount.value
    var execRate = total ? Math.round(executed / total * 100) : 0
    var passRate = executed ? Math.round(passed / executed * 100) : 0
    passChart.setOption({
      title: { text: t('execution.executionRate') + ' ' + execRate + '%  |  ' + t('page.test.passRate') + ' ' + passRate + '%', left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        data: [
          { name: t('execution.passed'), value: passed, itemStyle: { color: '#67c23a' } },
          { name: t('execution.failed'), value: failed, itemStyle: { color: '#f56c6c' } },
          { name: t('execution.notStarted'), value: notStartedCount.value, itemStyle: { color: '#909399' } },
        ].filter(function (d) { return d.value > 0 }),
      }],
    })
  }
  // Defect severity chart
  if (defectRef.value) {
    defectChart?.dispose()
    defectChart = echarts.init(defectRef.value)
    var data = defectChartData.value.length
      ? defectChartData.value.map(function (d) { return { name: DEFECT_SEVERITY_MAP[d.severity] || d.severity, value: d.count } })
      : [{ name: t('execution.noDefects'), value: 1, itemStyle: { color: '#dcdfe6' } }]
    defectChart.setOption({
      title: { text: t('page.defects.severity'), left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '60%', data: data }],
    })
  }
}

watch(() => props.report, async function () {
  await nextTick()
  renderCharts()
}, { deep: true })

onMounted(async function () {
  await nextTick()
  renderCharts()
})

onBeforeUnmount(function () {
  passChart?.dispose()
  defectChart?.dispose()
})
</script>

<style scoped lang="scss">
.report-summary__result-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.report-summary__result-tag {
  display: flex;
  align-items: center;
}

.report-summary__count-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.report-summary__charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.report-summary__chart {
  height: 220px;
  min-width: 0;
}
</style>
