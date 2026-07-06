<template>
  <div v-if="report" class="report-summary">
    <!-- 结果统计：左右结构 -->
    <SectionPanel :title="t('execution.reportResultStats')" class="report-summary__stats-panel">
      <div class="report-summary__top">
        <div class="report-summary__basic">
          <el-descriptions :column="1" border>
            <el-descriptions-item :label="t('page.test.suites.suiteName')">{{ report.suite_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.relatedTask')">{{ report.task_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('execution.duration')">{{ durationDisplay }}</el-descriptions-item>
            <el-descriptions-item :label="t('execution.startTime')">{{ formatTime(summary.start_time) }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.successRate')">
              <span class="report-summary__rate">{{ successRateDisplay }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="report-summary__stats">
          <div class="report-summary__result-row">
            <div class="report-summary__result-tag">
              <span style="margin-right: 8px; font-weight: 500">{{ t('execution.execResult') }}：</span>
              <el-tag v-if="resultTagType" :type="resultTagType" size="small">{{ resultLabel }}</el-tag>
              <StatusTag v-else :status="summary.status" :map="runStatusMap" />
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
        </div>
      </div>
    </SectionPanel>

    <!-- 测试结果 — 占主体高度，可滚动+分页 -->
    <SectionPanel :title="t('execution.reportTestResults')" class="report-summary__results-section">
      <div class="report-summary__results-scroll">
        <ReportCaseTable
          v-if="cases.length"
          :cases="paginatedCases"
          :suite-name="report.suite_name"
          :can-edit="canEdit"
          @view-log="$emit('view-log', $event)"
          @linked="$emit('linked')"
          @create-defect="$emit('create-defect', $event)"
        />
        <div v-else class="report-summary__no-cases">{{ t('execution.noData') || '暂无用例数据' }}</div>
      </div>
      <div v-if="cases.length" class="report-summary__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="cases.length"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          small
          background
        />
      </div>
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
import { getRunStatusMap, getDefectSeverityMap } from '@/utils/constants'
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
const runStatusMap = computed(() => getRunStatusMap(t))
const defectSeverityMap = computed(() => getDefectSeverityMap(t))
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

// Success rate display
const successRateDisplay = computed(() => {
  var total = totalCount.value
  var passed = passedCount.value
  if (!total) return '-'
  var pct = (passed / total * 100).toFixed(1)
  return pct + '% (' + passed + '/' + total + ')'
})

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
  if (s === 'completed' && failedCount.value === 0 && errorCount.value === 0) return runStatusMap.completed?.label || t('status.exec.completed')
  if (s === 'completed' || s === 'failed') return runStatusMap.failed?.label || t('status.exec.failed')
  if (s === 'cancelled') return runStatusMap.cancelled?.label || t('status.exec.cancelled')
  return runStatusMap[s]?.label || s
})

// Pagination for cases
const currentPage = ref(1)
const pageSize = ref(10)
const paginatedCases = computed(() => {
  var start = (currentPage.value - 1) * pageSize.value
  return cases.value.slice(start, start + pageSize.value)
})

watch(() => props.report, () => { currentPage.value = 1 })

function renderCharts() {
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
  if (defectRef.value) {
    defectChart?.dispose()
    defectChart = echarts.init(defectRef.value)
    var data = defectChartData.value.length
      ? defectChartData.value.map(function (d) { return { name: defectSeverityMap[d.severity] || d.severity, value: d.count } })
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
.report-summary__stats-panel {
  flex-shrink: 0;
}

.report-summary__top {
  display: flex;
  gap: 0;
  align-items: stretch;
}

.report-summary__basic {
  flex: 0 0 400px;
  min-width: 0;
  padding-right: 24px;
  border-right: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;

  :deep(.el-descriptions) {
    flex: 1;
  }

  :deep(.el-descriptions__label) {
    white-space: nowrap;
    width: 100px;
  }

  :deep(.el-descriptions__content) {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.report-summary__stats {
  flex: 1;
  min-width: 0;
  padding-left: 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
}

.report-summary__result-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
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

.report-summary__rate {
  font-weight: 600;
  color: var(--el-color-primary);
}

.report-summary__charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.report-summary__chart {
  height: 180px;
  min-width: 0;
}

.report-summary__results-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

  :deep(.ui-section-panel__body) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
}

.report-summary__results-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.report-summary__pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.report-summary__no-cases {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 24px 0;
  text-align: center;
}
</style>
