import { getAccessToken } from '@/utils/auth'

function apiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || '/api/v1'
}

export async function consumeSseStream(response, handlers = {}) {
  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      if (!block.trim()) continue
      let event = 'message'
      let data = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim()
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (!data) continue
      let parsed = data
      try {
        parsed = JSON.parse(data)
      } catch {
        // keep raw string
      }
      handlers.onEvent?.(event, parsed)
      handlers[event]?.(parsed)
    }
  }
}

export async function postEventStream(path, body, handlers = {}, signal) {
  const token = getAccessToken()
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    const text = await response.text()
    let message = text
    try {
      const json = JSON.parse(text)
      message = json.message || json.detail || text
    } catch {
      // ignore
    }
    throw new Error(message || `SSE request failed (${response.status})`)
  }

  await consumeSseStream(response, handlers)
}
