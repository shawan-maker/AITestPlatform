import request from '@/utils/request'

export function login(username, password) {
  const body = new URLSearchParams()
  body.append('username', username)
  body.append('password', password)
  return request.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function register(data) {
  return request.post('/auth/register', data)
}

export function logout(refreshToken) {
  return request.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {})
}

export function verifyToken() {
  return request.get('/auth/verify')
}

export function refreshToken(refresh_token) {
  return request.post('/auth/refresh', { refresh_token })
}
