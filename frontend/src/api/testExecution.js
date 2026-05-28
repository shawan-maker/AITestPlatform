import request from '@/utils/request'

export function runSuite(suiteId, data = {}) {
  return request.post(`/test-execution/runs/suites/${suiteId}`, data)
}

export function runTask(taskId, data = {}) {
  return request.post(`/test-execution/runs/tasks/${taskId}`, data)
}

export function cancelRun(runId) {
  return request.post(`/test-execution/runs/${runId}/cancel`)
}

export function getSuiteProgress(runId) {
  return request.get(`/test-execution/runs/suite-runs/${runId}/progress`)
}

export function getTaskProgress(runId) {
  return request.get(`/test-execution/runs/task-runs/${runId}/progress`)
}

export function getSuiteReport(runId) {
  return request.get(`/test-execution/runs/suite-runs/${runId}/report`)
}

export function getTaskReport(runId) {
  return request.get(`/test-execution/runs/task-runs/${runId}/report`)
}

export function getCaseRunLog(caseRunId) {
  return request.get(`/test-execution/runs/case-runs/${caseRunId}`)
}

export function getSuiteHistory(suiteId, params = {}) {
  return request.get(`/test-execution/runs/suites/${suiteId}/history`, { params })
}

export function getTaskHistory(taskId, params = {}) {
  return request.get(`/test-execution/runs/tasks/${taskId}/history`, { params })
}

export function openManualRun(taskId, data = {}) {
  return request.post(`/test-execution/runs/tasks/${taskId}/manual`, data)
}

export function getManualContext(runId) {
  return request.get(`/test-execution/runs/task-runs/${runId}/manual`)
}

export function getManualCase(runId, caseId) {
  return request.get(`/test-execution/runs/task-runs/${runId}/manual/cases/${caseId}`)
}

export function patchManualCase(runId, caseId, data) {
  return request.patch(`/test-execution/runs/task-runs/${runId}/manual/cases/${caseId}`, data)
}

export function createDefectFromRun(data) {
  return request.post('/test-execution/defects', data)
}

export function batchLinkDefects(data) {
  return request.post('/test-execution/defects/batch-link', data)
}
