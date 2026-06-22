import { ref } from 'vue'

/**
 * 报告查看器 composable，套件和任务报告共用。
 * @param {Function} fetchReportFn - 获取报告的 API 函数 (如 getSuiteReport / getTaskReport)
 */
export function useReportViewer(fetchReportFn) {
  const reportVisible = ref(false)
  const report = ref(null)
  const reportRunId = ref(null)

  async function viewReport(row) {
    reportRunId.value = row.id ?? row.run_id
    const res = await fetchReportFn(reportRunId.value)
    report.value = res.data.data
    reportVisible.value = true
  }

  async function reloadReport() {
    if (!reportRunId.value) return
    const res = await fetchReportFn(reportRunId.value)
    report.value = res.data.data
  }

  return { reportVisible, report, reportRunId, viewReport, reloadReport }
}
