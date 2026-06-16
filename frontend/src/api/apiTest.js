import request from '@/utils/request'

// Catalogs
export function getApiCatalogTree(params = {}) {
  return request.get('/api-test/catalogs/tree', { params })
}

export function createApiCatalog(data, params = {}) {
  return request.post('/api-test/catalogs', data, { params })
}

export function updateApiCatalog(id, data) {
  return request.patch(`/api-test/catalogs/${id}`, data)
}

export function deleteApiCatalog(id) {
  return request.delete(`/api-test/catalogs/${id}`)
}

export function moveApiCatalog(id, data) {
  return request.post(`/api-test/catalogs/${id}/move`, data)
}

// Interfaces
export function listInterfaces(params = {}) {
  return request.get('/api-test/interfaces', { params })
}

export function listInterfacesByCatalog(catalogId, params = {}) {
  return request.get(`/api-test/catalogs/${catalogId}/interfaces`, { params })
}

export function getInterface(id) {
  return request.get(`/api-test/interfaces/${id}`)
}

export function createInterface(data, params = {}) {
  return request.post('/api-test/interfaces', data, { params })
}

export function updateInterface(id, data) {
  return request.patch(`/api-test/interfaces/${id}`, data)
}

export function deleteInterface(id) {
  return request.delete(`/api-test/interfaces/${id}`)
}

export function batchDeleteInterfaces(ids) {
  return request.post('/api-test/interfaces/batch-delete', { interface_ids: ids })
}

export function copyInterface(id) {
  return request.post(`/api-test/interfaces/${id}/copy`)
}

export function reorderInterfaces(data) {
  return request.post('/api-test/interfaces/reorder', data)
}

// Import
export function previewApiImport(params) {
  return request.get('/api-test/imports/preview', { params })
}

export function confirmApiImport(data) {
  return request.post('/api-test/imports/confirm', data)
}

// Cases
export function listApiCases(interfaceId, params = {}) {
  return request.get(`/api-test/interfaces/${interfaceId}/cases`, { params })
}

export function getApiCase(id) {
  return request.get(`/api-test/cases/${id}`)
}

export function createApiCase(data) {
  return request.post('/api-test/cases', data)
}

export function updateApiCase(id, data) {
  return request.patch(`/api-test/cases/${id}`, data)
}

export function deleteApiCase(id) {
  return request.delete(`/api-test/cases/${id}`)
}

export function batchDeleteApiCases(data) {
  return request.post('/api-test/cases/batch-delete', data)
}

export function generateCasePreview(interfaceId, data) {
  // v3: 异步预览，接口立即返回 session_id，前端轮询 generation-status 获取结果
  return request.post(`/api-test/interfaces/${interfaceId}/cases/generate-preview`, data)
}

export function confirmCaseGeneration(interfaceId, data) {
  // 预执行可能耗时较长，超时设为 5 分钟
  return request.post(`/api-test/interfaces/${interfaceId}/cases/confirm`, data, {
    timeout: 300000,
  })
}

// v2-Q3: AI预执行进度轮询
export function getGenerationStatus(interfaceId, sessionId) {
  return request.get(`/api-test/interfaces/${interfaceId}/cases/generation-status`, {
    params: { session_id: sessionId },
  })
}

// v2-L2: 用例调试运行（支持AbortController取消）
export function debugRunApiCase(id, data, { signal } = {}) {
  return request.post(`/api-test/cases/${id}/debug-run`, data, { signal })
}

export function getApiCaseRunRecords(id) {
  return request.get(`/api-test/cases/${id}/run-records`)
}

// Debug template
export function getDebugTemplate(interfaceId) {
  return request.get(`/api-test/interfaces/${interfaceId}/debug-template`)
}

export function saveDebugTemplate(interfaceId, data) {
  return request.put(`/api-test/interfaces/${interfaceId}/debug-template`, data)
}

// v2-L2: 接口调试运行（支持AbortController取消）
export function debugRunInterface(interfaceId, data, { signal } = {}) {
  return request.post(`/api-test/interfaces/${interfaceId}/debug-run`, data, { signal })
}

export function fillDebugFromDoc(interfaceId) {
  return request.post(`/api-test/interfaces/${interfaceId}/debug-template/fill-from-doc`)
}

export function listDebugRecords(interfaceId, params) {
  return request.get(`/api-test/interfaces/${interfaceId}/debug-records`, { params })
}

// Dependencies
export function getDocPreview(interfaceId) {
  return request.get(`/api-test/interfaces/${interfaceId}/doc-preview`)
}

export function listDependencies(interfaceId) {
  return request.get(`/api-test/interfaces/${interfaceId}/dependencies`)
}

export function saveDependencies(interfaceId, data) {
  return request.put(`/api-test/interfaces/${interfaceId}/dependencies`, data)
}

export function inferDependencies(interfaceId) {
  return request.post(`/api-test/interfaces/${interfaceId}/dependencies/infer`)
}

export function reanalyzeDependencies(interfaceId) {
  return request.post(`/api-test/interfaces/${interfaceId}/dependencies/reanalyze`)
}
