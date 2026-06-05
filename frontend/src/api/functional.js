import request from '@/utils/request'

// Requirements
export function listRequirements(params = {}) {
  return request.get('/functional/requirements', { params })
}

export function getRequirement(id) {
  return request.get(`/functional/requirements/${id}`)
}

export function createRequirement(data) {
  return request.post('/functional/requirements', data)
}

export function updateRequirement(id, data) {
  return request.patch(`/functional/requirements/${id}`, data)
}

export function deleteRequirement(id) {
  return request.delete(`/functional/requirements/${id}`)
}

export function listCandidates(params = {}) {
  return request.get('/functional/requirements/candidates', { params })
}

export function getCandidatesCount(params = {}) {
  return request.get('/functional/requirements/candidates/count', { params })
}

export function getCandidate(id) {
  return request.get(`/functional/requirements/candidates/${id}`)
}

export function confirmCandidate(id, data) {
  return request.post(`/functional/requirements/candidates/${id}/confirm`, data)
}

export function deleteCandidate(id) {
  return request.delete(`/functional/requirements/candidates/${id}`)
}

export function updateCandidate(id, data) {
  return request.patch(`/functional/requirements/candidates/${id}`, data)
}

// Case catalogs
export function getCaseCatalogTree(params = {}) {
  return request.get('/functional/case-catalogs/tree', { params })
}

export function createCaseCatalog(data, params = {}) {
  return request.post('/functional/case-catalogs', data, { params })
}

export function moveCaseCatalog(id, data) {
  return request.post(`/functional/case-catalogs/${id}/move`, data)
}

export function updateCaseCatalog(id, data) {
  return request.patch(`/functional/case-catalogs/${id}`, data)
}

export function deleteCaseCatalog(id) {
  return request.delete(`/functional/case-catalogs/${id}`)
}

// Cases
export function listCases(params = {}) {
  return request.get('/functional/cases', { params })
}

export function getCase(id) {
  return request.get(`/functional/cases/${id}`)
}

export function createCase(data) {
  return request.post('/functional/cases', data)
}

export function updateCase(id, data) {
  return request.patch(`/functional/cases/${id}`, data)
}

export function deleteCase(id) {
  return request.delete(`/functional/cases/${id}`)
}

export function copyCase(id) {
  return request.post(`/functional/cases/${id}/copy`)
}

export function reorderCases(data) {
  return request.post('/functional/cases/reorder', data)
}

export function batchUpdateCases(data) {
  return request.post('/functional/cases/batch-update', data)
}

export function batchDeleteCases(data) {
  return request.post('/functional/cases/batch-delete', data)
}

export function exportCases(params = {}) {
  return request.get('/functional/cases/export', { params, responseType: 'blob' })
}
