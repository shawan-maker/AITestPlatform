import request from '@/utils/request'

export function getMe() {
  return request.get('/users/me')
}

export function listUsers(params = {}) {
  return request.get('/users', { params })
}

export function getUser(userId) {
  return request.get(`/users/${userId}`)
}

export function createUser(data) {
  return request.post('/users', data)
}

export function updateUserStatus(userId, isActive) {
  return request.patch(`/users/${userId}/status`, { is_active: isActive })
}

export function deleteUser(userId) {
  return request.delete(`/users/${userId}`)
}

export function changeMyPassword(data) {
  return request.put('/users/me/password', data)
}

export function resetUserPassword(userId, newPassword) {
  return request.put(`/users/${userId}/password`, { new_password: newPassword })
}

export function lookupUsers(params = {}) {
  return request.get('/users/lookup', { params })
}
