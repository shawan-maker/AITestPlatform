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
 * @param {number} ms - Duration in milliseconds
 * @param {string} locale - 'zh' or 'en'
 * @param {boolean} showMs - Whether to show milliseconds (default: false)
 */
export function formatDuration(ms, locale = 'zh', showMs = false) {
  if (ms == null || ms < 0) return '-'
  if (ms === 0) return locale === 'zh' ? '0秒' : '0s'
  const d = Math.floor(ms / 86400000)
  const h = Math.floor((ms % 86400000) / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  const remainder = ms % 1000
  const parts = []
  if (locale === 'zh') {
    if (d) parts.push(d + '天')
    if (h) parts.push(h + '时')
    if (m) parts.push(m + '分')
    if (s) parts.push(s + '秒')
    if (showMs && remainder) parts.push(remainder + '毫秒')
  } else {
    if (d) parts.push(d + 'd')
    if (h) parts.push(h + 'h')
    if (m) parts.push(m + 'm')
    if (s) parts.push(s + 's')
    if (showMs && remainder) parts.push(remainder + 'ms')
  }
  return parts.length ? parts.join(locale === 'zh' ? '' : ' ') : (locale === 'zh' ? '0秒' : '0s')
}

/**
 * Calculate time-in-state for each status_timeline entry.
 * Adds duration_ms (time spent in that status) and prev_status (for transition display).
 * Last entry gets duration_ms=null (still in that state).
 */
export function calcStatusDurations(timeline) {
  if (!timeline?.length) return []
  return timeline.map(function (item, i) {
    var prev = i > 0 ? timeline[i - 1].status : null
    var durationMs = null
    if (i < timeline.length - 1) {
      var at = new Date(item.at).getTime()
      var nextAt = new Date(timeline[i + 1].at).getTime()
      durationMs = Math.max(0, nextAt - at)
    }
    return Object.assign({}, item, { duration_ms: durationMs, prev_status: prev })
  })
}
