import { STORAGE_KEYS } from './constants'

export function getAccessToken() {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
}

export function getRefreshToken() {
  return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
}

export function setTokens({ accessToken, refreshToken }) {
  if (accessToken) {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
  }
  if (refreshToken) {
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)
  }
}

export function clearTokens() {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
}

export function getCurrentProjectId() {
  const raw = localStorage.getItem(STORAGE_KEYS.CURRENT_PROJECT_ID)
  return raw ? Number(raw) : null
}

export function setCurrentProjectId(id) {
  if (id == null) {
    localStorage.removeItem(STORAGE_KEYS.CURRENT_PROJECT_ID)
  } else {
    localStorage.setItem(STORAGE_KEYS.CURRENT_PROJECT_ID, String(id))
  }
}
