import request from '@/utils/request'

// Suites
export function listSuites(params = {}) {
  return request.get('/test-management/suites', { params })
}

export function createSuite(data) {
  return request.post('/test-management/suites', data)
}

export function getSuite(id) {
  return request.get(`/test-management/suites/${id}`)
}

export function updateSuite(id, data) {
  return request.patch(`/test-management/suites/${id}`, data)
}

export function deleteSuite(id) {
  return request.delete(`/test-management/suites/${id}`)
}

export function batchDeleteSuites(ids) {
  return request.post('/test-management/suites/batch-delete', { suite_ids: ids })
}

export function listSuiteCases(suiteId, params = {}) {
  return request.get(`/test-management/suites/${suiteId}/cases`, { params })
}

export function replaceSuiteCases(suiteId, data) {
  return request.put(`/test-management/suites/${suiteId}/cases`, data)
}

export function appendSuiteCases(suiteId, data) {
  return request.post(`/test-management/suites/${suiteId}/cases`, data)
}

export function deleteSuiteCases(suiteId, data) {
  return request.delete(`/test-management/suites/${suiteId}/cases`, { data })
}

export function reorderSuiteCases(suiteId, data) {
  return request.post(`/test-management/suites/${suiteId}/cases/reorder`, data)
}

export function patchSuiteCaseFlags(suiteId, data) {
  return request.patch(`/test-management/suites/${suiteId}/cases/dependency-flags`, data)
}

// Tasks
export function listTasks(params = {}) {
  return request.get('/test-management/tasks', { params })
}

export function createTask(data) {
  return request.post('/test-management/tasks', data)
}

export function getTask(id) {
  return request.get(`/test-management/tasks/${id}`)
}

export function updateTask(id, data) {
  return request.patch(`/test-management/tasks/${id}`, data)
}

export function deleteTask(id) {
  return request.delete(`/test-management/tasks/${id}`)
}

export function batchDeleteTasks(ids) {
  return request.post('/test-management/tasks/batch-delete', { task_ids: ids })
}

export function listTaskSuites(taskId) {
  return request.get(`/test-management/tasks/${taskId}/suites`)
}

export function replaceTaskSuites(taskId, data) {
  return request.put(`/test-management/tasks/${taskId}/suites`, data)
}

export function reorderTaskSuites(taskId, data) {
  return request.post(`/test-management/tasks/${taskId}/suites/reorder`, data)
}

export function deleteTaskSuites(taskId, data) {
  return request.delete(`/test-management/tasks/${taskId}/suites`, { data })
}

export function listTaskCases(taskId) {
  return request.get(`/test-management/tasks/${taskId}/cases`)
}

export function replaceTaskCases(taskId, data) {
  return request.put(`/test-management/tasks/${taskId}/cases`, data)
}

export function reorderTaskCases(taskId, data) {
  return request.post(`/test-management/tasks/${taskId}/cases/reorder`, data)
}

export function deleteTaskCases(taskId, data) {
  return request.delete(`/test-management/tasks/${taskId}/cases`, { data })
}

export function getTaskCaseTree(taskId) {
  return request.get(`/test-management/tasks/${taskId}/cases/tree`)
}

// Pickers
export function pickApiCases(params = {}) {
  return request.get('/test-management/pickers/api-cases', { params })
}

export function pickFunctionalCases(params = {}) {
  return request.get('/test-management/pickers/functional-cases', { params })
}

export function pickSuites(params = {}) {
  return request.get('/test-management/pickers/suites', { params })
}

// Defects
export function listDefects(params = {}) {
  return request.get('/test-management/defects', { params })
}

export function createDefect(data) {
  return request.post('/test-management/defects', data)
}

export function getDefect(id) {
  return request.get(`/test-management/defects/${id}`)
}

export function updateDefect(id, data) {
  return request.patch(`/test-management/defects/${id}`, data)
}

export function transitionDefect(id, data) {
  return request.post(`/test-management/defects/${id}/transition`, data)
}

export function addDefectComment(id, data) {
  return request.post(`/test-management/defects/${id}/comments`, data)
}

export function batchDeleteDefects(ids) {
  return request.post('/test-management/defects/batch-delete', { defect_ids: ids })
}
