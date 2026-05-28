import i18n from '@/i18n'

let refreshPromise = null

export function isApiSuccess(code) {
  return code === 200 || code === 0
}

export function getRefreshQueue() {
  return refreshPromise
}

export function setRefreshQueue(promise) {
  refreshPromise = promise
}

export function clearRefreshQueue() {
  refreshPromise = null
}

/** 409 code → i18n key (17-00 §6.1) */
const CONFLICT_CODE_MAP = {
  requirement_confirmed: 'error.conflict.requirementConfirmed',
  index_in_progress: 'error.conflict.indexInProgress',
  interface_duplicate: 'error.conflict.interfaceDuplicate',
  case_in_suite: 'error.conflict.caseInSuite',
  project_has_children: 'error.conflict.projectHasChildren',
  unique_owner: 'error.conflict.uniqueOwner',
  catalog_depth: 'error.conflict.catalogDepth',
  run_in_progress: 'error.conflict.runInProgress',
  copy_name: 'error.conflict.copyName',
  requirement_title: 'error.conflict.requirementTitle',
  upload_duplicate: 'error.conflict.uploadDuplicate',
}

/** 409 message → i18n key mapping (17-00 §6.1) */
const CONFLICT_MESSAGE_MAP = [
  { pattern: /已确认|confirmed/i, key: 'error.conflict.requirementConfirmed' },
  { pattern: /索引|解析中|indexing|parsing/i, key: 'error.conflict.indexInProgress' },
  { pattern: /method\+path|method.*path|相同.*接口/i, key: 'error.conflict.interfaceDuplicate' },
  { pattern: /套件|suite|已被.*引用/i, key: 'error.conflict.caseInSuite' },
  { pattern: /子资源|blockers/i, key: 'error.conflict.projectHasChildren' },
  { pattern: /owner|所有者/i, key: 'error.conflict.uniqueOwner' },
  { pattern: /层级|目录.*级|catalog.*depth/i, key: 'error.conflict.catalogDepth' },
  { pattern: /进行中|正在执行|running/i, key: 'error.conflict.runInProgress' },
  { pattern: /_copy|重名|已存在/i, key: 'error.conflict.copyName' },
  { pattern: /标题.*唯一|title.*unique/i, key: 'error.conflict.requirementTitle' },
  { pattern: /同名文件|upload.*duplicate/i, key: 'error.conflict.uploadDuplicate' },
]

function mapConflictMessage(message) {
  if (!message) return null
  const { t, te } = i18n.global
  for (const { pattern, key } of CONFLICT_MESSAGE_MAP) {
    if (pattern.test(message) && te(key)) {
      return t(key)
    }
  }
  return message
}

/** 从 Axios / FastAPI 错误中提取可读文案，避免暴露 HTTP 状态码 */
export function parseHttpError(error, fallback = '请求失败') {
  const data = error?.response?.data
  const status = error?.response?.status

  if (status === 409) {
    const { t, te } = i18n.global
    const code = data?.code
    if (code && CONFLICT_CODE_MAP[code] && te(CONFLICT_CODE_MAP[code])) {
      return t(CONFLICT_CODE_MAP[code])
    }
    const msg = data?.message || ''
    return mapConflictMessage(msg) || msg || fallback
  }

  if (data && typeof data.message === 'string' && data.message.trim()) {
    return data.message
  }
  if (typeof data?.detail === 'string' && data.detail.trim()) {
    return data.detail
  }
  if (Array.isArray(data?.detail) && data.detail.length) {
    const first = data.detail[0]
    if (typeof first === 'string') return first
    if (first?.msg) return first.msg
  }
  if (status === 401) return '用户名或密码错误'
  if (status === 403) return '账号已禁用或无权访问'
  if (status === 422) return '请求参数不正确'
  const raw = error?.message || ''
  if (/status code \d{3}/i.test(raw)) {
    return fallback
  }
  return raw || fallback
}
