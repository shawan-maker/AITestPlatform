import request from '@/utils/request'

export function getMeta() {
  return request.get('/ai-generation/meta')
}

export function generateFunctional(data) {
  return request.post('/ai-generation/functional/generate', data)
}

export function getFunctionalSession(sessionId) {
  return request.get(`/ai-generation/functional/sessions/${sessionId}`)
}

export function patchFunctionalPreview(sessionId, data) {
  return request.patch(`/ai-generation/functional/sessions/${sessionId}/preview`, data)
}

export function saveFunctionalSession(sessionId, data) {
  return request.post(`/ai-generation/functional/sessions/${sessionId}/save`, data)
}

export function generateApiFromInterface(data) {
  return request.post('/ai-generation/api/generate-from-interface', data)
}

export function generateApiFromDoc(data) {
  return request.post('/ai-generation/api/generate-from-doc', data)
}

export function getApiSession(sessionId) {
  return request.get(`/ai-generation/api/sessions/${sessionId}`)
}

export function patchApiPreview(sessionId, data) {
  return request.patch(`/ai-generation/api/sessions/${sessionId}/preview`, data)
}

export function confirmApiGeneration(data) {
  return request.post('/ai-generation/api/confirm', data)
}
