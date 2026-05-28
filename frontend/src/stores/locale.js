import { defineStore } from 'pinia'
import { STORAGE_KEYS } from '@/utils/constants'

export const useLocaleStore = defineStore('locale', {
  state: () => ({
    locale: localStorage.getItem(STORAGE_KEYS.LOCALE) || 'zh-CN',
  }),

  actions: {
    setLocale(locale) {
      this.locale = locale
      localStorage.setItem(STORAGE_KEYS.LOCALE, locale)
    },

    toggleLocale() {
      this.setLocale(this.locale === 'zh-CN' ? 'en-US' : 'zh-CN')
    },
  },
})
