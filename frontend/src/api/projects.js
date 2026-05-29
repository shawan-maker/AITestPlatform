import request from '@/utils/request'

export function listProjects(params = {}) {
  return request.get('/projects', { params: { page: 1, page_size: 20, ...params } })
}

export function getProject(projectId) {
  return request.get(`/projects/${projectId}`)
}

export function createProject(data) {
  return request.post('/projects', data)
}

export function updateProject(projectId, data) {
  return request.patch(`/projects/${projectId}`, data)
}

export function deleteProject(projectId) {
  return request.delete(`/projects/${projectId}`)
}

export function batchDeleteProjects(projectIds) {
  return request.post('/projects/batch-delete', { project_ids: projectIds })
}

export function setProjectAdmin(projectId, userId) {
  return request.put(`/projects/${projectId}/admin`, { user_id: userId })
}

export function listMembers(projectId) {
  return request.get(`/projects/${projectId}/members`)
}

export function addMember(projectId, data) {
  return request.post(`/projects/${projectId}/members`, data)
}

export function updateMember(projectId, userId, data) {
  return request.patch(`/projects/${projectId}/members/${userId}`, data)
}

export function removeMember(projectId, userId) {
  return request.delete(`/projects/${projectId}/members/${userId}`)
}

export function transferOwner(projectId, newOwnerUserId) {
  return setProjectAdmin(projectId, newOwnerUserId)
}

export function listModules(projectId) {
  return request.get(`/projects/${projectId}/modules`)
}

export function createModule(projectId, data) {
  return request.post(`/projects/${projectId}/modules`, data)
}

export function updateModule(projectId, moduleId, data) {
  return request.patch(`/projects/${projectId}/modules/${moduleId}`, data)
}

export function deleteModule(projectId, moduleId) {
  return request.delete(`/projects/${projectId}/modules/${moduleId}`)
}
