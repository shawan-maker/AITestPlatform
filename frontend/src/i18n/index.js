import { createI18n } from 'vue-i18n'
import { STORAGE_KEYS } from '@/utils/constants'
import zhCN from './zh-CN.json'
import enUS from './en-US.json'

// 支持的 locale 列表
const SUPPORTED_LOCALES = ['zh-CN', 'en-US']

function normalizeLocale(raw) {
  if (!raw) return 'zh-CN'
  if (raw === 'zh' || raw === 'zh-CN') return 'zh-CN'
  if (raw === 'en' || raw === 'en-US') return 'en-US'
  if (!SUPPORTED_LOCALES.includes(raw)) return 'zh-CN'
  return raw
}

const LS_KEY = 'locale'
const rawSavedLocale = localStorage.getItem(LS_KEY)
const savedLocale = normalizeLocale(rawSavedLocale)

if (import.meta.env.DEV) {
  console.log('[i18n] rawSavedLocale:', rawSavedLocale, '-> normalized:', savedLocale)
}

// 创建 i18n 实例 - 直接传入原始 JSON 对象，不用深拷贝
const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'zh': zhCN,
    'en-US': enUS,
    'en': enUS,
  },
})

export default i18n
