import { getAccessToken } from '@/utils/auth'

function apiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || '/api/v1'
}

export async function consumeSseStream(response, handlers = {}) {
  const reader = response.body?.getReader()
  if (!reader) {
    console.error('[SSE] ❌ No reader available')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let eventCount = 0

  console.log('[SSE] 🔄 Starting to consume SSE stream...')

  while (true) {
    const { done, value } = await reader.read()
    
    if (done) {
      console.log(`[SSE] ✅ Reader done, stream closed. Total events: ${eventCount}`)
      break
    }
    
    if (!value) {
      console.log('[SSE] ⚠️ No value received, continuing...')
      continue
    }
    
    // 正确解码 SSE 流
    const decoded = decoder.decode(value)
    buffer += decoded

    console.log(`[SSE] 📦 Received chunk: ${value.length} bytes, buffer: ${buffer.length} chars`)

    // SSE 事件以 \n\n 分隔
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    console.log(`[SSE] 📋 Parsed ${blocks.length} SSE blocks, remaining buffer: ${buffer.length} chars`)

    for (const block of blocks) {
      if (!block.trim()) continue
      
      let event = 'message'
      let data = ''
      
      const lines = block.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          event = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          data = line.slice(6)
        }
      }
      
      if (!data) {
        console.log(`[SSE] ⚠️ No data found in block, skipping`)
        continue
      }
      
      eventCount++
      let parsed = data
      try {
        parsed = JSON.parse(data)
        console.log(`[SSE] ✅ Event #${eventCount}: ${event}`, JSON.stringify(parsed).substring(0, 200))
      } catch (e) {
        console.log(`[SSE] 📄 Event #${eventCount}: ${event} (raw)`, data.substring(0, 200))
      }
      
      // 调用事件处理器
      if (handlers.onEvent) {
        handlers.onEvent(event, parsed)
      }
      if (handlers[event]) {
        handlers[event](parsed)
      }
      
      // 收到 done 事件后，强制停止读取
      if (event === 'done') {
        console.log('[SSE] 🏁 ✅ Done event received, stopping stream immediately')
        reader.cancel().catch((e) => console.warn('[SSE] ⚠️ Error cancelling reader:', e))
        console.log(`[SSE] ✅ Stream stopped. Total events: ${eventCount}`)
        return
      }

      // 每处理一个事件后让出主线程，确保用户交互能被响应
      await new Promise(resolve => setTimeout(resolve, 0))
    }
  }
  
  console.log(`[SSE] ✅ ConsumeSseStream ended normally. Total events: ${eventCount}`)
}

export async function postEventStream(path, body, handlers = {}, signal) {
  const token = getAccessToken()
  const url = `${apiBaseUrl()}${path}`

  console.log('[SSE] ========================================')
  console.log('[SSE] 📤 SENDING POST REQUEST')
  console.log('[SSE] URL:', url)
  console.log('[SSE] Has signal:', !!signal)
  console.log('[SSE] ========================================')

  // 诊断：记录活跃 SSE 连接数
  window.__activeSSECount = (window.__activeSSECount || 0) + 1
  console.log(`[SSE-DIAG] 活跃SSE连接数: ${window.__activeSSECount}`)

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    })

    console.log('[SSE] ✅ Response received, status:', response.status)

    if (!response.ok) {
      const text = await response.text()
      console.error('[SSE] ❌ Response not OK:', text)
      let message = text
      try {
        const json = JSON.parse(text)
        message = json.message || json.detail || text
      } catch {
        // ignore
      }
      throw new Error(message || `SSE request failed (${response.status})`)
    }

    console.log('[SSE] 🔄 Starting to consume SSE stream...')
    await consumeSseStream(response, handlers)
    console.log('[SSE] ✅ SSE stream consumption completed')
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('[SSE] ℹ️ Stream aborted by user')
    } else {
      console.error('[SSE] ❌ Error in postEventStream:', error)
    }
    throw error
  } finally {
    window.__activeSSECount = Math.max(0, (window.__activeSSECount || 1) - 1)
    console.log(`[SSE-DIAG] SSE连接关闭，剩余活跃数: ${window.__activeSSECount}`)
  }
}
