import request from '@/utils/request'
import { postEventStream } from '@/utils/sse'

export function getMeta() {
  return request.get('/ai-generation/meta')
}

// --- Functional agent (Phase 2) ---

export function createFunctionalSession(data) {
  return request.post('/ai-generation/functional/sessions', data)
}

export function listFunctionalSessions(params) {
  return request.get('/ai-generation/functional/sessions', { params })
}

export function getFunctionalSession(sessionId) {
  return request.get(`/ai-generation/functional/sessions/${sessionId}`)
}

export function listFunctionalMessages(sessionId, params = {}) {
  return request.get(`/ai-generation/functional/sessions/${sessionId}/messages`, { params })
}

export function streamFunctionalMessage(sessionId, content, handlers, signal) {
  return postEventStream(
    `/ai-generation/functional/sessions/${sessionId}/messages`,
    { content },
    handlers,
    signal,
  )
}

export function patchFunctionalPreview(sessionId, data) {
  return request.patch(`/ai-generation/functional/sessions/${sessionId}/preview`, data)
}

export function saveFunctionalSession(sessionId, data) {
  return request.post(`/ai-generation/functional/sessions/${sessionId}/save`, data)
}

// --- SIT-F7: Session management ---

export function renameFunctionalSession(sessionId, title) {
  return request.patch(`/ai-generation/functional/sessions/${sessionId}`, { title })
}

export function summarizeFunctionalTitle(sessionId) {
  return request.post(`/ai-generation/functional/sessions/${sessionId}/summarize-title`)
}

export function deleteFunctionalSession(sessionId) {
  return request.delete(`/ai-generation/functional/sessions/${sessionId}`)
}

/** @deprecated Phase 1 one-shot generate */
export function generateFunctional(data) {
  return request.post('/ai-generation/functional/generate', data)
}

// --- API agent (Phase 2) ---

export function createApiSession(data) {
  return request.post('/ai-generation/api/sessions', data)
}

export function listApiSessions(params) {
  return request.get('/ai-generation/api/sessions', { params })
}

export function getApiSession(sessionId) {
  return request.get(`/ai-generation/api/sessions/${sessionId}`)
}

export function listApiMessages(sessionId, params = {}) {
  return request.get(`/ai-generation/api/sessions/${sessionId}/messages`, { params })
}

export function streamApiMessage(sessionId, content, handlers, signal) {
  return postEventStream(
    `/ai-generation/api/sessions/${sessionId}/messages`,
    { content },
    handlers,
    signal,
  )
}

export function patchApiPreview(sessionId, data) {
  return request.patch(`/ai-generation/api/sessions/${sessionId}/preview`, data)
}

export function confirmApiGeneration(data) {
  return request.post('/ai-generation/api/confirm', data)
}

// --- SIT-F7: Session management ---

export function renameApiSession(sessionId, title) {
  return request.patch(`/ai-generation/api/sessions/${sessionId}`, { title })
}

export function deleteApiSession(sessionId) {
  return request.delete(`/ai-generation/api/sessions/${sessionId}`)
}

/** @deprecated Phase 1 */
export function generateApiFromInterface(data) {
  return request.post('/ai-generation/api/generate-from-interface', data)
}

/** @deprecated Phase 1 */
export function generateApiFromDoc(data) {
  return request.post('/ai-generation/api/generate-from-doc', data)
}
