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

export function debugRunApiCase(id, data) {
  return request.post(`/api-test/cases/${id}/debug-run`, data)
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

export function debugRunInterface(interfaceId, data) {
  return request.post(`/api-test/interfaces/${interfaceId}/debug-run`, data)
}

export function fillDebugFromDoc(interfaceId) {
  return request.post(`/api-test/interfaces/${interfaceId}/debug-template/fill-from-doc`)
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
