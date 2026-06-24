export function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString()
}

export function formatTime(dt) {
  if (!dt) return '-'
  var d = new Date(dt)
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
}

export function formatResponseBody(body) {
  if (!body) return '-'
  if (typeof body === 'string') {
    try { return JSON.stringify(JSON.parse(body), null, 2) } catch (e) { return body }
  }
  return JSON.stringify(body, null, 2)
}

export function formatFileSize(bytes) {
  if (bytes == null || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let i = 0
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i += 1
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function summarizePayload(text, maxLen = 120) {
  if (!text) return ''
  const s = String(text).replace(/\s+/g, ' ')
  return s.length > maxLen ? `${s.slice(0, maxLen)}…` : s
}

/**
 * Format duration in ms to human-readable string.
 * e.g. 61397 → "1m 1s 397ms" (en) or "1分1秒397毫秒" (zh)
 */
export function formatDuration(ms, locale = 'zh') {
  if (ms == null || ms < 0) return '-'
  if (ms === 0) return locale === 'zh' ? '0毫秒' : '0ms'
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  const remainder = ms % 1000
  const parts = []
  if (locale === 'zh') {
    if (h) parts.push(h + '时')
    if (m) parts.push(m + '分')
    if (s) parts.push(s + '秒')
    if (remainder) parts.push(remainder + '毫秒')
  } else {
    if (h) parts.push(h + 'h')
    if (m) parts.push(m + 'm')
    if (s) parts.push(s + 's')
    if (remainder) parts.push(remainder + 'ms')
  }
  return parts.join(locale === 'zh' ? '' : ' ')
}
