<template>
  <div v-if="report" class="task-report-summary">
    <!-- 结果统计：左右结构 -->
    <SectionPanel :title="t('execution.reportResultStats')" class="task-report__stats-panel">
      <div class="task-report__top">
        <div class="task-report__basic">
          <el-descriptions :column="1" border>
            <el-descriptions-item :label="t('page.test.tasks.taskName')">{{ report.task_name || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.tabSuites')">{{ suiteNames || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('execution.duration')">{{ durationDisplay }}</el-descriptions-item>
            <el-descriptions-item :label="t('execution.startTime')">{{ formatTime(summary.start_time) }}</el-descriptions-item>
            <el-descriptions-item :label="t('page.test.successRate')">
              <span class="task-report__rate">{{ successRateDisplay }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="task-report__stats">
          <div class="task-report__result-row">
            <div class="task-report__result-tag">
              <span style="margin-right: 8px; font-weight: 500">{{ t('execution.execResult') }}：</span>
              <el-tag v-if="resultTagType" :type="resultTagType" size="small">{{ resultLabel }}</el-tag>
              <StatusTag v-else :status="summary.status" :map="RUN_STATUS_MAP" />
            </div>
            <div class="task-report__count-badges">
              <el-tag type="info" effect="plain" size="small">{{ t('page.test.totalCases') }}: {{ totalCount }}</el-tag>
              <el-tag type="success" effect="plain" size="small">{{ t('execution.passed') }}: {{ passedCount }}</el-tag>
              <el-tag type="danger" effect="plain" size="small">{{ t('execution.failed') }}: {{ failedCount + errorCount }}</el-tag>
              <el-tag type="warning" effect="plain" size="small">{{ t('execution.error') }}: {{ errorCount }}</el-tag>
              <el-tag effect="plain" size="small">{{ t('execution.notStarted') }}: {{ notStartedCount }}</el-tag>
            </div>
          </div>
          <div class="task-report__charts">
            <div ref="passRateRef" class="task-report__chart" />
            <div ref="defectRef" class="task-report__chart" />
          </div>
        </div>
      </div>
    </SectionPanel>

    <!-- 测试结果 — 套件级列表，行内展开用例，可滚动+分页 -->
    <SectionPanel :title="t('execution.reportTestResults')" class="task-report__results-section">
      <div class="task-report__suite-toolbar">
        <el-input v-model="suiteSearch" :placeholder="t('page.test.suites.suiteName')" clearable style="width: 260px" />
      </div>
      <div class="task-report__results-scroll">
        <AppTable :data="paginatedSuites" row-key="suite_run_id">
          <AppTableColumn type="expand" variant="fixed" :width="50">
            <template #default="{ row }">
              <div class="task-report__expand-cases">
                <ReportCaseTable
                  v-if="row.cases && row.cases.length"
                  :cases="row.cases"
                  :suite-name="row.suite_name"
                  :can-edit="canEdit"
                  @view-log="$emit('view-log', $event)"
                  @linked="$emit('linked')"
                  @create-defect="$emit('create-defect', $event)"
                />
                <div v-else class="task-report__no-cases">{{ t('execution.noData') || '暂无用例数据' }}</div>
              </div>
            </template>
          </AppTableColumn>
          <AppTableColumn prop="suite_id" variant="fixed" label="ID" :width="70" />
          <AppTableColumn prop="suite_name" variant="content" :label="t('page.test.suites.suiteName')" />
          <AppTableColumn variant="fixed" :label="t('page.test.caseCount')" :width="80">
            <template #default="{ row }">{{ row.summary?.total ?? (row.cases ? row.cases.length : 0) }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('execution.execResult')" :width="100">
            <template #default="{ row }">
              <template v-if="getSuiteResult(row)">
                <el-tag :type="getSuiteResult(row).type" size="small">{{ getSuiteResult(row).label }}</el-tag>
              </template>
              <StatusTag v-else :status="row.summary?.status" :map="RUN_STATUS_MAP" />
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('page.test.successRate')" :width="120">
            <template #default="{ row }">{{ calcSuiteSuccessRate(row) }}</template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('execution.duration')" :width="100">
            <template #default="{ row }">
              {{ row.summary?.duration_ms != null ? ((row.summary.duration_ms < 1000 ? row.summary.duration_ms + 'ms' : (row.summary.duration_ms / 1000).toFixed(1) + 's')) : '-' }}
            </template>
          </AppTableColumn>
          <AppTableColumn variant="fixed" :label="t('execution.startTime')" :width="170">
            <template #default="{ row }">{{ row.summary?.start_time ? formatTime(row.summary.start_time) : '-' }}</template>
          </AppTableColumn>
        </AppTable>
      </div>
      <div v-if="filteredSuites.length" class="task-report__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredSuites.length"
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
import { RUN_STATUS_MAP, DEFECT_SEVERITY_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'
import SectionPanel from '@/components/common/SectionPanel.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
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
const suites = computed(() => props.report?.suites ?? [])
const defectChartData = computed(() => props.report?.defect_chart ?? [])

const suiteNames = computed(() => suites.value.map(s => s.suite_name).join('、') || '-')

const totalCount = computed(() => summary.value?.total ?? 0)
const passedCount = computed(() => summary.value?.passed ?? 0)
const failedCount = computed(() => summary.value?.failed ?? 0)
const errorCount = computed(() => summary.value?.error ?? 0)
const skippedCount = computed(() => summary.value?.skipped ?? 0)
const executedCount = computed(() => passedCount.value + failedCount.value + errorCount.value)
const notStartedCount = computed(() => Math.max(0, totalCount.value - executedCount.value - skippedCount.value))

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
  if (s === 'completed' && failedCount.value === 0 && errorCount.value === 0) return RUN_STATUS_MAP.completed?.label || '已完成'
  if (s === 'completed' || s === 'failed') return RUN_STATUS_MAP.failed?.label || '已失败'
  if (s === 'cancelled') return RUN_STATUS_MAP.cancelled?.label || '已停止'
  return RUN_STATUS_MAP[s]?.label || s
})

// Suite search + pagination
const suiteSearch = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredSuites = computed(() => {
  if (!suiteSearch.value) return suites.value
  var kw = suiteSearch.value.toLowerCase()
  return suites.value.filter(s => (s.suite_name || '').toLowerCase().includes(kw))
})

const paginatedSuites = computed(() => {
  var start = (currentPage.value - 1) * pageSize.value
  return filteredSuites.value.slice(start, start + pageSize.value)
})

watch([() => props.report, suiteSearch], () => { currentPage.value = 1 })

function getSuiteResult(row) {
  var s = row.summary?.status
  if (!s) return null
  if (s === 'completed') {
    var fc = row.summary?.failed ?? 0
    var ec = row.summary?.error ?? 0
    if (fc === 0 && ec === 0) return { type: 'success', label: t('page.test.resultSuccess') || '成功' }
    return { type: 'danger', label: t('page.test.resultFail') || '失败' }
  }
  if (s === 'failed') return { type: 'danger', label: t('page.test.resultFail') || '失败' }
  if (s === 'cancelled') return { type: 'info', label: t('page.test.resultCancelled') || '已停止' }
  return null
}

function calcSuiteSuccessRate(row) {
  var s = row.summary
  if (!s) return '-'
  var total = s.total ?? 0
  var passed = s.passed ?? 0
  if (!total) return '-'
  var done = (s.passed ?? 0) + (s.failed ?? 0) + (s.error ?? 0)
  if (!done) return '-'
  var pct = passed / total * 100
  return pct.toFixed(1) + '% (' + passed + '/' + total + ')'
}

// Charts
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
.task-report__stats-panel {
  flex-shrink: 0;
}

.task-report__top {
  display: flex;
  gap: 0;
  align-items: stretch;
}

.task-report__basic {
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

.task-report__stats {
  flex: 1;
  min-width: 0;
  padding-left: 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
}

.task-report__result-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.task-report__result-tag {
  display: flex;
  align-items: center;
}

.task-report__count-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.task-report__rate {
  font-weight: 600;
  color: var(--el-color-primary);
}

.task-report__charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.task-report__chart {
  height: 180px;
  min-width: 0;
}

.task-report__results-section {
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

.task-report__suite-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.task-report__results-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;

  // Nested expand table should not overflow the scroll container
  :deep(.el-table__expanded-cell) {
    overflow-x: auto;
  }
}

.task-report__pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.task-report__expand-cases {
  padding: 12px 16px;
}

.task-report__no-cases {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 12px 0;
}
</style>
