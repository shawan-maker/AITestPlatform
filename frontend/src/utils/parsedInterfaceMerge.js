import { normalizeParsedInterfaceItem } from './knowledge.js'

function interfaceKey(item) {
  const method = (item?.method || '').toUpperCase()
  const path = item?.path || ''
  return `${method}:${path}`
}

function pickField(target, source, field) {
  if (!target[field] && source[field]) {
    target[field] = source[field]
  }
}

/**
 * 按 method+path 合并多源解析接口，展示字段取首个非空值。
 * @param  {...Array} sources 每项为接口数组或 axios 响应 data.data.items
 */
export function mergeParsedInterfaceItems(...sources) {
  const byKey = new Map()

  for (const source of sources) {
    let items = source
    if (source && typeof source === 'object' && !Array.isArray(source)) {
      items = source.items ?? source.data?.items ?? source.data?.data?.items ?? []
    }
    if (!Array.isArray(items)) continue

    for (const raw of items) {
      const normalized = normalizeParsedInterfaceItem(raw)
      if (!normalized) continue
      const key = interfaceKey(normalized)
      const existing = byKey.get(key)
      if (!existing) {
        byKey.set(key, { ...normalized })
        continue
      }
      pickField(existing, normalized, 'summary')
      pickField(existing, normalized, 'module_name')
      pickField(existing, normalized, 'catalog_path')
    }
  }

  return [...byKey.values()]
}
