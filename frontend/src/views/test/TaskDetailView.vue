<template>
  <div v-loading="loading" class="task-detail-view app-card">
    <PageHeader :title="task?.name || t('page.test.tasks.title')">
      <template #actions>
        <el-button @click="router.push('/test/tasks')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" type="primary" :loading="running" @click="run">{{ t('page.test.run') }}</el-button>
        <el-button v-if="task?.task_type === 'functional' || task?.task_type === 'manual'" @click="openManual">{{ t('page.test.manualRun') }}</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('page.test.tabBasic')" name="basic">
        <el-tag>{{ task?.task_type }}</el-tag>
      </el-tab-pane>
      <el-tab-pane :label="t('page.test.tabHistory')" name="history">
        <el-table :data="history" border>
          <el-table-column prop="started_at" :label="t('page.test.startedAt')" />
          <el-table-column prop="status" :label="t('common.status')" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <ManualRunDrawer v-model="manualVisible" :task-id="taskId" :run-id="manualRunId" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getTask } from '@/api/testManagement'
import { getTaskHistory, openManualRun, runTask } from '@/api/testExecution'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import ManualRunDrawer from '@/components/execution/ManualRunDrawer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const taskId = computed(() => Number(route.params.taskId))

const loading = ref(false)
const task = ref(null)
const history = ref([])
const activeTab = ref('basic')
const running = ref(false)
const manualVisible = ref(false)
const manualRunId = ref(null)

async function load() {
  loading.value = true
  try {
    const [tRes, hRes] = await Promise.all([getTask(taskId.value), getTaskHistory(taskId.value)])
    task.value = tRes.data.data
    history.value = hRes.data.data?.items ?? hRes.data.data ?? []
  } finally {
    loading.value = false
  }
}

async function run() {
  running.value = true
  try {
    await runTask(taskId.value)
    ElMessage.success(t('page.test.runStarted'))
    load()
  } finally {
    running.value = false
  }
}

async function openManual() {
  const res = await openManualRun(taskId.value)
  manualRunId.value = res.data.data?.run_id ?? res.data.data?.id
  manualVisible.value = true
}

onMounted(load)
</script>
