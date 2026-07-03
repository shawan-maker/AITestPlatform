import { getAccessToken } from '@/utils/auth'

function apiBaseUrl() {
  // 如果配置了后端地址（VITE_BACKEND_ORIGIN），SSE 直连后端，绕过 Vite Proxy
  // 如果未配置（留空），SSE 走 VITE_API_BASE_URL（代理模式）
  const origin = import.meta.env.VITE_BACKEND_ORIGIN
  if (origin) {
    return `${origin}/api/v1`
  }
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

  console.log(`[SSE-TIME] 🔄 consumeSseStream 开始 at ${new Date().toISOString()}`)

  while (true) {
    const { done, value } = await reader.read()

    if (done) {
      console.log(`[SSE-TIME] ✅ Reader done at ${new Date().toISOString()}. Total events: ${eventCount}`)
      break
    }

    if (!value) {
      continue
    }

    // 正确解码 SSE 流
    const decoded = decoder.decode(value)
    buffer += decoded

    // SSE 事件以 \n\n 分隔
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

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
        continue
      }

      eventCount++
      let parsed = data
      try {
        parsed = JSON.parse(data)
      } catch (e) {
        // raw data
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
        console.log(`[SSE-TIME] 🏁 done 事件收到 at ${new Date().toISOString()}, events=${eventCount}`)
        reader.cancel().catch((e) => console.warn('[SSE] ⚠️ Error cancelling reader:', e))
        return
      }

      // 每处理一个事件后让出主线程，确保用户交互能被响应
      await new Promise(resolve => setTimeout(resolve, 0))
    }
  }

  console.log(`[SSE-TIME] ✅ consumeSseStream 正常结束 at ${new Date().toISOString()}, events=${eventCount}`)
}

export async function postEventStream(path, body, handlers = {}, signal) {
  const token = getAccessToken()
  const url = `${apiBaseUrl()}${path}`

  const sendTime = new Date().toISOString()
  console.log(`[SSE-TIME] 📤 POST 发送 at ${sendTime} url=${url}`)

  // 诊断：记录活跃 SSE 连接数
  window.__activeSSECount = (window.__activeSSECount || 0) + 1

  // 监听 abort 信号触发时间
  if (signal) {
    signal.addEventListener('abort', () => {
      console.log(`[SSE-TIME] ⚡ AbortSignal 触发 at ${new Date().toISOString()}`)
    }, { once: true })
  }

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

    console.log(`[SSE-TIME] ✅ Response headers 到达 at ${new Date().toISOString()}, status=${response.status}`)

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
    console.log(`[SSE-TIME] ✅ SSE 流消费完成 at ${new Date().toISOString()}`)
  } catch (error) {
    const abortTime = new Date().toISOString()
    if (error.name === 'AbortError') {
      console.log(`[SSE-TIME] ℹ️ AbortError 捕获 at ${abortTime} (发送于 ${sendTime})`)
      // 确保 reader 被取消
      try {
        console.log(`[SSE-TIME] 🔧 reader.cancel() 开始 at ${new Date().toISOString()}`)
        // reader 已在 consumeSseStream 中处理，这里不需要再 cancel
      } catch (e) {
        console.warn(`[SSE-TIME] ⚠️ cancel 异常:`, e)
      }
      console.log(`[SSE-TIME] ✅ abort 流程完成 at ${new Date().toISOString()}`)
    } else {
      console.error(`[SSE-TIME] ❌ 错误 at ${abortTime}:`, error)
    }
    throw error
  } finally {
    window.__activeSSECount = Math.max(0, (window.__activeSSECount || 1) - 1)
    console.log(`[SSE-TIME] 🏁 finally 执行 at ${new Date().toISOString()}, 活跃SSE=${window.__activeSSECount}`)
  }
}
