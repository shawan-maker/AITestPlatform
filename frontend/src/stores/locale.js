import { defineStore } from 'pinia'
import { STORAGE_KEYS } from '@/utils/constants'
import i18n from '@/i18n'

const SUPPORTED_LOCALES = ['zh-CN', 'en-US']

function normalizeLocale(raw) {
  if (!raw) return 'zh-CN'
  if (raw === 'zh' || raw === 'zh-CN') return 'zh-CN'
  if (raw === 'en' || raw === 'en-US') return 'en-US'
  if (!SUPPORTED_LOCALES.includes(raw)) return 'zh-CN'
  return raw
}

export const useLocaleStore = defineStore('locale', {
  state: () => {
    const rawLocale = localStorage.getItem(STORAGE_KEYS.LOCALE)
    const normalizedLocale = normalizeLocale(rawLocale)
    
    // 修复无效 locale 值
    if (rawLocale && !SUPPORTED_LOCALES.includes(rawLocale)) {
      localStorage.setItem(STORAGE_KEYS.LOCALE, normalizedLocale)
    }
    
    return {
      locale: normalizedLocale,
    }
  },

  actions: {
    setLocale(locale) {
      const normalized = normalizeLocale(locale)
      this.locale = normalized
      localStorage.setItem(STORAGE_KEYS.LOCALE, normalized)
      i18n.global.locale.value = normalized
    },

    toggleLocale() {
      this.setLocale(this.locale === 'zh-CN' ? 'en-US' : 'zh-CN')
    },
  },
})
