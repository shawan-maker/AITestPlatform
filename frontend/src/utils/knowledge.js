/** 首版默认版本号（与后端 version_label_from_seq(1) 一致） */
export const INITIAL_VERSION_LABEL = 'v1.0'

const VERSION_SUFFIX_RE = /_v\d+\.\d+$/

/** 生成 `{文档标题}_{版本号}`，避免重复拼接或版本号不一致 */
export function formatDocumentVersionTitle(documentTitle, versionLabel) {
  const ver = (versionLabel || '').trim()
  let name = (documentTitle || '').trim()
  if (!name) return ver || ''
  if (!ver) return name
  const suffix = `_${ver}`
  if (name.endsWith(suffix)) return name
  if (VERSION_SUFFIX_RE.test(name)) {
    name = name.replace(VERSION_SUFFIX_RE, '').trim() || name
  }
  return `${name}${suffix}`
}

/** 从文件名取文档名（去扩展名、去尾部版本号） */
export function documentTitleFromFileName(fileName) {
  if (!fileName) return ''
  let stem = fileName.replace(/\.[^.]+$/, '').trim()
  if (VERSION_SUFFIX_RE.test(stem)) {
    stem = stem.replace(VERSION_SUFFIX_RE, '').trim()
  }
  return stem
}

/** 文档是否仍在解析/索引中 */
export function isDocumentProcessing(doc) {
  if (!doc) return false
  if (doc.doc_type === 'api_doc') {
    const parseStatus = doc.parse_status ?? ''
    const indexStatus = doc.index_status ?? ''
    if (parseStatus === 'parsing') return true
    if (['pending', 'parsing', 'indexing'].includes(indexStatus)) return true
    if (!parseStatus || parseStatus === 'pending') {
      return ['pending', 'parsing', 'indexing'].includes(indexStatus)
    }
    return false
  }
  if (doc.doc_type === 'requirement') {
    return ['pending', 'indexing'].includes(doc.index_status)
  }
  return false
}

/** @returns {true | false | undefined} */
function readTriState(doc, snakeKey) {
  if (!doc) return undefined
  const camelKey = snakeKey.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
  const value = doc[snakeKey] ?? doc[camelKey]
  if (value === true || value === 1 || value === 'true') return true
  if (value === false || value === 0 || value === 'false') return false
  return undefined
}

/**
 * 保存需求：已索引且当前版本尚未写入 RequirementDoc 时显示。
 * 优先 can_save_requirement；已保存标志 requirement_saved 优先隐藏。
 */
export function canSaveRequirement(doc) {
  if (!doc || doc.doc_type !== 'requirement') return false
  if (isDocumentProcessing(doc)) return false
  if (readTriState(doc, 'requirement_saved') === true) return false

  const backend = readTriState(doc, 'can_save_requirement')
  if (backend === true) return true
  if (backend === false) return false

  return doc.index_status === 'indexed'
}

/**
 * 保存接口：已解析且当前版本尚未导入时显示。
 */
export function canSaveInterfaces(doc) {
  if (!doc || doc.doc_type !== 'api_doc') return false
  if (isDocumentProcessing(doc)) return false
  if (readTriState(doc, 'interfaces_saved') === true) return false

  const backend = readTriState(doc, 'can_save_interfaces')
  if (backend === true) return true
  if (backend === false) return false

  return doc.parse_status === 'parsed'
}

/** Badge 展示用状态键 */
export function resolveParseDisplayStatus(doc) {
  if (!doc) return doc?.index_status ?? ''
  if (doc.doc_type === 'api_doc' && doc.index_status === 'na' && doc.parse_status === 'parsed') {
    return 'parsed'
  }
  return doc.index_status ?? ''
}

/** 将详情/预览接口项统一为表格展示结构 */
export function normalizeParsedInterfaceItem(item) {
  if (!item || typeof item !== 'object') return null
  const method = (item.method || '').toUpperCase()
  const path = item.path || ''
  if (!method || !path) return null
  return {
    method,
    path,
    summary: item.summary ?? null,
    module_name: item.module_name ?? item.moduleName ?? null,
    catalog_path: item.catalog_path ?? item.catalogPath ?? null,
  }
}
