import { defineStore } from 'pinia'
import { login as loginApi, logout as logoutApi, verifyToken } from '@/api/auth'
import { clearTokens, getRefreshToken, setTokens, getAccessToken } from '@/utils/auth'
import { parseHttpError } from '@/utils/request-helpers'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    initialized: false,
  }),

  getters: {
    isLoggedIn: (state) => !!state.user,
    isSuperAdmin: (state) => !!state.user?.is_super_admin,
    accessToken: () => getAccessToken(),
  },

  actions: {
    async login(username, password) {
      try {
        const res = await loginApi(username, password)
        const body = res.data
        const tokenData = body.data ?? body
        setTokens({
          accessToken: body.access_token ?? tokenData.access_token,
          refreshToken: tokenData.refresh_token,
        })
        await this.fetchUser()
      } catch (error) {
        throw new Error(parseHttpError(error, '登录失败，请检查用户名和密码'))
      }
    },

    async fetchUser() {
      const res = await verifyToken()
      const data = res.data.data
      this.user = data?.user ?? data
      this.initialized = true
      return this.user
    },

    async restoreSession() {
      if (!getAccessToken()) {
        this.initialized = true
        return false
      }
      try {
        await this.fetchUser()
        return true
      } catch {
        clearTokens()
        this.user = null
        this.initialized = true
        return false
      }
    },

    async logout() {
      try {
        const refresh = getRefreshToken()
        if (getAccessToken()) {
          await logoutApi(refresh)
        }
      } catch {
        /* ignore */
      } finally {
        clearTokens()
        this.user = null
      }
    },
  },
})
