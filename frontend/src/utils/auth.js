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
  if (!raw) return null
  const num = Number(raw)
  // 校验：必须是有限正整数（排除 NaN, Infinity, 负数, 0）
  return Number.isFinite(num) && num > 0 ? num : null
}

export function setCurrentProjectId(id) {
  if (id == null) {
    localStorage.removeItem(STORAGE_KEYS.CURRENT_PROJECT_ID)
  } else {
    localStorage.setItem(STORAGE_KEYS.CURRENT_PROJECT_ID, String(id))
  }
}
