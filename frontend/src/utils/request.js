import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '@/utils/auth'
import {
  clearRefreshQueue,
  getRefreshQueue,
  isApiSuccess,
  maybeParseJsonBlob,
  parseHttpError,
  setRefreshQueue,
} from '@/utils/request-helpers'

const AUTH_SKIP_PATHS = ['/auth/login', '/auth/register', '/auth/refresh']

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 60000,
})

function shouldSkipAuth(url = '') {
  return AUTH_SKIP_PATHS.some((path) => url.includes(path))
}

async function doRefreshToken() {
  const refresh = getRefreshToken()
  if (!refresh) {
    throw new Error('No refresh token')
  }
  const res = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
    { refresh_token: refresh },
    { timeout: 60000 },
  )
  const payload = res.data
  if (payload && typeof payload.code === 'number' && !isApiSuccess(payload.code)) {
    throw new Error(payload.message || '刷新失败')
  }
  const data = payload?.data ?? payload
  setTokens({
    accessToken: data.access_token,
    refreshToken: data.refresh_token ?? refresh,
  })
  return data.access_token
}

service.interceptors.request.use((config) => {
  if (!shouldSkipAuth(config.url)) {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

service.interceptors.response.use(
  async (response) => {
    const payload = response.data
    if (payload && typeof payload.code === 'number' && !isApiSuccess(payload.code)) {
      ElMessage.error(payload.message || '请求失败')
      return Promise.reject(new Error(payload.message || '请求失败'))
    }
    return response
  },
  async (error) => {
    const { config, response } = error
    if (response?.config?.responseType === 'blob' && response.data instanceof Blob) {
      const parsed = await maybeParseJsonBlob(response)
      if (parsed !== response.data) {
        response.data = parsed
      }
    }
    const status = response?.status

    const message = parseHttpError(error)
    error.displayMessage = message

    if (status === 401 && config && !config.__isRetry && !shouldSkipAuth(config.url)) {
      const refresh = getRefreshToken()
      if (!refresh) {
        clearTokens()
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
        return Promise.reject(error)
      }

      try {
        if (!getRefreshQueue()) {
          setRefreshQueue(
            doRefreshToken().finally(() => {
              clearRefreshQueue()
            }),
          )
        }
        const newToken = await getRefreshQueue()
        config.__isRetry = true
        config.headers.Authorization = `Bearer ${newToken}`
        return service(config)
      } catch {
        clearTokens()
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
        return Promise.reject(error)
      }
    }

    if (shouldSkipAuth(config?.url)) {
      return Promise.reject(Object.assign(error, { message }))
    }

    if (status !== 401) {
      if (!config?.silentError) {
        ElMessage.error(message)
      }
    }
    return Promise.reject(Object.assign(error, { message }))
  },
)

export default service
