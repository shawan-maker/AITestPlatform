import request from '@/utils/request'

export function uploadDocument(formData, params = {}) {
  return request.post('/knowledge/documents', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listDocuments(params = {}) {
  return request.get('/knowledge/documents', { params })
}

export function getDocument(documentId) {
  return request.get(`/knowledge/documents/${documentId}`)
}

export function uploadVersion(documentId, formData) {
  return request.post(`/knowledge/documents/${documentId}/versions`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listVersions(documentId, params = {}) {
  return request.get(`/knowledge/documents/${documentId}/versions`, { params })
}

export function downloadDocument(documentId) {
  return request.get(`/knowledge/documents/${documentId}/download`, { responseType: 'blob' })
}

export function downloadVersion(documentId, versionId) {
  return request.get(`/knowledge/documents/${documentId}/versions/${versionId}/download`, {
    responseType: 'blob',
  })
}

export function reindexDocument(documentId) {
  return request.post(`/knowledge/documents/${documentId}/reindex`)
}

export function deleteDocument(documentId) {
  return request.delete(`/knowledge/documents/${documentId}`)
}

export function getRequirementCandidate(documentId) {
  return request.get(`/knowledge/documents/${documentId}/requirement-candidate`)
}

export function getVersionTextPreview(documentId, versionId) {
  return request.get(`/knowledge/documents/${documentId}/versions/${versionId}/text-preview`)
}

export function getParsedInterfaces(documentId, versionId, config = {}) {
  return request.get(
    `/knowledge/documents/${documentId}/versions/${versionId}/parsed-interfaces`,
    { silentError: true, ...config },
  )
}

export function previewImport(documentId, versionId, config = {}) {
  return request.post(
    `/knowledge/documents/${documentId}/versions/${versionId}/import-interfaces/preview`,
    null,
    config,
  )
}

export function confirmImport(documentId, versionId, data) {
  return request.post(
    `/knowledge/documents/${documentId}/versions/${versionId}/import-interfaces`,
    data,
  )
}
