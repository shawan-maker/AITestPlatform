import request from '@/utils/request'

// Catalogs
export function getCatalogTree(params = {}) {
  return request.get('/env/catalogs/tree', { params })
}

export function createCatalog(data, params = {}) {
  return request.post('/env/catalogs', data, { params })
}

export function updateCatalog(id, data) {
  return request.patch(`/env/catalogs/${id}`, data)
}

export function deleteCatalog(id) {
  return request.delete(`/env/catalogs/${id}`)
}

export function moveCatalog(id, data) {
  return request.post(`/env/catalogs/${id}/move`, data)
}

// Environments
export function listEnvironments(params = {}) {
  return request.get('/env/environments', { params })
}

export function getEnvironment(id) {
  return request.get(`/env/environments/${id}`)
}

export function createEnvironment(data, params = {}) {
  return request.post('/env/environments', data, { params })
}

export function updateEnvironment(id, data) {
  return request.patch(`/env/environments/${id}`, data)
}

export function deleteEnvironment(id) {
  return request.delete(`/env/environments/${id}`)
}

export function copyEnvironment(id, data) {
  return request.post(`/env/environments/${id}/copy`, data)
}

export function getConfigs(environmentId) {
  return request.get(`/env/environments/${environmentId}/configs`)
}

export function putConfigGroup(environmentId, group, data) {
  return request.put(`/env/environments/${environmentId}/configs/${group}`, data)
}

export function createConfig(environmentId, data) {
  return request.post(`/env/environments/${environmentId}/configs`, data)
}

export function updateConfig(id, data) {
  return request.patch(`/env/configs/${id}`, data)
}

export function deleteConfig(id) {
  return request.delete(`/env/configs/${id}`)
}

// Global configs (project-level)
export function listGlobalConfigs(projectId) {
  return request.get(`/env/projects/${projectId}/global-configs`)
}

export function replaceGlobalConfigs(projectId, data) {
  return request.put(`/env/projects/${projectId}/global-configs`, data)
}

export function updateGlobalConfig(id, data) {
  return request.patch(`/env/global-configs/${id}`, data)
}

export function deleteGlobalConfig(id) {
  return request.delete(`/env/global-configs/${id}`)
}

// Snapshots (read-only for reports)
export function listSnapshots(environmentId) {
  return request.get(`/env/environments/${environmentId}/snapshots`)
}

export function getSnapshot(snapshotId) {
  return request.get(`/env/snapshots/${snapshotId}`)
}

export function deleteSnapshot(snapshotId) {
  return request.delete(`/env/snapshots/${snapshotId}`)
}

export function getTestEnvData(environmentId) {
  return request.get(`/env/environments/${environmentId}/test-env-data`)
}

// DB connections
export function listDbConnections(params = {}) {
  return request.get('/env/db-connections', { params })
}

export function createDbConnection(data, params = {}) {
  return request.post('/env/db-connections', data, { params })
}

export function updateDbConnection(id, data) {
  return request.patch(`/env/db-connections/${id}`, data)
}

export function deleteDbConnection(id) {
  return request.delete(`/env/db-connections/${id}`)
}

export function bindDbConnections(environmentId, data) {
  return request.put(`/env/environments/${environmentId}/db-connections`, data)
}

export function testDbConnection(id) {
  return request.post(`/env/db-connections/${id}/test`)
}

export function getDbTestLogs(id) {
  return request.get(`/env/db-connections/${id}/test-logs`)
}

// Functions
export function listFunctionFiles(params = {}) {
  return request.get('/env/function-files', { params })
}

export function getFunctionFile(id) {
  return request.get(`/env/function-files/${id}`)
}

export function createFunctionFile(data, params = {}) {
  return request.post('/env/function-files', data, { params })
}

export function updateFunctionFile(id, data) {
  return request.patch(`/env/function-files/${id}`, data)
}

export function deleteFunctionFile(id) {
  return request.delete(`/env/function-files/${id}`)
}

export function bindFunctionFiles(environmentId, data) {
  return request.put(`/env/environments/${environmentId}/function-files`, data)
}

export function validateFunctionFile(data) {
  return request.post('/env/function-files/validate', data)
}

// Uploaded files
export function listUploadedFiles(params = {}) {
  return request.get('/env/uploaded-files', { params })
}

export function uploadFile(formData, params = {}) {
  return request.post('/env/uploaded-files', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteUploadedFile(id) {
  return request.delete(`/env/uploaded-files/${id}`)
}

export function downloadUploadedFile(id) {
  return request.get(`/env/uploaded-files/${id}/download`, { responseType: 'blob' })
}

// Import/export
export function exportEnvironment(environmentId) {
  return request.get(`/env/environments/${environmentId}/export`, { responseType: 'blob' })
}

export function importEnvironment(data) {
  return request.post('/env/environments/import', data)
}

export function importEnvironmentFile(formData, params = {}) {
  return request.post('/env/environments/import-file', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
