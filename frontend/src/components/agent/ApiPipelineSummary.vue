<template>
  <div class="pipeline-summary">
    <div class="pipeline-summary__header">
      <el-icon><CircleCheckFilled /></el-icon>
      <span class="pipeline-summary__title">{{ t('page.agent.pipelineSummary') }}</span>
    </div>

    <div class="pipeline-summary__stats">
      <div class="pipeline-summary__stat">
        <span class="pipeline-summary__stat-value">{{ summary.total_interfaces || 0 }}</span>
        <span class="pipeline-summary__stat-label">{{ t('page.agent.interfaceCount') }}</span>
      </div>
      <div class="pipeline-summary__stat">
        <span class="pipeline-summary__stat-value">{{ summary.total_cases || 0 }}</span>
        <span class="pipeline-summary__stat-label">{{ t('page.agent.caseCount') }}</span>
      </div>
      <div class="pipeline-summary__stat">
        <span class="pipeline-summary__stat-value">{{ formatPercent(summary.overall_pass_rate) }}</span>
        <span class="pipeline-summary__stat-label">{{ t('page.agent.overallPassRate') }}</span>
      </div>
    </div>

    <div class="pipeline-summary__interfaces">
      <div
        v-for="(iface, idx) in (summary.per_interface || [])"
        :key="idx"
        class="pipeline-summary__iface"
      >
        <div class="pipeline-summary__iface-header">
          <el-tag :type="methodTagType(iface.method)" size="small">{{ iface.method }}</el-tag>
          <span class="pipeline-summary__iface-name">{{ iface.summary }}</span>
        </div>
        <div class="pipeline-summary__iface-stats">
          <span>{{ t('page.agent.caseCount') }}: {{ iface.structured_case_count || 0 }}</span>
          <template v-if="iface.exec_results">
            <span class="pipeline-summary__pass">
              ✅ {{ iface.exec_results.passed || 0 }}
            </span>
            <span class="pipeline-summary__fail">
              ❌ {{ iface.exec_results.failed || 0 }}
            </span>
            <span class="pipeline-summary__rate">
              {{ t('page.agent.passRate') }}:
              <el-progress
                :percentage="Math.round((iface.exec_results.pass_rate || 0) * 100)"
                :stroke-width="8"
                :show-text="true"
                :color="passRateColor(iface.exec_results.pass_rate || 0)"
                style="width: 120px; display: inline-flex; vertical-align: middle;"
              />
            </span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { CircleCheckFilled } from '@element-plus/icons-vue'

defineProps({
  summary: { type: Object, default: () => ({}) },
})

const { t } = useI18n()

function formatPercent(rate) {
  if (rate == null) return '-'
  return `${Math.round(rate * 100)}%`
}

function methodTagType(method) {
  const m = (method || '').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

function passRateColor(rate) {
  if (rate >= 0.8) return '#67c23a'
  if (rate >= 0.5) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped lang="scss">
.pipeline-summary {
  margin-top: 16px;
  padding: 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  border-left: 3px solid var(--el-color-success);
}

.pipeline-summary__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-success);
}

.pipeline-summary__stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.pipeline-summary__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pipeline-summary__stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.pipeline-summary__stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pipeline-summary__interfaces {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pipeline-summary__iface {
  padding: 8px 12px;
  background: var(--el-bg-color);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}

.pipeline-summary__iface-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.pipeline-summary__iface-name {
  font-weight: 500;
  font-size: 14px;
}

.pipeline-summary__iface-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.pipeline-summary__pass {
  color: var(--el-color-success);
}

.pipeline-summary__fail {
  color: var(--el-color-danger);
}

.pipeline-summary__rate {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
