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
  const parseStatus = doc.parse_status ?? ''
  const indexStatus = doc.index_status ?? ''
  // parse_status=parsing 说明正在执行结构化解析（AI/Swagger/OpenAPI）
  if (parseStatus === 'parsing') return true
  // index_status 处于中间状态
  if (['pending', 'parsing', 'indexing'].includes(indexStatus)) return true
  // 已有最终状态则不再轮询
  if (['parsed', 'failed'].includes(parseStatus)) return false
  if (['indexed', 'failed', 'na'].includes(indexStatus)) return false
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
 * 保存接口：
 * - 结构化解析完成时显示（Swagger/OpenAPI → parse_status=parsed, index_status=na）
 * - AI 解析模式完成后也支持（parse_status=parsed, index_status=indexed）
 * - 需求文档等其他类型不支持"保存接口"
 */
export function canSaveInterfaces(doc) {
  if (!doc || doc.doc_type !== 'api_doc') return false
  if (isDocumentProcessing(doc)) return false
  if (readTriState(doc, 'interfaces_saved') === true) return false

  // 后端标记 can_save_interfaces=true 时允许（结构化解析或 AI 解析均可触发）
  const backend = readTriState(doc, 'can_save_interfaces')
  if (backend === true) return true
  if (backend === false) return false

  // 兜底：仅 parse_status=parsed（结构化或AI解析均适用）
  return doc.parse_status === 'parsed'
}

/** Badge 展示用状态键 */
export function resolveParseDisplayStatus(doc) {
  if (!doc) return doc?.index_status ?? ''
  const indexStatus = doc.index_status ?? ''
  const parseStatus = doc.parse_status ?? ''

  // api_doc：优先用 parse_status 判断结构化解析进度
  if (doc.doc_type === 'api_doc') {
    // 结构化解析完成（Swagger/OpenAPI/AI 均适用）
    if (parseStatus === 'parsed') return 'parsed'
    // 结构化解析中
    if (parseStatus === 'parsing') return 'parsing'
    // 结构化解析失败（AI 解析失败时 parse_status=failed，index_status 仍为 indexed）
    if (parseStatus === 'failed') return 'failed'
    // Swagger/OpenAPI 走 _process_spec_parse 时 index_status=na, parse_status=parsed 已在上面处理
    // 兜底回退到 index_status
  }

  // 非api_doc 或兜底：基于 index_status
  // indexing/pending → 解析中；indexed/na → 已解析
  if (indexStatus === 'indexing' || indexStatus === 'pending' || indexStatus === 'parsing') {
    return indexStatus
  }
  return indexStatus || ''
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
