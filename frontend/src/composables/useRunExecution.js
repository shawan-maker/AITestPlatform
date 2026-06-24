import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { cancelRun } from '@/api/testExecution'
import { usePolling } from './usePolling'

/**
 * Composable for run/stop/polling logic, shared by suite and task views.
 */
export function useRunExecution({ triggerFn, progressFn, getRunId, onStarted, onComplete, onTick }) {
  const { t } = useI18n()
  const running = ref(false)
  const activeRun = ref(null)
  const progress = ref(null)
  const isRunning = computed(() => ['running', 'pending'].includes(progress.value?.status))
  let pollingInstance = null

  async function run(entityId) {
    running.value = true
    try {
      const res = await triggerFn(entityId)
      activeRun.value = res.data.data
      var rid = getRunId(activeRun.value)
      pollingInstance = usePolling(async () => {
        const pRes = await progressFn(rid)
        progress.value = pRes.data.data
        if (onTick) onTick()
      }, { interval: 2000, until: () => !['running', 'pending'].includes(progress.value?.status), onStop: () => { if (onComplete) onComplete() } })
      pollingInstance.start()
      ElMessage.success(t('page.test.runStarted'))
      if (onStarted) onStarted()
    } finally {
      running.value = false
    }
  }

  async function stopRun() {
    if (!activeRun.value) return
    try {
      var rid = getRunId(activeRun.value)
      await cancelRun(rid)
      ElMessage.success(t('page.test.runStopped'))
    } catch (e) {
      ElMessage.error(e.message)
    }
  }

  function resumePolling(rid) {
    activeRun.value = { suite_run_id: rid, id: rid }
    if (pollingInstance) pollingInstance.stop()
    pollingInstance = usePolling(async () => {
      const pRes = await progressFn(rid)
      progress.value = pRes.data.data
      if (onTick) onTick()
    }, { interval: 2000, until: () => !['running', 'pending'].includes(progress.value?.status), onStop: () => { if (onComplete) onComplete() } })
    pollingInstance.start()
  }

  return { running, activeRun, progress, isRunning, run, stopRun, resumePolling }
}
