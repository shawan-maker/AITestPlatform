<template>
  <div v-loading="loading" class="suite-detail-view app-card">
    <PageHeader :title="suite?.name || t('page.test.suites.title')">
      <template #actions>
        <el-button @click="router.push('/test/suites')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" type="primary" :loading="running" @click="run">{{ t('page.test.run') }}</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('page.test.tabBasic')" name="basic">
        <el-descriptions v-if="suite" :column="2" border>
          <el-descriptions-item :label="t('common.name')">{{ suite.name }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.apiCases.selectEnv')">{{ suite.environment_name || suite.environment_id }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      <el-tab-pane :label="t('page.test.tabCases')" name="cases">
        <el-table :data="cases" border>
          <el-table-column prop="case_name" :label="t('page.functional.caseName')" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane :label="t('page.test.tabHistory')" name="history">
        <RunProgressPanel v-if="activeRun" :progress="progress" />
        <el-table :data="history" border>
          <el-table-column prop="started_at" :label="t('page.test.startedAt')" />
          <el-table-column prop="status" :label="t('common.status')" width="120">
            <template #default="{ row }"><StatusTag :status="row.status" :map="RUN_STATUS_MAP" /></template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="120">
            <template #default="{ row }">
              <el-button link @click="viewReport(row)">{{ t('page.test.report') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="reportVisible" :title="t('page.test.report')" size="70%">
      <ReportSummary v-if="report" :report="report" :can-edit="canEdit" @view-log="viewCaseLog" @linked="reloadReport" />
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getSuite, listSuiteCases } from '@/api/testManagement'
import { getCaseRunLog, getSuiteHistory, getSuiteProgress, getSuiteReport, runSuite } from '@/api/testExecution'
import { usePermission } from '@/composables/usePermission'
import { usePolling } from '@/composables/usePolling'
import { RUN_STATUS_MAP } from '@/utils/constants'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import RunProgressPanel from '@/components/execution/RunProgressPanel.vue'
import ReportSummary from '@/components/execution/ReportSummary.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const suiteId = computed(() => Number(route.params.suiteId))

const loading = ref(false)
const suite = ref(null)
const cases = ref([])
const history = ref([])
const activeTab = ref('basic')
const running = ref(false)
const activeRun = ref(null)
const progress = ref(null)
const reportVisible = ref(false)
const report = ref(null)
const reportRunId = ref(null)

async function load() {
  loading.value = true
  try {
    const [sRes, cRes, hRes] = await Promise.all([
      getSuite(suiteId.value),
      listSuiteCases(suiteId.value),
      getSuiteHistory(suiteId.value),
    ])
    suite.value = sRes.data.data
    cases.value = cRes.data.data?.items ?? cRes.data.data ?? []
    history.value = hRes.data.data?.items ?? hRes.data.data ?? []
  } finally {
    loading.value = false
  }
}

async function run() {
  running.value = true
  try {
    const res = await runSuite(suiteId.value)
    activeRun.value = res.data.data
    activeTab.value = 'history'
    const polling = usePolling(async () => {
      const pRes = await getSuiteProgress(activeRun.value.run_id ?? activeRun.value.id)
      progress.value = pRes.data.data
    }, { interval: 2000, until: () => !['running', 'pending'].includes(progress.value?.status) })
    polling.start()
    ElMessage.success(t('page.test.runStarted'))
    load()
  } finally {
    running.value = false
  }
}

async function viewReport(row) {
  reportRunId.value = row.id ?? row.run_id
  const res = await getSuiteReport(reportRunId.value)
  report.value = res.data.data
  reportVisible.value = true
}

async function reloadReport() {
  if (!reportRunId.value) return
  const res = await getSuiteReport(reportRunId.value)
  report.value = res.data.data
}

async function viewCaseLog(row) {
  const res = await getCaseRunLog(row.id)
  ElMessage.info(res.data.data?.error_message || res.data.data?.case_name || t('execution.viewLog'))
}

onMounted(load)
</script>
