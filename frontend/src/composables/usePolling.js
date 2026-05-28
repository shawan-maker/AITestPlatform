import { onUnmounted } from 'vue'

export function usePolling(fn, { interval = 2500, until = () => false } = {}) {
  let timer = null

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  async function tick() {
    await fn()
    if (until()) {
      stop()
    }
  }

  function start() {
    stop()
    tick()
    timer = setInterval(tick, interval)
  }

  onUnmounted(stop)

  return { start, stop }
}
